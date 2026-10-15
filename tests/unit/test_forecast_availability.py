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
