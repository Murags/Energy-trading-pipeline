"""Core strategy aggregation from small canonical forecast and event logs."""

import numpy as np
import pandas as pd
import pytest

from energy_trading_pipeline.backtesting.forecast_log import build_forecast_log
from energy_trading_pipeline.evaluation.strategy_comparison import (
    calculate_strategy_metrics,
)
from energy_trading_pipeline.retraining.events import (
    RETRAINING_EVENT_COLUMNS,
    build_retraining_events,
)


START = pd.Timestamp("2024-01-01T00:00:00Z")
END = pd.Timestamp("2024-01-03T00:00:00Z")
METRIC_COLUMNS = ["strategy", "rmse", "mae", "retraining_count", "retraining_frequency"]


@pytest.fixture
def forecasts():
    timestamps = pd.date_range(START, periods=4, freq="12h")
    actuals = [1.0, np.nan, 5.0, 7.0]
    predictions = {
        "no_retraining": [0.0, 100.0, 2.0, 3.0],
        "fixed_schedule": [0.0, 100.0, 4.0, 6.0],
        "performance_triggered": [1.0, 100.0, 5.0, 7.0],
    }
    return build_forecast_log(
        pd.DataFrame(
            [
                {
                    "timestamp": timestamp,
                    "forecast_timestamp": timestamp - pd.Timedelta(days=1),
                    "actual": actual,
                    "prediction": prediction,
                    "strategy": strategy,
                    "model_version": "initial_model",
                }
                for strategy, values in predictions.items()
                for timestamp, actual, prediction in zip(timestamps, actuals, values)
            ]
        )
    )


def event_record(timestamp, strategy, model_version):
    performance = strategy == "performance_triggered"
    return {
        "timestamp": timestamp,
        "strategy": strategy,
        "trigger_reason": "rmse_threshold_exceeded" if performance else "scheduled",
        "threshold": 1.0 if performance else np.nan,
        "rolling_rmse": 2.0 if performance else np.nan,
        "training_window_start": timestamp - pd.Timedelta(days=10),
        "training_window_end": timestamp,
        "model_version": model_version,
    }


@pytest.fixture
def events():
    return build_retraining_events(
        pd.DataFrame(
            [
                event_record(START, "fixed_schedule", "scheduled_1"),
                event_record(
                    START + pd.Timedelta(days=1), "fixed_schedule", "scheduled_2"
                ),
                event_record(
                    END - pd.Timedelta(hours=12), "performance_triggered", "triggered_1"
                ),
            ]
        )
    )


def aggregate(forecasts, events, start=START, end=END):
    return calculate_strategy_metrics(
        forecasts, events, evaluation_start=start, evaluation_end=end
    )


def test_known_strategy_metrics(forecasts, events):
    result = aggregate(forecasts, events)
    assert list(result.columns) == METRIC_COLUMNS
    assert set(result["strategy"]) == {
        "no_retraining",
        "fixed_schedule",
        "performance_triggered",
    }
    rows = result.set_index("strategy")
    assert rows.loc["no_retraining", "rmse"] == pytest.approx(np.sqrt(26 / 3))
    assert rows.loc["no_retraining", "mae"] == pytest.approx(8 / 3)
    assert rows.loc["fixed_schedule", "rmse"] == 1.0
    assert rows.loc["fixed_schedule", "mae"] == 1.0
    assert rows.loc["performance_triggered", "rmse"] == 0.0
    assert rows.loc["performance_triggered", "mae"] == 0.0
    assert rows["retraining_count"].to_dict() == {
        "no_retraining": 0,
        "fixed_schedule": 2,
        "performance_triggered": 1,
    }
    assert rows["retraining_frequency"].to_dict() == {
        "no_retraining": 0.0,
        "fixed_schedule": 1.0,
        "performance_triggered": 0.5,
    }


def test_half_open_window_filters_forecasts_and_events(forecasts, events):
    extra = pd.DataFrame(
        [
            event_record(START - pd.Timedelta(hours=1), "fixed_schedule", "before"),
            event_record(END, "fixed_schedule", "after"),
        ]
    )
    events = pd.concat([events, extra], ignore_index=True)
    result = aggregate(forecasts, events, START, START + pd.Timedelta(days=1))
    scheduled = result.set_index("strategy").loc["fixed_schedule"]
    assert scheduled["retraining_count"] == 1
    assert scheduled["retraining_frequency"] == 1.0
    static = result.set_index("strategy").loc["no_retraining"]
    assert static["rmse"] == 1.0
    assert static["mae"] == 1.0


def test_fractional_day_frequency_uses_explicit_duration(forecasts, events):
    result = aggregate(forecasts, events, START, START + pd.Timedelta(hours=6))
    scheduled = result.set_index("strategy").loc["fixed_schedule"]
    assert scheduled["retraining_frequency"] == 4.0


def test_missing_actuals_do_not_change_event_frequency(forecasts, events):
    forecasts["actual"] = np.nan
    result = aggregate(forecasts, events)
    assert result[["rmse", "mae"]].isna().all().all()
    scheduled = result.set_index("strategy").loc["fixed_schedule"]
    assert scheduled["retraining_frequency"] == 1.0


def test_empty_event_log_means_zero_retraining(forecasts, events):
    result = aggregate(forecasts, events.iloc[:0])
    assert (result["retraining_count"] == 0).all()
    assert (result["retraining_frequency"] == 0.0).all()


def test_empty_inputs_preserve_output_schema_and_dtypes(forecasts, events):
    result = aggregate(forecasts.iloc[:0], events.iloc[:0])
    assert result.empty
    assert list(result.columns) == METRIC_COLUMNS
    assert str(result["retraining_count"].dtype) == "int64"
    for column in ("rmse", "mae", "retraining_frequency"):
        assert str(result[column].dtype) == "float64"


def test_unsorted_nondefault_indexes_and_stale_errors_do_not_mutate_inputs(
    forecasts, events
):
    forecasts = forecasts.iloc[::-1].copy()
    forecasts.index = [9] * len(forecasts)
    events = events.iloc[::-1].copy()
    forecasts["error"] = 999.0
    forecasts["squared_error"] = 999.0
    forecasts["absolute_error"] = 999.0
    original_forecasts = forecasts.copy(deep=True)
    original_events = events.copy(deep=True)
    result = aggregate(forecasts, events)
    assert result.set_index("strategy").loc["fixed_schedule", "rmse"] == 1.0
    pd.testing.assert_frame_equal(forecasts, original_forecasts)
    pd.testing.assert_frame_equal(events, original_events)


@pytest.mark.parametrize("bound", ["start", "end"])
@pytest.mark.parametrize("invalid", [pd.NaT, pd.Timestamp("2024-01-01"), "2024-01-01"])
def test_invalid_bounds_fail(forecasts, events, bound, invalid):
    bounds = {"start": START, "end": END}
    bounds[bound] = invalid
    with pytest.raises(ValueError, match="evaluation_.*timezone-aware"):
        aggregate(forecasts, events, **bounds)


@pytest.mark.parametrize("end", [START, START - pd.Timedelta(days=1)])
def test_nonpositive_duration_fails(forecasts, events, end):
    with pytest.raises(
        ValueError, match="evaluation_start must precede evaluation_end"
    ):
        aggregate(forecasts, events, START, end)


def test_timezone_equivalent_bounds_produce_identical_metrics(forecasts, events):
    pd.testing.assert_frame_equal(
        aggregate(forecasts, events),
        aggregate(
            forecasts,
            events,
            START.tz_convert("Europe/Berlin"),
            END.tz_convert("Europe/Berlin"),
        ),
    )


def test_duplicate_forecast_targets_fail(forecasts, events):
    duplicated = pd.concat([forecasts, forecasts.iloc[:1]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate target timestamps"):
        aggregate(duplicated, events)


def test_mismatched_strategy_timeline_fails(forecasts, events):
    forecasts = forecasts.drop(forecasts.index[0])
    with pytest.raises(ValueError, match="same evaluation timeline"):
        aggregate(forecasts, events)


@pytest.mark.parametrize("actual", [99.0, np.nan])
def test_mismatched_actuals_fail(forecasts, events, actual):
    forecasts.loc[forecasts.index[0], "actual"] = actual
    with pytest.raises(ValueError, match="same actuals"):
        aggregate(forecasts, events)


def test_duplicate_events_fail(forecasts, events):
    duplicated = pd.concat([events, events.iloc[:1]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate retraining events"):
        aggregate(forecasts, duplicated)


def test_events_without_a_forecast_strategy_fail(forecasts, events):
    forecasts = forecasts.loc[forecasts["strategy"] != "fixed_schedule"]
    with pytest.raises(ValueError, match="without forecasts"):
        aggregate(forecasts, events)


@pytest.mark.parametrize("column", ["prediction", "actual", "strategy", "timestamp"])
def test_missing_forecast_columns_fail(forecasts, events, column):
    with pytest.raises(ValueError, match="Missing required forecast log columns"):
        aggregate(forecasts.drop(columns=column), events)


@pytest.mark.parametrize("column", RETRAINING_EVENT_COLUMNS)
def test_missing_event_columns_fail(forecasts, events, column):
    with pytest.raises(ValueError, match="Missing required retraining event columns"):
        aggregate(forecasts, events.drop(columns=column))


@pytest.mark.parametrize(
    "column, value", [("prediction", np.nan), ("strategy", "unknown")]
)
def test_invalid_forecast_values_fail(forecasts, events, column, value):
    forecasts.loc[0, column] = value
    with pytest.raises(ValueError, match=column):
        aggregate(forecasts, events)


def test_daylight_saving_frequency_uses_elapsed_utc_days(forecasts, events):
    start = pd.Timestamp("2024-03-31", tz="Europe/Berlin")
    end = pd.Timestamp("2024-04-01", tz="Europe/Berlin")
    shift = start.tz_convert("UTC") - START
    forecasts["timestamp"] += shift
    forecasts["forecast_timestamp"] += shift
    events = pd.DataFrame([event_record(start, "fixed_schedule", "dst_model")])
    scheduled = aggregate(forecasts, events, start, end).set_index("strategy").loc[
        "fixed_schedule"
    ]
    assert scheduled["retraining_count"] == 1
    assert scheduled["retraining_frequency"] == pytest.approx(24 / 23)


def test_empty_selected_window_has_nan_errors_not_zero(forecasts, events):
    result = aggregate(forecasts, events, END, END + pd.Timedelta(days=1))
    assert len(result) == 3
    assert result[["rmse", "mae"]].isna().all().all()
    assert (result["retraining_count"] == 0).all()
    assert (result["retraining_frequency"] == 0.0).all()


def test_entire_strategy_missing_from_selected_window_fails(forecasts, events):
    outside = forecasts["strategy"] == "no_retraining"
    forecasts.loc[outside, "timestamp"] += pd.Timedelta(days=3)
    forecasts.loc[outside, "forecast_timestamp"] += pd.Timedelta(days=3)
    with pytest.raises(ValueError, match="same evaluation timeline"):
        aggregate(forecasts, events)


def test_events_at_end_and_before_start_are_excluded(forecasts, events):
    extra = pd.DataFrame(
        [
            event_record(START - pd.Timedelta(hours=1), "fixed_schedule", "before"),
            event_record(END, "fixed_schedule", "at_end"),
        ]
    )
    result = aggregate(forecasts, pd.concat([events, extra], ignore_index=True))
    scheduled = result.set_index("strategy").loc["fixed_schedule"]
    assert scheduled["retraining_count"] == 2
    assert scheduled["retraining_frequency"] == 1.0


def test_model_version_changes_are_not_inferred_as_retrains(forecasts, events):
    forecasts["model_version"] = [f"version_{index}" for index in range(len(forecasts))]
    result = aggregate(forecasts, events.iloc[:0])
    assert (result["retraining_count"] == 0).all()


@pytest.mark.parametrize("source", ["forecasts", "events"])
def test_non_dataframe_logs_fail(forecasts, events, source):
    inputs = {"forecasts": forecasts, "events": events}
    inputs[source] = []
    with pytest.raises(ValueError, match="DataFrame"):
        aggregate(**inputs)


@pytest.mark.parametrize("source", ["forecasts", "events"])
def test_duplicate_column_names_fail(forecasts, events, source):
    inputs = {"forecasts": forecasts, "events": events}
    frame = inputs[source]
    inputs[source] = pd.concat([frame, frame[["strategy"]]], axis=1)
    with pytest.raises(ValueError, match="Duplicate.*column"):
        aggregate(**inputs)