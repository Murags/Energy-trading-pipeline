"""Availability dependencies, civil-day issuance and strict scientific inputs."""

from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from energy_trading_pipeline.backtesting.splitter import (
    BacktestWindow,
    day_ahead_issuance,
    generate_backtest_windows_from_config,
)
from energy_trading_pipeline.features.availability import (
    availability_contract,
    build_availability_dataset,
    validate_availability_frame,
)
from energy_trading_pipeline.features.calendar_features import build_calendar_features
from energy_trading_pipeline.features.rolling_features import build_rolling_features
from energy_trading_pipeline.models.trainer import (
    TrainingWindow,
    select_training_window,
)


@pytest.fixture
def config():
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
    return config


@pytest.fixture
def prices():
    timestamps = pd.date_range("2025-01-01", "2025-01-18", freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "price_de": 50 + np.sin(np.arange(len(timestamps))),
            "price_fr": 40.0,
        }
    )


def test_preparation_provenance_and_warmup(config, prices):
    frame, metadata = build_availability_dataset(
        prices, config, source_dataset="fixture"
    )
    assert metadata["warmup_rows_dropped"] == 168
    assert len(frame) == len(prices) - 168
    assert (
        frame["actual_available_at"] == frame["timestamp"] + pd.Timedelta(hours=1)
    ).all()
    assert (
        frame["feature_available_at"] == frame["timestamp"] - pd.Timedelta(hours=47)
    ).all()
    assert (frame["feature_available_at"] <= frame["forecast_timestamp"]).all()
    assert frame["hour"].equals(
        frame["timestamp"].dt.tz_convert("Europe/Berlin").dt.hour.astype("int16")
    )
    assert (
        "not an observed publication time"
        in metadata["availability_contract"]["limitations"]
    )
    validate_availability_frame(frame, config, config["backtest"]["feature_columns"])


@pytest.mark.parametrize(
    "day,hours", [("2025-03-30", 23), ("2025-10-26", 25), ("2025-01-15", 24)]
)
def test_full_civil_days(config, day, hours):
    config["backtest"].update(evaluation_start_date=day, evaluation_end_date=day)
    (window,) = generate_backtest_windows_from_config(config)
    assert (window.forecast.end - window.forecast.start) / pd.Timedelta(
        hours=1
    ) == hours
    local_issue = window.issuance.tz_convert("Europe/Berlin")
    assert local_issue.hour == 10
    assert local_issue.date() == (pd.Timestamp(day) - pd.Timedelta(days=1)).date()
    assert window.validation.end == window.issuance
    assert window.train.end == window.validation.start


@pytest.mark.parametrize("day", ["2025-03-31", "2025-10-27"])
def test_invalid_dst_issue_hour(config, day):
    config["backtest"]["issue_hour"] = 2
    with pytest.raises(ValueError, match="Invalid or ambiguous"):
        day_ahead_issuance(pd.Timestamp(day).date(), config["backtest"])


@pytest.mark.parametrize("value", [10.5, True, -1, 24, "10:30"])
def test_non_whole_issue_hours_rejected(config, value):
    config["backtest"]["issue_hour"] = value
    with pytest.raises(ValueError, match="issue_hour"):
        generate_backtest_windows_from_config(config)


@pytest.mark.parametrize("value", [pd.Timestamp("2025-01-14"), pd.NaT])
def test_explicit_issuance_rejects_naive_and_nat(config, value):
    window = generate_backtest_windows_from_config(config)[0]
    with pytest.raises(ValueError, match="timezone-aware"):
        BacktestWindow(window.train, window.validation, window.forecast, value)


@pytest.mark.parametrize("mutation", ["gap", "duplicate", "nan", "infinity"])
def test_bad_source_is_not_silently_dropped(config, prices, mutation):
    if mutation == "gap":
        prices = prices.drop(200)
    elif mutation == "duplicate":
        prices = pd.concat([prices, prices.iloc[[200]]])
    else:
        prices.loc[200, "price_de"] = np.nan if mutation == "nan" else np.inf
    with pytest.raises(ValueError):
        build_availability_dataset(prices, config, source_dataset="fixture")


@pytest.mark.parametrize(
    "key,value",
    [
        ("weather_columns", ["temperature"]),
        ("grid_columns", ["load"]),
        ("lag_hours", [24]),
        ("rolling_shift_hours", 1),
        ("calendar_timezone", "UTC"),
        ("typo", 1),
    ],
)
def test_unsupported_or_unavailable_features_fail(config, prices, key, value):
    config["features"][key] = value
    with pytest.raises(ValueError):
        build_availability_dataset(prices, config, source_dataset="fixture")


def test_shifted_rolling_values_and_timezone(config, prices):
    prices["spread"] = prices["price_de"] - prices["price_fr"]
    frame, metadata = build_rolling_features(prices, [24], shift_hours=48)
    assert frame.loc[71, "spread_rolling_mean_24"] == pytest.approx(
        prices.loc[:23, "spread"].mean()
    )
    assert metadata["min_history_hours"] == 71
    calendar, metadata = build_calendar_features(prices, timezone="Europe/Berlin")
    assert calendar.loc[0, "hour"] == 1
    assert metadata["timezone"] == "Europe/Berlin"


def test_trainer_never_models_provenance(config, prices):
    frame, metadata = build_availability_dataset(
        prices, config, source_dataset="fixture"
    )
    window = TrainingWindow.from_config(
        {
            "train_start_date": "2025-01-09",
            "train_end_date": "2025-01-10",
            "validation_start_date": "2025-01-11",
            "validation_end_date": "2025-01-12",
        }
    )
    split = select_training_window(frame, window)
    assert split.feature_columns == metadata["feature_columns"]
    for name in ("forecast_timestamp", "feature_available_at", "actual_available_at"):
        with pytest.raises(ValueError, match="predictors"):
            select_training_window(frame, window, feature_columns=[name])


def _issuance_config(config):
    """Add issuance-relative predictors to a day-ahead config."""
    config = deepcopy(config)
    config["features"]["issuance_window_hours"] = [24]
    config["backtest"]["feature_columns"] = config["backtest"]["feature_columns"] + [
        f"{column}_issuance_{statistic}_24"
        for column in ("spread", "price_de", "price_fr")
        for statistic in ("mean", "std")
    ] + [f"{column}_issuance_last" for column in ("spread", "price_de", "price_fr")]
    return config


def test_issuance_features_summarize_only_history_usable_at_issuance(config, prices):
    config = _issuance_config(config)

    frame, _ = build_availability_dataset(prices, config, source_dataset="fixture")

    block = frame[frame["forecast_timestamp"] == frame["forecast_timestamp"].iloc[-1]]
    issuance = block["forecast_timestamp"].iloc[0]
    newest = issuance - pd.Timedelta(hours=1)
    spread = prices.assign(spread=prices["price_de"] - prices["price_fr"])
    window = spread[
        (spread["timestamp"] >= newest - pd.Timedelta(hours=23))
        & (spread["timestamp"] <= newest)
    ]

    assert len(window) == 24
    assert window["timestamp"].max() < issuance
    assert block["spread_issuance_mean_24"].nunique() == 1
    assert block["spread_issuance_mean_24"].iloc[0] == pytest.approx(
        window["spread"].mean()
    )
    assert block["spread_issuance_last"].iloc[0] == pytest.approx(
        window["spread"].iloc[-1]
    )
    # Usable exactly at issuance, never after it.
    assert (block["feature_available_at"] == issuance).all()
    assert (frame["feature_available_at"] <= frame["forecast_timestamp"]).all()


def test_issuance_features_ignore_prices_published_after_issuance(config, prices):
    """Mutating anything usable only after an issuance must not move its features."""
    config = _issuance_config(config)
    original, _ = build_availability_dataset(prices, config, source_dataset="fixture")
    issuance = original["forecast_timestamp"].iloc[-1]

    mutated_prices = prices.copy(deep=True)
    later = mutated_prices["timestamp"] + pd.Timedelta(hours=1) > issuance
    assert later.any()
    mutated_prices.loc[later, "price_de"] += 10_000
    mutated, _ = build_availability_dataset(
        mutated_prices, config, source_dataset="fixture"
    )

    columns = [c for c in original.columns if "issuance" in c and c != "forecast_timestamp"]
    selected = original["forecast_timestamp"] == issuance
    pd.testing.assert_frame_equal(
        original.loc[selected, columns], mutated.loc[selected, columns]
    )


def test_issuance_windows_must_be_complete(config, prices):
    config = _issuance_config(config)
    config["features"]["issuance_window_hours"] = [24 * 365]

    # No issuance has a full year of history in the fixture, so nothing survives.
    frame, metadata = build_availability_dataset(
        prices, config, source_dataset="fixture"
    )
    assert frame.empty
    assert metadata["issuance_warmup_rows_dropped"] > 0


@pytest.mark.parametrize("windows", [[], [0], [1], [24, 24], ["24"], [True], 24])
def test_invalid_issuance_windows_fail_clearly(config, prices, windows):
    config = deepcopy(config)
    config["features"]["issuance_window_hours"] = windows
    with pytest.raises(ValueError, match="issuance_window_hours"):
        availability_contract(config)


WEATHER_COLUMNS = ["temperature_2m_c_de_mean", "wind_speed_100m_m_s_de_weighted"]


def _weather(prices):
    """Hourly weather covering exactly the price timestamps."""
    return pd.DataFrame(
        {
            "timestamp": prices["timestamp"],
            "temperature_2m_c_de_mean": np.linspace(0, 20, len(prices)),
            "wind_speed_100m_m_s_de_weighted": np.linspace(2, 12, len(prices)),
        }
    )


def _foresight_config(config):
    config = deepcopy(config)
    config["features"]["perfect_foresight_weather"] = True
    config["features"]["weather_columns"] = WEATHER_COLUMNS
    config["backtest"]["feature_columns"] = (
        config["backtest"]["feature_columns"] + WEATHER_COLUMNS
    )
    return config


def test_day_ahead_weather_requires_declaring_the_perfect_foresight_bound(config):
    """Weather must never enter an operational day-ahead run unannounced."""
    config = deepcopy(config)
    config["features"]["weather_columns"] = WEATHER_COLUMNS

    with pytest.raises(ValueError, match="perfect_foresight_weather"):
        availability_contract(config)


def test_perfect_foresight_requires_weather_columns(config):
    config = deepcopy(config)
    config["features"]["perfect_foresight_weather"] = True
    with pytest.raises(ValueError, match="requires weather_columns"):
        availability_contract(config)


def test_perfect_foresight_contract_labels_itself_as_a_bound(config):
    contract = availability_contract(_foresight_config(config))

    assert contract["evaluation_purpose"] == "perfect_foresight_bound_not_operational"
    assert "UNAVAILABLE_AT_ISSUANCE" in contract["weather_usable_after"]
    assert "PERFECT FORESIGHT" in contract["limitations"]
    assert "never be reported as day-ahead forecast accuracy" in contract["limitations"]


def test_perfect_foresight_records_weather_as_unavailable_at_issuance(config, prices):
    """The artifact must state the truth even though the experiment allows it."""
    config = _foresight_config(config)

    frame, metadata = build_availability_dataset(
        prices, config, source_dataset="fixture", weather=_weather(prices)
    )

    assert metadata["perfect_foresight_weather"] is True
    assert metadata["evaluation_purpose"] == "perfect_foresight_bound_not_operational"
    # Delivery-hour weather is known only at the delivery hour, and the
    # provenance says so rather than pretending it arrived at issuance.
    assert (frame["feature_available_at"] == frame["timestamp"]).all()
    assert (frame["feature_available_at"] > frame["forecast_timestamp"]).any()
    validate_availability_frame(frame, config, config["backtest"]["feature_columns"])


def test_perfect_foresight_weather_must_cover_every_delivery_hour(config, prices):
    config = _foresight_config(config)
    weather = _weather(prices).iloc[:-50]

    with pytest.raises(ValueError, match="cover every prepared delivery hour"):
        build_availability_dataset(
            prices, config, source_dataset="fixture", weather=weather
        )


def test_perfect_foresight_requires_a_weather_frame(config, prices):
    config = _foresight_config(config)
    with pytest.raises(ValueError, match="requires a weather frame"):
        build_availability_dataset(prices, config, source_dataset="fixture")


PUBLISHED_COLUMNS = ["forecast_pv_wind_de", "forecast_generation_total_de"]


def _published(prices):
    return pd.DataFrame(
        {
            "timestamp": prices["timestamp"],
            "forecast_pv_wind_de": np.linspace(5000, 40000, len(prices)),
            "forecast_generation_total_de": np.linspace(30000, 70000, len(prices)),
        }
    )


def _published_config(config):
    config = deepcopy(config)
    config["backtest"]["issue_hour"] = 18
    config["features"]["day_ahead_forecast_columns"] = PUBLISHED_COLUMNS
    config["backtest"]["feature_columns"] = (
        config["backtest"]["feature_columns"] + PUBLISHED_COLUMNS
    )
    return config


def test_published_forecasts_require_issuance_after_the_regulated_deadline(config):
    """Issuing before 18:00 would use a publication not yet guaranteed to exist."""
    config = _published_config(config)
    config["backtest"]["issue_hour"] = 10

    with pytest.raises(ValueError, match="issue_hour of at least 18"):
        availability_contract(config)


def test_published_forecast_contract_records_its_legal_basis(config):
    contract = availability_contract(_published_config(config))

    assert contract["day_ahead_forecast_deadline_hour"] == 18
    assert "543/2013" in contract["day_ahead_forecast_basis"]
    assert "not retrospectively updated" in contract["day_ahead_forecast_basis"]


def test_published_forecasts_are_available_exactly_at_issuance(config, prices):
    config = _published_config(config)

    frame, metadata = build_availability_dataset(
        prices, config, source_dataset="fixture",
        day_ahead_forecasts=_published(prices),
    )

    assert set(PUBLISHED_COLUMNS).issubset(frame.columns)
    # Published by the deadline on D-1, so usable at issuance but never earlier.
    assert (frame["feature_available_at"] == frame["forecast_timestamp"]).all()
    assert (frame["feature_available_at"] <= frame["forecast_timestamp"]).all()
    assert "543/2013" in metadata["day_ahead_forecast_basis"]
    validate_availability_frame(frame, config, config["backtest"]["feature_columns"])


def test_published_forecasts_must_cover_every_delivery_hour(config, prices):
    config = _published_config(config)
    with pytest.raises(ValueError, match="cover every prepared delivery hour"):
        build_availability_dataset(
            prices, config, source_dataset="fixture",
            day_ahead_forecasts=_published(prices).iloc[:-40],
        )


def test_published_forecasts_require_the_frame(config, prices):
    config = _published_config(config)
    with pytest.raises(ValueError, match="day_ahead_forecasts frame"):
        build_availability_dataset(prices, config, source_dataset="fixture")
