"""Prepared cached prices through static XGBoost forecasting and CLI artifacts."""

from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from energy_trading_pipeline.backtesting.backtest_runner import (
    run_backtest,
    run_configured_backtest,
)
from energy_trading_pipeline.backtesting.splitter import (
    generate_backtest_windows_from_config,
)
from energy_trading_pipeline.cli import main
from energy_trading_pipeline.features.availability import (
    build_availability_dataset,
    prepare_configured_day_ahead,
)
from energy_trading_pipeline.retraining.performance_triggered import (
    PerformanceTriggeredPolicy,
)


@pytest.fixture
def inputs(tmp_path):
    config = yaml.safe_load(Path("configs/experiment_day_ahead.yaml").read_text())
    config["backtest"].update(
        train_window_days=2,
        validation_window_days=1,
        evaluation_start_date="2025-01-15",
        evaluation_end_date="2025-01-16",
    )
    config["model"]["params"] = {
        "n_estimators": 3,
        "max_depth": 2,
        "n_jobs": 1,
        "random_state": 42,
    }
    config["paths"] = {
        "processed_data_parquet_path": str(tmp_path / "prices.parquet"),
        "feature_data_parquet_path": str(tmp_path / "features.parquet"),
        "models_dir": str(tmp_path / "models"),
        "logs_dir": str(tmp_path / "logs"),
    }
    timestamps = pd.date_range("2025-01-01", "2025-01-18", freq="h", tz="UTC")
    prices = pd.DataFrame(
        {
            "timestamp": timestamps,
            "price_de": 50 + np.sin(np.arange(len(timestamps))),
            "price_fr": 40.0,
        }
    )
    prices.to_parquet(config["paths"]["processed_data_parquet_path"], index=False)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config))
    return config, prices, config_path


def run(frame, config, tmp_path, name, **kwargs):
    return run_backtest(
        frame,
        config,
        feature_columns=config["backtest"]["feature_columns"],
        model_version="model_20250114_090000",
        model_output_path=tmp_path / name / "model.json",
        forecast_path=tmp_path / name / "forecasts.parquet",
        **kwargs,
    )


def test_future_mutation_cannot_change_issued_features_or_predictions(inputs, tmp_path):
    config, prices, _ = inputs
    original, _ = build_availability_dataset(prices, config, source_dataset="fixture")
    issuance = generate_backtest_windows_from_config(config)[0].issuance
    later = prices["timestamp"] + pd.Timedelta(hours=1) > issuance
    prices.loc[later, "price_de"] += 10000
    mutated, _ = build_availability_dataset(prices, config, source_dataset="fixture")
    selected = original["forecast_timestamp"] == issuance
    columns = config["backtest"]["feature_columns"]
    pd.testing.assert_frame_equal(
        original.loc[selected, columns], mutated.loc[selected, columns]
    )
    before = run(original, config, tmp_path, "before")
    after = run(mutated, config, tmp_path, "after")
    np.testing.assert_array_equal(
        before.loc[before["forecast_timestamp"] == issuance, "prediction"],
        after.loc[after["forecast_timestamp"] == issuance, "prediction"],
    )
    assert not before["actual"].equals(after["actual"])


def test_hooks_see_only_actuals_usable_at_issuance(inputs, tmp_path):
    config, prices, _ = inputs
    frame, _ = build_availability_dataset(prices, config, source_dataset="fixture")
    seen = []

    def hook(issuance, history):
        seen.append((issuance, history.copy()))
        return False

    forecasts = run(frame, config, tmp_path, "hook", policy_hook=hook)
    assert len(forecasts) == 48
    assert seen[0][1].empty
    issuance, history = seen[1]
    assert history["timestamp"].max() + pd.Timedelta(hours=1) == issuance
    assert ((history["timestamp"] + pd.Timedelta(hours=1)) <= issuance).all()
    assert not (history["timestamp"] == issuance).any()


@pytest.mark.parametrize("day,count", [("2025-03-30", 23), ("2025-10-26", 25)])
def test_dst_complete_prediction_blocks(inputs, tmp_path, day, count):
    config, _, _ = inputs
    config["backtest"].update(evaluation_start_date=day, evaluation_end_date=day)
    times = pd.date_range(
        pd.Timestamp(day, tz="UTC") - pd.Timedelta(days=15), periods=17 * 24, freq="h"
    )
    prices = pd.DataFrame(
        {
            "timestamp": times,
            "price_de": 50 + np.sin(np.arange(len(times))),
            "price_fr": 40.0,
        }
    )
    frame, _ = build_availability_dataset(prices, config, source_dataset="fixture")
    forecasts = run(frame, config, tmp_path, "dst")
    assert len(forecasts) == count
    assert forecasts["timestamp"].is_unique
    assert forecasts["forecast_timestamp"].nunique() == 1


def test_cli_preparation_backtest_and_no_overwrite(inputs, capsys):
    config, _, config_path = inputs
    assert main(["prepare-day-ahead", "--config", str(config_path)]) == 0
    output = Path(config["paths"]["feature_data_parquet_path"])
    original = output.read_bytes()
    assert main(["prepare-day-ahead", "--config", str(config_path)]) == 1
    assert output.read_bytes() == original
    assert main(["backtest", "--config", str(config_path)]) == 0
    (metadata_path,) = Path(config["paths"]["logs_dir"]).glob(
        "runs/*/run_metadata.yaml"
    )
    metadata = yaml.safe_load(metadata_path.read_text())
    assert metadata["availability_contract"]["issue_hour"] == 10
    assert metadata["evaluation_purpose"] == "engineering_smoke_not_final_evaluation"
    forecasts = pd.read_parquet(metadata["artifact_paths"]["forecasts"])
    assert len(forecasts) == 48
    assert (
        metadata["issuance_times"][0]
        == forecasts.iloc[0]["forecast_timestamp"].isoformat()
    )


@pytest.mark.parametrize("mutation", ["hash", "config", "metadata_missing"])
def test_sidecar_config_and_integrity_fail_before_artifacts(inputs, mutation):
    config, _, config_path = inputs
    prepare_configured_day_ahead(config, config_file_path=config_path)
    path = Path(config["paths"]["feature_data_parquet_path"])
    if mutation == "config":
        config["backtest"]["issue_hour"] = 9
    elif mutation == "hash":
        frame = pd.read_parquet(path)
        frame.loc[0, "spread_lag_48"] += 2
        frame.to_parquet(path, index=False)
    else:
        path.with_suffix(".metadata.yaml").unlink()
    with pytest.raises((ValueError, FileNotFoundError)):
        run_configured_backtest(config, config_file_path=config_path)
    assert not Path(config["paths"]["logs_dir"]).exists()


@pytest.mark.parametrize(
    "mutation", ["gap", "provenance", "naive", "metadata_predictor", "nonfinite"]
)
def test_invalid_day_ahead_input_preflight(inputs, tmp_path, mutation):
    config, prices, _ = inputs
    frame, _ = build_availability_dataset(prices, config, source_dataset="fixture")
    if mutation == "gap":
        frame = frame.loc[
            frame["timestamp"] != pd.Timestamp("2025-01-15 03:00", tz="UTC")
        ]
    elif mutation == "provenance":
        frame.loc[0, "feature_available_at"] -= pd.Timedelta(hours=1)
    elif mutation == "naive":
        frame["forecast_timestamp"] = frame["forecast_timestamp"].dt.tz_localize(None)
    elif mutation == "metadata_predictor":
        config["backtest"]["feature_columns"].append("forecast_timestamp")
    else:
        frame.loc[0, "spread_lag_48"] = np.inf
    with pytest.raises(ValueError):
        run(frame, config, tmp_path, "invalid")
    assert not (tmp_path / "invalid").exists()


def test_direct_backtest_never_overwrites(inputs, tmp_path):
    config, prices, _ = inputs
    frame, _ = build_availability_dataset(prices, config, source_dataset="fixture")
    run(frame, config, tmp_path, "saved")
    original = (tmp_path / "saved" / "model.json").read_bytes()
    with pytest.raises(FileExistsError):
        run(frame, config, tmp_path, "saved")
    assert (tmp_path / "saved" / "model.json").read_bytes() == original


def test_rolling_rmse_is_unreachable_on_the_day_ahead_decision_schedule(
    inputs, tmp_path
):
    """Runner-shaped 167/168: a dense window still misses the decision hour."""
    config, prices, _ = inputs
    config = deepcopy(config)
    config["backtest"]["evaluation_end_date"] = "2025-01-17"
    frame, _ = build_availability_dataset(prices, config, source_dataset="fixture")
    observed = {}

    def hook_for(policy, name):
        def hook(issuance, history):
            policy.should_retrain(issuance, history)
            observed.setdefault(name, []).append(policy.rolling_rmse)
            return False

        return hook

    starved = PerformanceTriggeredPolicy(threshold=10.0**9, window_days=1)
    anchored = PerformanceTriggeredPolicy(
        threshold=10.0**9, window_days=1, actual_availability_lag_hours=1
    )
    run(frame, config, tmp_path, "starved", policy_hook=hook_for(starved, "starved"))
    run(frame, config, tmp_path, "anchored", policy_hook=hook_for(anchored, "anchored"))

    # The decision hour's actual is never usable, so the unanchored window holds
    # at most 23 of the 24 hourly errors it requires and stays warm-up forever.
    assert all(np.isnan(value) for value in observed["starved"])
    assert np.isnan(observed["anchored"][0])
    assert np.isfinite(observed["anchored"][-1])


def test_day_ahead_rolling_rmse_matches_errors_observable_at_issuance(
    inputs, tmp_path
):
    config, prices, _ = inputs
    config = deepcopy(config)
    config["backtest"]["evaluation_end_date"] = "2025-01-17"
    frame, _ = build_availability_dataset(prices, config, source_dataset="fixture")
    policy = PerformanceTriggeredPolicy(
        threshold=10.0**9, window_days=1, actual_availability_lag_hours=1
    )
    seen = []

    def hook(issuance, history):
        policy.should_retrain(issuance, history)
        seen.append((issuance, history.copy(), policy.rolling_rmse))
        return False

    run(frame, config, tmp_path, "matches", policy_hook=hook)

    issuance, history, reported = seen[-1]
    anchor = issuance - pd.Timedelta(hours=1)
    window = history[
        (history["timestamp"] > anchor - pd.Timedelta(days=1))
        & (history["timestamp"] <= anchor)
    ]
    assert len(window) == 24
    expected = float(np.sqrt((window["error"].to_numpy(dtype=float) ** 2).mean()))
    assert reported == pytest.approx(expected)


def test_strategies_share_one_timeline_and_differ_only_in_refits(inputs, tmp_path):
    """The comparison is only fair if nothing but refit timing varies."""
    config, prices, _ = inputs
    config = deepcopy(config)
    config["backtest"]["evaluation_end_date"] = "2025-01-17"
    frame, _ = build_availability_dataset(prices, config, source_dataset="fixture")
    results = {}
    for name, hook in (
        ("no_retraining", None),
        ("always", lambda issuance, history: True),
    ):
        results[name] = run(
            frame,
            config,
            tmp_path,
            name,
            policy_hook=hook,
            strategy="no_retraining",
        )

    static, refitting = results["no_retraining"], results["always"]
    for column in ("timestamp", "forecast_timestamp", "actual"):
        pd.testing.assert_series_equal(static[column], refitting[column])
    # The first block is issued before any refit, so it must be identical.
    first = static["forecast_timestamp"].min()
    pd.testing.assert_series_equal(
        static.loc[static["forecast_timestamp"] == first, "prediction"],
        refitting.loc[refitting["forecast_timestamp"] == first, "prediction"],
    )
    assert static["model_version"].nunique() == 1
    assert refitting["model_version"].nunique() > 1


def test_refit_cannot_use_actuals_published_after_its_issuance(inputs, tmp_path):
    config, prices, _ = inputs
    config = deepcopy(config)
    config["backtest"]["evaluation_end_date"] = "2025-01-17"
    original, _ = build_availability_dataset(prices, config, source_dataset="fixture")
    windows = generate_backtest_windows_from_config(config)
    second = windows[1].issuance

    mutated_prices = prices.copy(deep=True)
    later = mutated_prices["timestamp"] + pd.Timedelta(hours=1) > second
    mutated_prices.loc[later, "price_de"] += 10000
    mutated, _ = build_availability_dataset(
        mutated_prices, config, source_dataset="fixture"
    )

    hook = lambda issuance, history: True  # noqa: E731 - refit at every issuance
    before = run(original, config, tmp_path, "before_mut", policy_hook=hook)
    after = run(mutated, config, tmp_path, "after_mut", policy_hook=hook)

    issued = before["forecast_timestamp"] <= second
    np.testing.assert_array_equal(
        before.loc[issued, "prediction"], after.loc[issued, "prediction"]
    )
