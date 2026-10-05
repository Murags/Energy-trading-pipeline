"""Decision-time rolling RMSE arithmetic, availability, and validation."""

import numpy as np
import pandas as pd
import pytest

from energy_trading_pipeline.backtesting.forecast_log import build_forecast_log
from energy_trading_pipeline.config.loader import load_config
from energy_trading_pipeline.monitoring.rolling_rmse import calculate_rolling_rmse


def make_history(errors: list[float], *, start: str = "2024-01-01") -> pd.DataFrame:
    """Build hourly canonical records with prediction zero and observed errors."""
    timestamps = pd.date_range(start, periods=len(errors), freq="h", tz="UTC")
    return build_forecast_log(
        pd.DataFrame(
            {
                "timestamp": timestamps,
                "forecast_timestamp": timestamps,
                "prediction": [0.0] * len(errors),
                "actual": errors,
                "strategy": ["fixed_schedule"] * len(errors),
                "model_version": ["model_20240101_000000"] * len(errors),
            }
        )
    )


def test_seven_day_default_requires_168_available_errors():
    history = make_history([3.0, -4.0] * 84)
    decision = history["timestamp"].iloc[-1]

    result = calculate_rolling_rmse(history, decision)

    assert set(result) == {"rolling_rmse"}
    assert result["rolling_rmse"] == pytest.approx(np.sqrt(12.5))
    assert np.isnan(
        calculate_rolling_rmse(history.iloc[:-1], decision)["rolling_rmse"]
    )


def test_window_days_comes_from_experiment_config():
    config = load_config("configs/experiment.yaml")
    history = make_history([2.0] * 168)
    result = calculate_rolling_rmse(
        history,
        history["timestamp"].iloc[-1],
        window_days=config["retraining"]["rolling_rmse_window_days"],
    )
    assert result["rolling_rmse"] == 2.0


def test_custom_window_excludes_older_errors():
    history = make_history([100.0] * 24 + [2.0] * 24)
    result = calculate_rolling_rmse(
        history, history["timestamp"].iloc[-1], window_days=1
    )
    assert result["rolling_rmse"] == 2.0


def test_left_boundary_is_excluded_and_available_decision_error_is_included():
    history = make_history([100.0] + [np.nan] * 23 + [3.0, 1000.0])
    decision = history["timestamp"].iloc[24]
    result = calculate_rolling_rmse(history, decision, window_days=1, min_periods=1)
    assert result["rolling_rmse"] == 3.0


def test_future_errors_cannot_change_an_earlier_decision():
    history = make_history([3.0, -4.0, 1000.0, 2000.0])
    decision = history["timestamp"].iloc[1]
    expected = calculate_rolling_rmse(history.iloc[:2], decision, min_periods=2)

    assert calculate_rolling_rmse(history, decision, min_periods=2) == expected
    history.loc[2:, "error"] = np.inf
    assert calculate_rolling_rmse(history, decision, min_periods=2) == expected


def test_future_errors_do_not_fill_an_insufficient_window():
    history = make_history([2.0] * 200)
    result = calculate_rolling_rmse(history, history["timestamp"].iloc[166])
    assert np.isnan(result["rolling_rmse"])


def test_errors_from_future_issuance_are_unavailable():
    history = make_history([3.0, 1000.0])
    decision = history["timestamp"].iloc[-1]
    history.loc[1, "forecast_timestamp"] = decision + pd.Timedelta(hours=1)
    result = calculate_rolling_rmse(history, decision, min_periods=1)
    assert result["rolling_rmse"] == 3.0


@pytest.mark.parametrize("errors", [[], [np.nan], [3.0, np.nan]])
def test_insufficient_history_is_explicitly_nan(errors):
    result = calculate_rolling_rmse(
        make_history(errors), pd.Timestamp("2024-01-02T00:00:00Z"), min_periods=2
    )
    assert np.isnan(result["rolling_rmse"])


def test_missing_errors_are_not_zero_or_counted_as_observations():
    history = make_history([3.0, np.nan, -4.0])
    result = calculate_rolling_rmse(
        history, history["timestamp"].iloc[-1], min_periods=2
    )
    assert result["rolling_rmse"] == pytest.approx(np.sqrt(12.5))


def test_available_errors_from_previous_model_versions_remain_in_window():
    history = make_history([3.0, -4.0])
    history.loc[1, "model_version"] = "model_20240102_000000"
    result = calculate_rolling_rmse(
        history, history["timestamp"].iloc[-1], min_periods=2
    )
    assert result["rolling_rmse"] == pytest.approx(np.sqrt(12.5))


def test_shuffled_history_and_input_are_preserved():
    history = make_history([3.0, -4.0, 5.0]).iloc[::-1].copy()
    original = history.copy(deep=True)
    result = calculate_rolling_rmse(
        history, pd.Timestamp("2024-01-01T02:00:00Z"), min_periods=3
    )
    assert result["rolling_rmse"] == pytest.approx(np.sqrt(50 / 3))
    pd.testing.assert_frame_equal(history, original)


def test_utc_elapsed_window_is_stable_across_daylight_saving():
    history = make_history([100.0] + [2.0] * 24, start="2024-03-30T01:00:00")
    history["timestamp"] = history["timestamp"].dt.tz_convert("Europe/Berlin")
    history["forecast_timestamp"] = history["forecast_timestamp"].dt.tz_convert(
        "Europe/Berlin"
    )
    result = calculate_rolling_rmse(
        history, history["timestamp"].iloc[-1], window_days=1
    )
    assert result["rolling_rmse"] == 2.0


def test_minimal_timestamp_and_error_input_is_supported():
    history = make_history([3.0, -4.0])
    result = calculate_rolling_rmse(
        history[["timestamp", "error"]], history["timestamp"].iloc[-1], min_periods=2
    )
    assert result["rolling_rmse"] == pytest.approx(np.sqrt(12.5))


def test_timezone_aware_serialized_timestamps_are_supported():
    history = make_history([2.0])
    history["timestamp"] = history["timestamp"].map(pd.Timestamp.isoformat)
    result = calculate_rolling_rmse(
        history, pd.Timestamp("2024-01-01T00:00:00Z"), min_periods=1
    )
    assert result["rolling_rmse"] == 2.0


@pytest.mark.parametrize("window_days", [0, -1, 1.5, True, "7", None])
def test_invalid_window_days_fail_clearly(window_days):
    with pytest.raises(ValueError, match="window_days.*positive integer"):
        calculate_rolling_rmse(
            make_history([]),
            pd.Timestamp("2024-01-01T00:00:00Z"),
            window_days=window_days,
        )


@pytest.mark.parametrize("min_periods", [0, -1, 1.5, True, "2"])
def test_invalid_min_periods_fail_clearly(min_periods):
    with pytest.raises(ValueError, match="min_periods.*positive integer"):
        calculate_rolling_rmse(
            make_history([]),
            pd.Timestamp("2024-01-01T00:00:00Z"),
            min_periods=min_periods,
        )


@pytest.mark.parametrize(
    "decision", [pd.Timestamp("2024-01-01"), pd.NaT, "2024-01-01T00:00:00Z"]
)
def test_invalid_decision_timestamp_is_rejected(decision):
    with pytest.raises(ValueError, match="decision_timestamp.*timezone-aware"):
        calculate_rolling_rmse(make_history([]), decision)


@pytest.mark.parametrize("column", ["timestamp", "forecast_timestamp"])
@pytest.mark.parametrize("invalid", [pd.NaT, "invalid", "2024-01-01", 42])
def test_invalid_history_timestamps_are_rejected(column, invalid):
    history = make_history([2.0])
    history[column] = pd.Series([invalid], dtype=object)
    with pytest.raises(ValueError, match=f"{column}.*timezone-aware"):
        calculate_rolling_rmse(history, pd.Timestamp("2024-01-02T00:00:00Z"))


@pytest.mark.parametrize("invalid", [np.inf, -np.inf, "3", True, 1 + 2j])
def test_invalid_available_errors_are_rejected(invalid):
    history = make_history([2.0])
    history["error"] = [invalid]
    with pytest.raises(ValueError, match="error.*finite real numeric"):
        calculate_rolling_rmse(history, history["timestamp"].iloc[-1], min_periods=1)


@pytest.mark.parametrize("column", ["timestamp", "error"])
def test_missing_required_columns_are_rejected(column):
    history = make_history([]).drop(columns=column)
    with pytest.raises(ValueError, match="Missing required.*columns"):
        calculate_rolling_rmse(history, pd.Timestamp("2024-01-01T00:00:00Z"))


def test_non_dataframe_is_rejected():
    with pytest.raises(ValueError, match="forecast_history.*DataFrame"):
        calculate_rolling_rmse([], pd.Timestamp("2024-01-01T00:00:00Z"))


def test_duplicate_column_names_are_rejected():
    history = make_history([])
    history = pd.concat([history, history[["error"]]], axis=1)
    with pytest.raises(ValueError, match="duplicate column"):
        calculate_rolling_rmse(history, pd.Timestamp("2024-01-01T00:00:00Z"))


def test_multiple_strategies_cannot_be_combined_into_one_metric():
    history = make_history([3.0, -4.0])
    history.loc[1, "strategy"] = "no_retraining"
    with pytest.raises(ValueError, match="single strategy"):
        calculate_rolling_rmse(history, history["timestamp"].iloc[-1], min_periods=1)


def test_duplicate_targets_cannot_inflate_history_count():
    history = make_history([2.0])
    history = pd.concat([history, history], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate target timestamp"):
        calculate_rolling_rmse(history, history["timestamp"].iloc[-1], min_periods=2)


@pytest.mark.parametrize("errors", [[0.0, 0.0], [2, -2], [1e200, -1e200]])
def test_zero_integer_and_large_real_errors_are_numerically_safe(errors):
    history = make_history([0.0, 0.0])
    history["error"] = errors
    result = calculate_rolling_rmse(
        history, history["timestamp"].iloc[-1], min_periods=2
    )
    assert result["rolling_rmse"] == pytest.approx(abs(errors[0]))


def test_expired_errors_cannot_make_history_sufficient():
    history = make_history([2.0] * 168)
    decision = history["timestamp"].iloc[-1] + pd.Timedelta(hours=1)
    assert np.isnan(calculate_rolling_rmse(history, decision)["rolling_rmse"])


def test_time_window_does_not_substitute_the_latest_rows_for_elapsed_days():
    history = make_history([3.0, 4.0])
    history.loc[1, "timestamp"] += pd.Timedelta(days=2)
    history.loc[1, "forecast_timestamp"] = history.loc[1, "timestamp"]
    result = calculate_rolling_rmse(
        history, history["timestamp"].iloc[-1], window_days=1, min_periods=2
    )
    assert np.isnan(result["rolling_rmse"])


def test_unavailable_actuals_delay_default_readiness():
    history = make_history([2.0] * 167 + [np.nan])
    result = calculate_rolling_rmse(history, history["timestamp"].iloc[-1])
    assert np.isnan(result["rolling_rmse"])


def test_future_strategy_and_duplicate_target_do_not_affect_metric():
    history = make_history([3.0, -4.0, 1000.0])
    history.loc[2, "strategy"] = "no_retraining"
    history = pd.concat([history, history.iloc[[2]]], ignore_index=True)
    result = calculate_rolling_rmse(
        history, history["timestamp"].iloc[1], min_periods=2
    )
    assert result["rolling_rmse"] == pytest.approx(np.sqrt(12.5))


def test_future_string_error_does_not_change_numeric_history_validation():
    history = make_history([3.0, -4.0, 1000.0])
    history["error"] = pd.Series([3.0, -4.0, "not_available"], dtype=object)
    result = calculate_rolling_rmse(
        history, history["timestamp"].iloc[1], min_periods=2
    )
    assert result["rolling_rmse"] == pytest.approx(np.sqrt(12.5))


def test_nullable_missing_errors_are_supported():
    history = make_history([3.0, np.nan, -4.0])
    history["error"] = pd.Series([3.0, pd.NA, -4.0], dtype="Float64")
    result = calculate_rolling_rmse(
        history, history["timestamp"].iloc[-1], min_periods=2
    )
    assert result["rolling_rmse"] == pytest.approx(np.sqrt(12.5))


def test_excessive_window_fails_with_clear_timestamp_bounds_message():
    with pytest.raises(ValueError, match="timestamp bounds"):
        calculate_rolling_rmse(
            make_history([]),
            pd.Timestamp("2024-01-01T00:00:00Z"),
            window_days=10**20,
        )