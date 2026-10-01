"""Independent timestamp-membership and invalid-input tests for backtest windows."""

from collections import Counter
from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from energy_trading_pipeline.backtesting.splitter import (
    BacktestWindow,
    TimeWindow,
    generate_backtest_windows,
    generate_backtest_windows_from_config,
)
from energy_trading_pipeline.config.loader import load_config


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARGUMENTS = {
    "start_date": "2023-01-06",
    "end_date": "2023-01-08",
    "train_window_days": 3,
    "validation_window_days": 1,
    "forecast_horizon_hours": 24,
}
BACKTEST_CONFIG = {
    "evaluation_start_date": "2023-01-06",
    "evaluation_end_date": "2023-01-08",
    "train_window_days": 3,
    "validation_window_days": 1,
    "forecast_horizon_hours": 24,
}


def hourly_timestamps(first_hour: str, count: int) -> list[datetime]:
    """Construct expected observations independently of splitter endpoints/pandas."""
    first = datetime.fromisoformat(first_hour).replace(tzinfo=timezone.utc)
    return [first + timedelta(hours=index) for index in range(count)]


def members(window: TimeWindow, timestamps: list[datetime]) -> list[datetime]:
    """Select actual row identities using the documented half-open contract."""
    return [stamp for stamp in timestamps if window.start <= stamp < window.end]


def test_daily_windows_select_independently_declared_train_validation_forecast_rows():
    windows = generate_backtest_windows(**ARGUMENTS)
    observations = hourly_timestamps("2023-01-01", 24 * 10)
    expected_starts = [
        ("2023-01-02", "2023-01-05", "2023-01-06"),
        ("2023-01-03", "2023-01-06", "2023-01-07"),
        ("2023-01-04", "2023-01-07", "2023-01-08"),
    ]

    assert len(windows) == 3
    for window, (train_day, validation_day, forecast_day) in zip(
        windows, expected_starts, strict=True
    ):
        train = members(window.train, observations)
        validation = members(window.validation, observations)
        forecast = members(window.forecast, observations)
        assert train == hourly_timestamps(train_day, 72)
        assert validation == hourly_timestamps(validation_day, 24)
        assert forecast == hourly_timestamps(forecast_day, 24)
        assert set(train).isdisjoint(validation + forecast)
        assert max(train) < min(validation) <= max(validation) < min(forecast)
        assert window.train.end == window.validation.start
        assert window.validation.end == window.forecast.start
        for interval in (window.train, window.validation, window.forecast):
            assert str(interval.start.tz) == str(interval.end.tz) == "UTC"

    # Walk-forward history may include earlier evaluation observations.
    assert windows[0].forecast.start in members(windows[2].train, observations)


@pytest.mark.parametrize("horizon", [1, 5, 24, 25, 48, 72, 100])
def test_every_evaluation_hour_is_forecast_once_and_only_once(horizon):
    windows = generate_backtest_windows(
        **{**ARGUMENTS, "forecast_horizon_hours": horizon}
    )
    observations = hourly_timestamps("2023-01-05", 24 * 5)
    expected = hourly_timestamps("2023-01-06", 72)
    selected = [
        stamp
        for window in windows
        for stamp in members(window.forecast, observations)
    ]

    assert selected == expected
    assert Counter(selected) == Counter(expected)
    assert len(windows) == (72 + horizon - 1) // horizon
    assert windows[-1].forecast.end == pd.Timestamp("2023-01-09", tz="UTC")
    for previous, current in zip(windows, windows[1:]):
        assert previous.forecast.end == current.forecast.start
    for window in windows[:-1]:
        assert window.forecast.end - window.forecast.start == timedelta(hours=horizon)


def test_subdaily_partial_block_has_exact_history_and_forecast_membership():
    windows = generate_backtest_windows(
        "2023-01-06", "2023-01-06", 3, 7, validation_window_days=2
    )
    observations = hourly_timestamps("2022-12-31", 24 * 9)
    last = windows[-1]
    assert len(windows) == 4
    assert members(last.train, observations) == hourly_timestamps(
        "2023-01-01T21:00", 72
    )
    assert members(last.validation, observations) == hourly_timestamps(
        "2023-01-04T21:00", 48
    )
    assert members(last.forecast, observations) == hourly_timestamps(
        "2023-01-06T21:00", 3
    )


def test_shared_endpoints_belong_only_to_the_next_interval():
    window = generate_backtest_windows(**ARGUMENTS)[0]
    boundary_rows = [
        pd.Timestamp("2023-01-02", tz="UTC") - pd.Timedelta(nanoseconds=1),
        pd.Timestamp("2023-01-02", tz="UTC"),
        pd.Timestamp("2023-01-05", tz="UTC") - pd.Timedelta(nanoseconds=1),
        pd.Timestamp("2023-01-05", tz="UTC"),
        pd.Timestamp("2023-01-06", tz="UTC"),
        pd.Timestamp("2023-01-07", tz="UTC"),
    ]
    assert members(window.train, boundary_rows) == boundary_rows[1:3]
    assert members(window.validation, boundary_rows) == boundary_rows[3:4]
    assert members(window.forecast, boundary_rows) == boundary_rows[4:5]


@pytest.mark.parametrize(
    "day", ["2023-03-26", "2023-10-29", "2024-02-29", "2023-12-31"]
)
def test_one_day_debug_runs_have_24_utc_hours_across_calendar_boundaries(day):
    windows = generate_backtest_windows(day, day, 1, 1, validation_window_days=1)
    expected = hourly_timestamps(day, 24)
    assert len(windows) == 24
    assert [window.forecast.start for window in windows] == expected
    assert windows[-1].forecast.end == expected[-1] + timedelta(hours=1)


def test_generation_is_deterministic_and_accepts_calendar_date_objects():
    expected = generate_backtest_windows(**ARGUMENTS)
    assert generate_backtest_windows(**ARGUMENTS) == expected
    assert generate_backtest_windows(
        date(2023, 1, 6), date(2023, 1, 8), 3, 24, validation_window_days=1
    ) == expected
    with pytest.raises(FrozenInstanceError):
        expected[0].train.start = pd.Timestamp("2020-01-01", tz="UTC")
    with pytest.raises(FrozenInstanceError):
        expected[0].forecast = expected[0].train


@pytest.mark.parametrize("field", ["start_date", "end_date"])
@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "not-a-date",
        "2023-02-29",
        "2023-13-01",
        "2023-1-06",
        "20230106",
        "2023-W01-5",
        "06/01/2023",
        " 2023-01-06",
        "2023-01-06 ",
        "2023-01-06T00:00:00Z",
        "2023-01-06 12:30",
        datetime(2023, 1, 6),
        datetime(2023, 1, 6, tzinfo=timezone.utc),
        pd.Timestamp("2023-01-06", tz="UTC"),
        pd.NaT,
        20230106,
        True,
        [],
    ],
)
def test_invalid_calendar_bounds_fail_at_call_time(field, value):
    with pytest.raises(ValueError, match=field):
        generate_backtest_windows(**{**ARGUMENTS, field: value})


def test_reversed_dates_fail_clearly():
    with pytest.raises(ValueError, match="end_date must not precede start_date"):
        generate_backtest_windows(**{**ARGUMENTS, "end_date": "2023-01-05"})


@pytest.mark.parametrize(
    "field", ["train_window_days", "validation_window_days", "forecast_horizon_hours"]
)
@pytest.mark.parametrize(
    "value",
    [None, 0, -1, True, False, 1.5, 1.0, "3", float("nan"), float("inf"), []],
)
def test_invalid_durations_fail_without_coercion(field, value):
    with pytest.raises(ValueError, match=f"{field} must be a positive integer"):
        generate_backtest_windows(**{**ARGUMENTS, field: value})


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"start_date": "0001-01-01"}, "start_date.*timestamp limits"),
        ({"end_date": date(9999, 12, 31)}, "end_date.*timestamp limits"),
        ({"end_date": "2262-04-11"}, "end_date exclusive endpoint"),
        (
            {"start_date": "1677-09-22", "end_date": "1677-09-22"},
            "validation_window_days.*timestamp limits",
        ),
        (
            {"start_date": "1677-09-23", "end_date": "1677-09-23"},
            "train_window_days.*timestamp limits",
        ),
        ({"train_window_days": 10**30}, "train_window_days.*duration limits"),
        ({"validation_window_days": 10**30}, "validation_window_days.*duration limits"),
        ({"forecast_horizon_hours": 10**30}, "forecast_horizon_hours.*duration limits"),
        # pandas 3 can construct these at second resolution, but subsequent
        # nanosecond arithmetic must fail here with the setting's name.
        ({"train_window_days": 106752}, "train_window_days.*duration limits"),
        ({"validation_window_days": 106752}, "validation_window_days.*duration limits"),
        ({"forecast_horizon_hours": 2562048}, "forecast_horizon_hours.*duration limits"),
    ],
)
def test_unrepresentable_dates_durations_and_arithmetic_fail_before_return(
    overrides, message
):
    with pytest.raises(ValueError, match=message):
        generate_backtest_windows(**{**ARGUMENTS, **overrides})


def test_last_forecast_is_clipped_before_horizon_arithmetic_can_overflow():
    windows = generate_backtest_windows(
        "2262-04-10", "2262-04-10", 1, 240, validation_window_days=1
    )
    assert len(windows) == 1
    assert windows[0].forecast.end == pd.Timestamp("2262-04-11", tz="UTC")


def test_wide_evaluation_range_does_not_overflow_timedelta_subtraction():
    windows = generate_backtest_windows(
        "1700-01-01", "2200-01-01", 1, 2_000_000, validation_window_days=1
    )
    assert len(windows) == 3
    assert windows[0].forecast.start == pd.Timestamp("1700-01-01", tz="UTC")
    assert windows[-1].forecast.end == pd.Timestamp("2200-01-02", tz="UTC")
    assert all(a.forecast.end == b.forecast.start for a, b in zip(windows, windows[1:]))


@pytest.mark.parametrize(
    "config_path", ["configs/experiment.yaml", "tests/fixtures/sample_config.yaml"]
)
def test_sample_configs_match_direct_generation_and_keep_baseline_dates(config_path):
    config = load_config(PROJECT_ROOT / config_path)
    original = deepcopy(config)
    assert config["backtest"] == BACKTEST_CONFIG
    assert generate_backtest_windows_from_config(config) == generate_backtest_windows(
        **ARGUMENTS
    )
    assert config == original
    assert config["dates"]["train_end_date"] == "2023-01-06"
    assert config["dates"]["validation_start_date"] == "2023-01-07"


@pytest.mark.parametrize("value", [None, [], "backtest", 42])
def test_non_mapping_config_fails_clearly(value):
    with pytest.raises(ValueError, match="config.*mapping"):
        generate_backtest_windows_from_config(value)


@pytest.mark.parametrize(
    "config", [{}, {"backtest": None}, {"backtest": []}, {"backtest": "invalid"}]
)
def test_missing_or_non_mapping_backtest_section_fails(config):
    with pytest.raises(ValueError, match="config.backtest.*mapping"):
        generate_backtest_windows_from_config(config)


@pytest.mark.parametrize("field", list(BACKTEST_CONFIG))
def test_each_backtest_setting_is_required_even_if_other_sections_supply_it(field):
    backtest = {key: value for key, value in BACKTEST_CONFIG.items() if key != field}
    with pytest.raises(ValueError, match=f"Missing required backtest setting.*{field}"):
        generate_backtest_windows_from_config(
            {"backtest": backtest, "dates": BACKTEST_CONFIG}
        )


@pytest.mark.parametrize("field", list(BACKTEST_CONFIG))
def test_config_invalid_values_identify_the_setting(field):
    with pytest.raises(ValueError, match=field):
        generate_backtest_windows_from_config(
            {"backtest": {**BACKTEST_CONFIG, field: None}}
        )


def test_config_reversed_evaluation_dates_fail_clearly():
    with pytest.raises(ValueError, match="evaluation_end_date.*evaluation_start_date"):
        generate_backtest_windows_from_config(
            {"backtest": {**BACKTEST_CONFIG, "evaluation_end_date": "2023-01-05"}}
        )


def test_time_window_normalizes_aware_timestamps_to_utc():
    window = TimeWindow(
        pd.Timestamp("2023-01-06T01:00:00+01:00"),
        pd.Timestamp("2023-01-06T02:00:00+01:00"),
    )
    assert window.start == pd.Timestamp("2023-01-06T00:00:00Z")
    assert str(window.start.tz) == str(window.end.tz) == "UTC"


@pytest.mark.parametrize("field", ["start", "end"])
@pytest.mark.parametrize(
    "value",
    [
        None,
        pd.NaT,
        "2023-01-06",
        pd.Timestamp("2023-01-06"),
        pd.Timestamp("9999-01-01", tz="UTC"),
    ],
)
def test_time_window_rejects_invalid_endpoints(field, value):
    endpoints = {
        "start": pd.Timestamp("2023-01-06", tz="UTC"),
        "end": pd.Timestamp("2023-01-07", tz="UTC"),
        field: value,
    }
    with pytest.raises(ValueError, match=f"TimeWindow.{field}"):
        TimeWindow(**endpoints)


@pytest.mark.parametrize("end", ["2023-01-06", "2023-01-05"])
def test_time_window_rejects_empty_and_inverted_intervals(end):
    with pytest.raises(ValueError, match="end must be strictly after"):
        TimeWindow(pd.Timestamp("2023-01-06", tz="UTC"), pd.Timestamp(end, tz="UTC"))


@pytest.mark.parametrize("field", ["train", "validation", "forecast"])
def test_backtest_window_rejects_non_window_components(field):
    window = generate_backtest_windows(**ARGUMENTS)[0]
    with pytest.raises(ValueError, match=f"BacktestWindow.{field}"):
        BacktestWindow(**{**vars(window), field: None})


def test_backtest_window_rejects_overlap_or_reversed_interval_order():
    window = generate_backtest_windows(**ARGUMENTS)[0]
    with pytest.raises(ValueError, match="train.end.*validation.start"):
        BacktestWindow(window.validation, window.train, window.forecast)
    with pytest.raises(ValueError, match="validation.end.*forecast.start"):
        BacktestWindow(window.train, window.validation, window.validation)
