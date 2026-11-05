"""Live daily issuance: availability, idempotency, resumption and persistence."""

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from energy_trading_pipeline.data_ingestion.smard_client import SMARD_SERIES
from energy_trading_pipeline.forecasting.daily import (
    backfill_actuals,
    latest_issuance,
    refresh_market_data,
    run_daily_forecast,
)
from energy_trading_pipeline.forecasting.store import (
    MARKET_DATA_KEY,
    LocalArtifactStore,
    build_store,
    strategy_keys,
)

STRATEGIES = ("no_retraining", "fixed_schedule", "performance_triggered")


@pytest.fixture
def config():
    config = yaml.safe_load(Path("configs/experiment_day_ahead_published.yaml").read_text())
    config["backtest"].update(train_window_days=10, validation_window_days=1)
    config["model"]["params"] = {
        "n_estimators": 3,
        "max_depth": 2,
        "n_jobs": 1,
        "random_state": 42,
        "objective": "reg:squarederror",
    }
    config["retraining"] = {
        "strategy": "performance_triggered",
        "fixed_schedule_interval_days": 2,
        "rolling_rmse_threshold": 0.0,
        "rolling_rmse_window_days": 1,
        "rolling_rmse_min_periods": 1,
        "actual_availability_lag_hours": 1,
    }
    return config


@pytest.fixture
def market():
    """Hourly SMARD-shaped data with a deterministic, learnable structure."""
    stamps = pd.date_range("2026-09-01", "2026-11-05", freq="h", tz="UTC")
    index = np.arange(len(stamps), dtype=float)
    return pd.DataFrame(
        {
            "timestamp": stamps,
            "price_de": 50 + 10 * np.sin(index / 12) + index / 500,
            "price_fr": 40 + 5 * np.cos(index / 24),
            "forecast_pv_wind_de": 20000 + 8000 * np.sin(index / 24),
            "forecast_generation_total_de": 45000 + 5000 * np.cos(index / 24),
        }
    )


class FakeClient:
    """Serve rows from a fixed frame, recording requested intervals."""

    def __init__(self, frame, published_through=None):
        self.frame = frame
        self.published_through = published_through
        self.calls = []

    def fetch_frame(self, columns, start, end):
        self.calls.append((start, end))
        index = pd.date_range(start, end, freq="h", inclusive="left")
        result = pd.DataFrame({"timestamp": index}).merge(
            self.frame, on="timestamp", how="left"
        )
        if self.published_through is not None:
            result.loc[result["timestamp"] > self.published_through, list(columns)] = np.nan
        return result.loc[:, ["timestamp", *columns]]


def seed(store, market, through):
    store.write_frame(MARKET_DATA_KEY, market[market["timestamp"] < through].copy())


@pytest.mark.parametrize(
    "now,expected_delivery",
    [
        ("2026-11-03T15:00:00Z", date(2026, 11, 3)),  # before 18:00 local
        ("2026-11-03T17:30:00Z", date(2026, 11, 4)),  # after 18:00 local
        ("2026-11-03T23:30:00Z", date(2026, 11, 4)),
    ],
)
def test_issuance_never_precedes_the_run(config, now, expected_delivery):
    """A daytime run reissues yesterday's issuance, never a future one."""
    issuance, delivery = latest_issuance(config, pd.Timestamp(now))
    assert delivery == expected_delivery
    assert issuance <= pd.Timestamp(now)


def test_refresh_fetches_only_new_hours(tmp_path, config, market):
    store = LocalArtifactStore(tmp_path)
    through = pd.Timestamp("2026-11-01", tz="UTC")
    seed(store, market, through)
    client = FakeClient(market)

    refresh_market_data(store, config, through=pd.Timestamp("2026-11-02", tz="UTC"), client=client)

    start, end = client.calls[0]
    assert start == through
    assert end == pd.Timestamp("2026-11-02", tz="UTC")


def test_unpublished_hours_are_not_stored(tmp_path, config, market):
    store = LocalArtifactStore(tmp_path)
    seed(store, market, pd.Timestamp("2026-11-01", tz="UTC"))
    published_through = pd.Timestamp("2026-11-01T12:00", tz="UTC")
    client = FakeClient(market, published_through=published_through)

    combined = refresh_market_data(
        store, config, through=pd.Timestamp("2026-11-02", tz="UTC"), client=client
    )

    assert combined["timestamp"].max() == published_through
    assert not combined[list(SMARD_SERIES)].isna().any().any()


def test_backfill_only_records_actuals_that_are_usable(market):
    now = pd.Timestamp("2026-11-02T12:00", tz="UTC")
    forecasts = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                ["2026-11-02T10:00", "2026-11-02T11:00", "2026-11-02T13:00"], utc=True
            ),
            "actual": [np.nan, np.nan, np.nan],
        }
    )

    filled = backfill_actuals(forecasts, market, now=now)

    # Usable one hour after delivery: 10:00 yes, 11:00 exactly at the bound, 13:00 no.
    assert filled["actual"].notna().tolist() == [True, True, False]


def test_daily_run_issues_every_strategy_and_persists_state(tmp_path, config, market):
    store = LocalArtifactStore(tmp_path)
    now = pd.Timestamp("2026-11-03T18:30:00Z")
    seed(store, market, now.floor("h"))

    summary = run_daily_forecast(
        store, config, strategies=STRATEGIES, now=now, client=FakeClient(market)
    )

    assert summary["delivery_date"] == "2026-11-04"
    assert {row["strategy"] for row in summary["strategies"]} == set(STRATEGIES)
    for row in summary["strategies"]:
        assert row["hours"] == 24
        keys = strategy_keys(row["strategy"])
        forecasts = store.read_frame(keys["forecasts"])
        assert len(forecasts) == 24
        assert forecasts["prediction"].notna().all()
        # Tomorrow is not delivered yet, so no actuals exist for it.
        assert forecasts["actual"].isna().all()
        state = store.read_yaml(keys["state"])
        assert state["model_version"] == row["model_version"]
        assert state["policy"]["strategy"] == row["strategy"]
        assert store.exists(f"live/{row['strategy']}/models/{row['model_version']}.json")
    assert store.exists("live/latest_run.yaml")


def test_forecasts_use_only_data_available_at_issuance(tmp_path, config, market):
    """Mutating prices usable only after issuance must not change the forecast."""
    now = pd.Timestamp("2026-11-03T18:30:00Z")
    issuance = pd.Timestamp("2026-11-03T17:00:00Z")

    first = LocalArtifactStore(tmp_path / "a")
    seed(first, market, now.floor("h"))
    run_daily_forecast(first, config, strategies=("no_retraining",), now=now, client=FakeClient(market))

    mutated = market.copy()
    later = mutated["timestamp"] + pd.Timedelta(hours=1) > issuance
    assert later.any()
    mutated.loc[later, "price_de"] += 10_000
    second = LocalArtifactStore(tmp_path / "b")
    seed(second, mutated, now.floor("h"))
    run_daily_forecast(second, config, strategies=("no_retraining",), now=now, client=FakeClient(mutated))

    keys = strategy_keys("no_retraining")
    np.testing.assert_array_equal(
        first.read_frame(keys["forecasts"])["prediction"].to_numpy(),
        second.read_frame(keys["forecasts"])["prediction"].to_numpy(),
    )


def test_rerunning_a_day_is_idempotent(tmp_path, config, market):
    store = LocalArtifactStore(tmp_path)
    now = pd.Timestamp("2026-11-03T18:30:00Z")
    seed(store, market, now.floor("h"))
    client = FakeClient(market)

    first = run_daily_forecast(store, config, strategies=STRATEGIES, now=now, client=client)
    before = {s: store.read_frame(strategy_keys(s)["forecasts"]).copy() for s in STRATEGIES}
    second = run_daily_forecast(store, config, strategies=STRATEGIES, now=now + pd.Timedelta(hours=1), client=client)

    for row in second["strategies"]:
        strategy = row["strategy"]
        assert row["reissued"] is True
        assert row["retrained"] is False
        after = store.read_frame(strategy_keys(strategy)["forecasts"])
        assert len(after) == 24
        assert not after.duplicated(["timestamp"]).any()
        pd.testing.assert_series_equal(after["prediction"], before[strategy]["prediction"])
    versions = {r["strategy"]: r["model_version"] for r in first["strategies"]}
    assert {r["strategy"]: r["model_version"] for r in second["strategies"]} == versions


def test_consecutive_days_respect_each_strategy_schedule(tmp_path, config, market):
    store = LocalArtifactStore(tmp_path)
    client = FakeClient(market)
    versions = {s: [] for s in STRATEGIES}

    for day in range(4):
        now = pd.Timestamp("2026-10-31T18:30:00Z") + pd.Timedelta(days=day)
        if day == 0:
            seed(store, market, now.floor("h"))
        summary = run_daily_forecast(store, config, strategies=STRATEGIES, now=now, client=client)
        for row in summary["strategies"]:
            versions[row["strategy"]].append(row["model_version"])

    # Trained once, then frozen.
    assert len(set(versions["no_retraining"])) == 1
    # Threshold 0 fires whenever observed errors exist, so it refits repeatedly.
    assert len(set(versions["performance_triggered"])) > 1
    # Weekly-style interval of 2 days refits less often than the daily trigger.
    assert len(set(versions["fixed_schedule"])) < len(set(versions["performance_triggered"]))
    forecasts = store.read_frame(strategy_keys("no_retraining")["forecasts"])
    assert len(forecasts) == 4 * 24
    assert not forecasts.duplicated(["timestamp"]).any()


def test_missing_predictors_refuse_to_issue(tmp_path, config, market):
    """A predictor SMARD has not published must stop the day, not be invented."""
    store = LocalArtifactStore(tmp_path)
    now = pd.Timestamp("2026-11-03T18:30:00Z")
    # Publication stops before the delivery day begins.
    truncated = market[market["timestamp"] < pd.Timestamp("2026-11-03T20:00", tz="UTC")]
    seed(store, truncated, now.floor("h"))

    with pytest.raises(ValueError, match="not fully published"):
        run_daily_forecast(
            store, config, strategies=("no_retraining",), now=now,
            client=FakeClient(truncated, published_through=truncated["timestamp"].max()),
        )


def test_build_store_selects_backend():
    assert isinstance(build_store("/tmp/example"), LocalArtifactStore)
    s3 = build_store("s3://bucket/prefix", client=object())
    assert s3.bucket == "bucket" and s3.prefix == "prefix"
    with pytest.raises(ValueError, match="Invalid S3 destination"):
        build_store("s3://")


@pytest.mark.parametrize("key", ["/etc/passwd", "../escape", ""])
def test_store_rejects_keys_outside_the_root(tmp_path, key):
    with pytest.raises(ValueError, match="within the store"):
        LocalArtifactStore(tmp_path).exists(key)


def test_only_configured_series_are_required(config):
    """An unused series must not be fetched, nor able to withhold an hour."""
    from energy_trading_pipeline.forecasting.daily import required_market_columns

    assert required_market_columns(config) == [
        "price_de",
        "price_fr",
        "forecast_pv_wind_de",
        "forecast_generation_total_de",
    ]
    config["features"]["day_ahead_forecast_columns"] = ["forecast_pv_wind_de"]
    assert required_market_columns(config) == [
        "price_de",
        "price_fr",
        "forecast_pv_wind_de",
    ]


def test_unknown_configured_series_fails_clearly(config):
    from energy_trading_pipeline.forecasting.daily import required_market_columns

    config["features"]["day_ahead_forecast_columns"] = ["load_fr"]
    with pytest.raises(ValueError, match="Unknown SMARD forecast series"):
        required_market_columns(config)


def test_a_gap_in_an_unused_series_does_not_block_a_run(tmp_path, config, market):
    """Filter 122 has real holes; a config that excludes it must still run."""
    config["features"]["day_ahead_forecast_columns"] = ["forecast_pv_wind_de"]
    config["backtest"]["feature_columns"] = [
        column
        for column in config["backtest"]["feature_columns"]
        if column != "forecast_generation_total_de"
    ]
    holed = market.copy()
    hole = (holed["timestamp"] >= pd.Timestamp("2026-10-23", tz="UTC")) & (
        holed["timestamp"] < pd.Timestamp("2026-10-24", tz="UTC")
    )
    holed.loc[hole, "forecast_generation_total_de"] = np.nan

    store = LocalArtifactStore(tmp_path)
    now = pd.Timestamp("2026-11-03T18:30:00Z")
    seed(store, holed, now.floor("h"))
    summary = run_daily_forecast(
        store, config, strategies=("no_retraining",), now=now, client=FakeClient(holed)
    )

    assert summary["strategies"][0]["hours"] == 24
    stored = store.read_frame(MARKET_DATA_KEY)
    assert "forecast_generation_total_de" not in stored.columns
    assert not stored["timestamp"].diff().iloc[1:].ne(pd.Timedelta(hours=1)).any()


def test_lambda_handler_runs_the_same_forecast(tmp_path, config, market, monkeypatch):
    """The handler must add no forecasting logic of its own."""
    from energy_trading_pipeline.forecasting import lambda_handler

    store = LocalArtifactStore(tmp_path / "store")
    seed(store, market, pd.Timestamp("2026-11-03T18:00:00Z"))
    captured = {}

    def fake_run(built_store, cfg, *, strategies):
        captured["destination"] = built_store.root
        captured["strategies"] = strategies
        return {"strategies": [], "delivery_date": "2026-11-04"}

    monkeypatch.setattr(lambda_handler, "run_daily_forecast", fake_run)
    monkeypatch.setenv("ETP_STORE", str(tmp_path / "store"))
    monkeypatch.setenv("ETP_CONFIG", "configs/experiment_day_ahead_pvwind.yaml")
    monkeypatch.setenv("ETP_MODEL_PARAMS", "configs/model_params.yaml")

    summary = lambda_handler.handler({}, None)

    assert captured["destination"] == tmp_path / "store"
    assert captured["strategies"] == ("fixed_schedule", "no_retraining", "performance_triggered")
    assert summary["delivery_date"] == "2026-11-04"


def test_lambda_handler_requires_a_store(monkeypatch):
    from energy_trading_pipeline.forecasting import lambda_handler

    monkeypatch.delenv("ETP_STORE", raising=False)
    with pytest.raises(ValueError, match="ETP_STORE"):
        lambda_handler.handler({}, None)


def test_lambda_handler_rejects_unknown_strategies(monkeypatch, tmp_path):
    from energy_trading_pipeline.forecasting import lambda_handler

    monkeypatch.setenv("ETP_STORE", str(tmp_path))
    with pytest.raises(ValueError, match="Unknown strategies"):
        lambda_handler.handler({"strategies": "no_retraining,made_up"}, None)
