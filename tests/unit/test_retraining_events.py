"""Retraining request handoff and validated local event artifacts."""

import pandas as pd
import pytest

from energy_trading_pipeline.backtesting.forecast_log import build_forecast_log
from energy_trading_pipeline.backtesting.splitter import TimeWindow
from energy_trading_pipeline.retraining.events import (
    RETRAINING_EVENT_COLUMNS,
    build_retraining_events,
    write_retraining_events,
)
from energy_trading_pipeline.retraining.performance_triggered import (
    PerformanceTriggeredPolicy,
)


@pytest.fixture
def event_frame():
    return pd.DataFrame(
        [
            {
                "timestamp": "2024-01-03T01:00:00+01:00",
                "strategy": "performance_triggered",
                "trigger_reason": "rolling_rmse_exceeds_threshold",
                "threshold": 0.5,
                "rolling_rmse": 1.0,
                "training_window_start": "2023-12-30T00:00:00Z",
                "training_window_end": "2024-01-02T00:00:00Z",
                "model_version": "model_20240103_000000",
            }
        ]
    )


def make_history(error=1.0):
    return build_forecast_log(
        pd.DataFrame(
            {
                "timestamp": [pd.Timestamp("2024-01-02T12:00:00Z")],
                "forecast_timestamp": [pd.Timestamp("2024-01-02T00:00:00Z")],
                "prediction": [0.0],
                "actual": [error],
                "strategy": ["performance_triggered"],
                "model_version": ["model_20240101_000000"],
            }
        )
    )


def training_window_at(issuance):
    return TimeWindow(issuance - pd.Timedelta(days=4), issuance - pd.Timedelta(days=1))


def test_performance_hook_hands_off_all_required_event_fields(event_frame):
    events = []
    policy = PerformanceTriggeredPolicy(threshold=0.5, min_periods=1)
    hook = policy.as_policy_hook(
        training_window_provider=training_window_at,
        model_version_provider=lambda issuance: "model_20240103_000000",
        event_logger=events.append,
    )
    assert hook(pd.Timestamp("2024-01-03T01:00:00+01:00"), make_history()) is True
    assert len(events) == 1
    pd.testing.assert_frame_equal(
        build_retraining_events(pd.DataFrame(events)),
        build_retraining_events(event_frame),
    )


@pytest.mark.parametrize("error", [0.0, 0.5, float("nan")])
def test_performance_hook_does_not_log_nontriggers(error):
    events = []
    hook = PerformanceTriggeredPolicy(threshold=0.5, min_periods=1).as_policy_hook(
        training_window_provider=training_window_at,
        model_version_provider=lambda issuance: "model_20240103_000000",
        event_logger=events.append,
    )
    assert hook(pd.Timestamp("2024-01-03T00:00:00Z"), make_history(error)) is False
    assert events == []


@pytest.mark.parametrize(
    "options",
    [
        {"event_logger": [].append},
        {"training_window_provider": training_window_at},
        {"model_version_provider": lambda issuance: "model_20240103_000000"},
        {
            "training_window_provider": training_window_at,
            "model_version_provider": "model_20240103_000000",
            "event_logger": [].append,
        },
    ],
)
def test_performance_hook_requires_all_callable_logging_inputs(options):
    with pytest.raises(ValueError, match="must all be callable"):
        PerformanceTriggeredPolicy(threshold=0.5).as_policy_hook(**options)


@pytest.mark.parametrize("fault", ["future_window", "untyped_window", "model_version"])
def test_performance_hook_rejects_invalid_context_without_advancing(fault):
    policy = PerformanceTriggeredPolicy(threshold=0.5, min_periods=1)
    events = []
    window_provider = training_window_at
    version_provider = lambda issuance: "model_20240103_000000"
    if fault == "future_window":
        window_provider = lambda issuance: TimeWindow(
            issuance, issuance + pd.Timedelta(days=1)
        )
    elif fault == "untyped_window":
        window_provider = lambda issuance: {}
    else:
        version_provider = lambda issuance: ""
    hook = policy.as_policy_hook(
        training_window_provider=window_provider,
        model_version_provider=version_provider,
        event_logger=events.append,
    )
    with pytest.raises(ValueError):
        hook(pd.Timestamp("2024-01-03T00:00:00Z"), make_history())
    assert events == []
    assert policy.should_retrain(
        pd.Timestamp("2024-01-02T12:00:00Z"), make_history()
    ) is True


def test_event_builder_normalizes_orders_and_preserves_input(event_frame):
    earlier = event_frame.copy()
    earlier["timestamp"] = "2024-01-02T00:00:00Z"
    frame = pd.concat([event_frame, earlier], ignore_index=True)
    original = frame.copy(deep=True)
    result = build_retraining_events(frame)
    assert tuple(result.columns) == RETRAINING_EVENT_COLUMNS
    assert result["timestamp"].is_monotonic_increasing
    assert str(result["timestamp"].dtype) == "datetime64[ns, UTC]"
    pd.testing.assert_frame_equal(frame, original)


def test_write_events_round_trips_parquet(event_frame, tmp_path):
    output_path = (
        tmp_path / "logs" / "runs" / "run_20240103_000000"
        / "retraining_events.parquet"
    )
    assert write_retraining_events(event_frame, output_path) == output_path
    pd.testing.assert_frame_equal(
        pd.read_parquet(output_path), build_retraining_events(event_frame)
    )
    write_retraining_events(event_frame, output_path)
    assert len(pd.read_parquet(output_path)) == 1


def test_empty_event_artifact_has_stable_schema(tmp_path):
    empty = pd.DataFrame(columns=RETRAINING_EVENT_COLUMNS)
    result = build_retraining_events(empty)
    assert result.empty
    output_path = tmp_path / "retraining_events.parquet"
    write_retraining_events(empty, output_path)
    pd.testing.assert_frame_equal(pd.read_parquet(output_path), result)


@pytest.mark.parametrize("column", RETRAINING_EVENT_COLUMNS)
def test_events_require_auditable_columns(event_frame, column):
    with pytest.raises(ValueError, match="Missing required retraining event columns"):
        build_retraining_events(event_frame.drop(columns=[column]))


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("strategy", "unknown"),
        ("trigger_reason", ""),
        ("model_version", None),
        ("timestamp", "2024-01-03"),
        ("training_window_start", "2024-01-02T00:00:00Z"),
        ("training_window_end", "2024-01-04T00:00:00Z"),
        ("threshold", -1.0),
        ("threshold", float("nan")),
        ("threshold", float("inf")),
        ("threshold", True),
        ("rolling_rmse", float("nan")),
        ("rolling_rmse", -1.0),
        ("rolling_rmse", 0.5),
    ],
)
def test_invalid_events_fail_before_creating_files(
    event_frame, tmp_path, column, value
):
    frame = event_frame.copy()
    frame[column] = value
    output_path = tmp_path / "not_created" / "retraining_events.parquet"
    with pytest.raises(ValueError):
        write_retraining_events(frame, output_path)
    assert not output_path.parent.exists()


def test_events_reject_unsupported_artifact_format(event_frame, tmp_path):
    with pytest.raises(ValueError, match="parquet"):
        write_retraining_events(event_frame, tmp_path / "events.json")


def test_scheduled_events_can_have_inapplicable_rmse_values(event_frame):
    event_frame["strategy"] = "fixed_schedule"
    event_frame["trigger_reason"] = "fixed_schedule_interval_elapsed"
    event_frame["threshold"] = float("nan")
    event_frame["rolling_rmse"] = float("nan")
    result = build_retraining_events(event_frame)
    assert result["threshold"].isna().all()
    assert result["rolling_rmse"].isna().all()


def test_performance_hook_request_can_be_persisted(tmp_path):
    requests = []
    hook = PerformanceTriggeredPolicy(threshold=0.5, min_periods=1).as_policy_hook(
        training_window_provider=training_window_at,
        model_version_provider=lambda issuance: "model_20240101_000000",
        event_logger=requests.append,
    )
    assert hook(pd.Timestamp("2024-01-03T00:00:00Z"), make_history()) is True
    output_path = tmp_path / "run_20240103_000000" / "retraining_events.parquet"
    write_retraining_events(pd.DataFrame(requests), output_path)
    saved = pd.read_parquet(output_path)
    assert saved.loc[0, "rolling_rmse"] == 1.0
    assert saved.loc[0, "threshold"] == 0.5
    assert saved.loc[0, "model_version"] == "model_20240101_000000"
    assert saved.loc[0, "training_window_end"] < saved.loc[0, "timestamp"]


def test_performance_hook_propagates_logging_failure():
    def failing_logger(event):
        raise OSError("artifact unavailable")

    hook = PerformanceTriggeredPolicy(threshold=0.5, min_periods=1).as_policy_hook(
        training_window_provider=training_window_at,
        model_version_provider=lambda issuance: "model_20240103_000000",
        event_logger=failing_logger,
    )
    with pytest.raises(OSError, match="artifact unavailable"):
        hook(pd.Timestamp("2024-01-03T00:00:00Z"), make_history())


def test_performance_hook_rejects_future_errors_without_logging():
    requests = []
    hook = PerformanceTriggeredPolicy(threshold=0.5, min_periods=1).as_policy_hook(
        training_window_provider=training_window_at,
        model_version_provider=lambda issuance: "model_20240103_000000",
        event_logger=requests.append,
    )
    with pytest.raises(ValueError, match="must not follow decision_timestamp"):
        hook(pd.Timestamp("2024-01-02T00:00:00Z"), make_history())
    assert requests == []


@pytest.mark.parametrize("value", [None, "", "   ", 123])
@pytest.mark.parametrize("column", ["strategy", "trigger_reason", "model_version"])
def test_events_reject_missing_or_invalid_identifiers(event_frame, column, value):
    event_frame[column] = value
    with pytest.raises(ValueError, match="nonempty strings"):
        build_retraining_events(event_frame)


@pytest.mark.parametrize("value", [None, "not-a-time", "2024-01-01", 123])
@pytest.mark.parametrize(
    "column", ["timestamp", "training_window_start", "training_window_end"]
)
def test_events_reject_invalid_timestamp_values(event_frame, column, value):
    event_frame[column] = value
    with pytest.raises(ValueError, match="timezone-aware timestamps"):
        build_retraining_events(event_frame)


def test_event_builder_rejects_duplicate_columns(event_frame):
    duplicated = pd.concat([event_frame, event_frame[["timestamp"]]], axis=1)
    with pytest.raises(ValueError, match="Duplicate retraining event column"):
        build_retraining_events(duplicated)


def test_event_builder_requires_dataframe():
    with pytest.raises(ValueError, match="pandas DataFrame"):
        build_retraining_events([])