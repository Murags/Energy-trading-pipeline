"""Retraining policy contract and the static no-retraining strategy."""

import pandas as pd
import pytest

from energy_trading_pipeline.backtesting.forecast_log import build_forecast_log
from energy_trading_pipeline.backtesting.splitter import TimeWindow
from energy_trading_pipeline.config.loader import load_config
from energy_trading_pipeline.retraining.fixed_schedule import FixedSchedulePolicy
from energy_trading_pipeline.retraining.no_retraining import NoRetrainingPolicy
from energy_trading_pipeline.retraining.performance_triggered import (
    PerformanceTriggeredPolicy,
)
from energy_trading_pipeline.retraining.policies import RetrainingPolicy


def make_history(timestamps: list[str], *, strategy: str = "no_retraining") -> pd.DataFrame:
    """Build a canonical forecast log with available actuals."""
    return build_forecast_log(
        pd.DataFrame(
            {
                "timestamp": pd.to_datetime(timestamps, utc=True),
                "forecast_timestamp": pd.to_datetime(timestamps, utc=True),
                "prediction": [1.0] * len(timestamps),
                "actual": [2.0] * len(timestamps),
                "strategy": [strategy] * len(timestamps),
                "model_version": ["model_20240101_000000"] * len(timestamps),
            }
        )
    )


@pytest.fixture
def empty_history() -> pd.DataFrame:
    return make_history([])


def test_no_retraining_never_triggers_across_decision_timestamps():
    policy = NoRetrainingPolicy()
    issuances = pd.date_range("2024-01-02", periods=5, freq="24h", tz="UTC")
    history = make_history([])
    decisions = []
    for issuance in issuances:
        decisions.append(policy.should_retrain(issuance, history))
        history = make_history(
            [timestamp.isoformat() for timestamp in issuances[: len(decisions)]]
        )
    assert decisions == [False] * len(issuances)


def test_strategy_identifier_is_stable_and_canonical():
    assert NoRetrainingPolicy.strategy == "no_retraining"
    assert NoRetrainingPolicy().strategy == "no_retraining"


def test_policy_hook_matches_backtest_runner_contract(empty_history):
    hook = NoRetrainingPolicy().as_policy_hook()
    decision = hook(pd.Timestamp("2024-01-02T00:00:00Z"), empty_history)
    assert decision is False


def test_decision_timestamp_must_be_timezone_aware(empty_history):
    policy = NoRetrainingPolicy()
    with pytest.raises(ValueError):
        policy.should_retrain(pd.Timestamp("2024-01-02T00:00:00"), empty_history)
    with pytest.raises(ValueError):
        policy.should_retrain("2024-01-02T00:00:00Z", empty_history)


def test_non_utc_decision_timestamps_are_normalized():
    policy = NoRetrainingPolicy()
    assert (
        policy.should_retrain(
            pd.Timestamp("2024-01-02T01:00:00+01:00"), make_history([])
        )
        is False
    )


def test_forecast_history_must_use_canonical_columns():
    policy = NoRetrainingPolicy()
    history = make_history(["2024-01-01T00:00:00Z"]).drop(columns=["squared_error"])
    with pytest.raises(ValueError):
        policy.should_retrain(pd.Timestamp("2024-01-02T00:00:00Z"), history)


def test_history_after_decision_timestamp_is_rejected():
    policy = NoRetrainingPolicy()
    history = make_history(["2024-01-03T00:00:00Z"])
    with pytest.raises(ValueError):
        policy.should_retrain(pd.Timestamp("2024-01-02T00:00:00Z"), history)


def test_decision_timestamps_must_not_move_backwards(empty_history):
    policy = NoRetrainingPolicy()
    policy.should_retrain(pd.Timestamp("2024-01-03T00:00:00Z"), empty_history)
    with pytest.raises(ValueError):
        policy.should_retrain(pd.Timestamp("2024-01-02T00:00:00Z"), empty_history)


def test_forecast_history_is_not_mutated():
    policy = NoRetrainingPolicy()
    history = make_history(["2024-01-01T00:00:00Z"])
    original = history.copy(deep=True)
    policy.should_retrain(pd.Timestamp("2024-01-02T00:00:00Z"), history)
    pd.testing.assert_frame_equal(history, original)


def test_subclasses_must_declare_a_canonical_strategy_identifier():
    with pytest.raises(ValueError):

        class UnknownStrategyPolicy(RetrainingPolicy):
            strategy = "weekly_ish"

            def _decide(
                self, decision_timestamp: pd.Timestamp, forecast_history: pd.DataFrame
            ) -> bool:
                return False


def test_decide_must_return_a_bool(empty_history):
    class BadPolicy(RetrainingPolicy):
        strategy = "fixed_schedule"

        def _decide(
            self, decision_timestamp: pd.Timestamp, forecast_history: pd.DataFrame
        ) -> int:
            return 1

    with pytest.raises(ValueError):
        BadPolicy().should_retrain(pd.Timestamp("2024-01-02T00:00:00Z"), empty_history)


def test_interface_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        RetrainingPolicy()


def test_fixed_schedule_defaults_to_weekly_decisions(empty_history):
    policy = FixedSchedulePolicy()
    issuances = pd.date_range("2024-01-01", periods=22, freq="24h", tz="UTC")
    decisions = [
        policy.should_retrain(issuance, empty_history) for issuance in issuances
    ]

    triggered_days = [index for index, decision in enumerate(decisions) if decision]
    assert triggered_days == [7, 14, 21]
    assert policy.strategy == "fixed_schedule"


@pytest.mark.parametrize("interval_days", [1, 3, 14])
def test_fixed_schedule_custom_interval_boundaries(empty_history, interval_days):
    policy = FixedSchedulePolicy(interval_days=interval_days)
    start = pd.Timestamp("2024-01-01T06:00:00Z")
    due = start + pd.Timedelta(days=interval_days)

    assert policy.should_retrain(start, empty_history) is False
    assert policy.should_retrain(due - pd.Timedelta(seconds=1), empty_history) is False
    assert policy.should_retrain(due, empty_history) is True
    assert policy.should_retrain(due, empty_history) is False
    assert policy.should_retrain(due + pd.Timedelta(days=interval_days), empty_history)


def test_fixed_schedule_anchors_next_interval_to_actual_decision(empty_history):
    policy = FixedSchedulePolicy()
    start = pd.Timestamp("2024-01-01T00:00:00Z")

    assert policy.should_retrain(start, empty_history) is False
    assert policy.should_retrain(start + pd.Timedelta(days=10), empty_history) is True
    assert policy.should_retrain(start + pd.Timedelta(days=14), empty_history) is False
    assert policy.should_retrain(start + pd.Timedelta(days=17), empty_history) is True


def test_fixed_schedule_uses_elapsed_utc_days_across_dst(empty_history):
    policy = FixedSchedulePolicy()
    start = pd.Timestamp("2024-03-25T00:00:00", tz="Europe/Berlin")
    local_week = pd.Timestamp("2024-04-01T00:00:00", tz="Europe/Berlin")

    assert policy.should_retrain(start, empty_history) is False
    assert policy.should_retrain(local_week, empty_history) is False
    due = local_week + pd.Timedelta(hours=1)
    assert policy.should_retrain(due, empty_history) is True


@pytest.mark.parametrize("interval_days", [0, -1, True, False, 1.5, "7", None])
def test_fixed_schedule_rejects_invalid_intervals(interval_days):
    with pytest.raises(ValueError, match="interval_days.*positive integer"):
        FixedSchedulePolicy(interval_days=interval_days)


def test_fixed_schedule_loads_interval_from_experiment_config(empty_history):
    config = load_config("configs/experiment.yaml")
    original_interval = config["retraining"]["fixed_schedule_interval_days"]
    assert original_interval == 7
    config["retraining"]["fixed_schedule_interval_days"] = 2
    policy = FixedSchedulePolicy.from_config(config)
    start = pd.Timestamp("2024-01-01T00:00:00Z")

    assert policy.should_retrain(start, empty_history) is False
    assert policy.should_retrain(start + pd.Timedelta(days=2), empty_history) is True


def test_fixed_schedule_requires_interval_in_config():
    with pytest.raises(ValueError, match="fixed_schedule_interval_days"):
        FixedSchedulePolicy.from_config({"retraining": {}})


def training_window_at(issuance: pd.Timestamp) -> TimeWindow:
    """Provide an explicit half-open training window with held-out validation."""
    return TimeWindow(
        start=issuance - pd.Timedelta(days=4),
        end=issuance - pd.Timedelta(days=1),
    )


def test_fixed_schedule_hook_passes_training_window_to_event_logger(empty_history):
    policy = FixedSchedulePolicy(interval_days=2)
    events = []
    hook = policy.as_policy_hook(
        training_window_provider=training_window_at,
        event_logger=events.append,
    )
    start = pd.Timestamp("2024-01-01T01:00:00+01:00")
    due = start + pd.Timedelta(days=2)

    assert hook(start, empty_history) is False
    assert events == []
    assert hook(due, empty_history) is True
    assert events == [
        {
            "timestamp": "2024-01-03T00:00:00+00:00",
            "strategy": "fixed_schedule",
            "trigger_reason": "fixed_schedule_interval_elapsed",
            "interval_days": 2,
            "training_window": {
                "start": "2023-12-30T00:00:00+00:00",
                "end": "2024-01-02T00:00:00+00:00",
            },
        }
    ]
    assert hook(due, empty_history) is False
    assert len(events) == 1


def test_fixed_schedule_hook_without_logger_preserves_bool_contract(empty_history):
    hook = FixedSchedulePolicy(interval_days=1).as_policy_hook()
    assert hook(pd.Timestamp("2024-01-01T00:00:00Z"), empty_history) is False
    assert hook(pd.Timestamp("2024-01-02T00:00:00Z"), empty_history) is True


@pytest.mark.parametrize(
    "options",
    [
        {"training_window_provider": training_window_at},
        {"event_logger": [].append},
        {"training_window_provider": 42, "event_logger": [].append},
        {"training_window_provider": training_window_at, "event_logger": 42},
    ],
)
def test_fixed_schedule_hook_requires_both_callable_logging_inputs(options):
    with pytest.raises(ValueError, match="training_window_provider.*event_logger"):
        FixedSchedulePolicy().as_policy_hook(**options)


def test_fixed_schedule_hook_rejects_future_training_window_without_advancing(
    empty_history,
):
    policy = FixedSchedulePolicy(interval_days=1)
    events = []
    invalid = True

    def provide_window(issuance):
        if invalid:
            return TimeWindow(issuance, issuance + pd.Timedelta(days=1))
        return training_window_at(issuance)

    hook = policy.as_policy_hook(
        training_window_provider=provide_window,
        event_logger=events.append,
    )
    start = pd.Timestamp("2024-01-01T00:00:00Z")

    with pytest.raises(ValueError, match="training_window.*decision_timestamp"):
        hook(start + pd.Timedelta(days=1), empty_history)
    assert events == []
    invalid = False
    assert hook(start, empty_history) is False
    assert hook(start + pd.Timedelta(days=1), empty_history) is True


def test_fixed_schedule_hook_requires_typed_training_window(empty_history):
    hook = FixedSchedulePolicy().as_policy_hook(
        training_window_provider=lambda issuance: {"start": issuance, "end": issuance},
        event_logger=[].append,
    )
    with pytest.raises(ValueError, match="TimeWindow"):
        hook(pd.Timestamp("2024-01-01T00:00:00Z"), empty_history)


@pytest.mark.parametrize("fault", ["future_history", "missing_column"])
def test_fixed_schedule_invalid_history_does_not_consume_trigger(empty_history, fault):
    policy = FixedSchedulePolicy(interval_days=1)
    start = pd.Timestamp("2024-01-01T00:00:00Z")
    due = start + pd.Timedelta(days=1)
    policy.should_retrain(start, empty_history)
    invalid_history = make_history(["2024-01-03T00:00:00Z"])
    if fault == "missing_column":
        invalid_history = invalid_history.drop(columns=["squared_error"])

    with pytest.raises(ValueError):
        policy.should_retrain(due, invalid_history)
    assert policy.should_retrain(due, empty_history) is True


def test_fixed_schedule_does_not_mutate_history_when_triggering():
    policy = FixedSchedulePolicy(interval_days=1)
    policy.should_retrain(pd.Timestamp("2024-01-01T00:00:00Z"), make_history([]))
    history = make_history(["2024-01-01T12:00:00Z"], strategy="fixed_schedule")
    original = history.copy(deep=True)

    assert policy.should_retrain(pd.Timestamp("2024-01-02T00:00:00Z"), history) is True
    pd.testing.assert_frame_equal(history, original)


@pytest.mark.parametrize(
    ("threshold", "expected"), [(2.0, False), (1.0, False), (0.5, True)]
)
def test_performance_triggered_threshold_boundaries(threshold, expected):
    policy = PerformanceTriggeredPolicy(threshold=threshold, min_periods=1)
    history = make_history(
        ["2024-01-01T12:00:00Z"], strategy="performance_triggered"
    )
    original = history.copy(deep=True)

    assert policy.strategy == "performance_triggered"
    assert (
        policy.should_retrain(pd.Timestamp("2024-01-02T00:00:00Z"), history)
        is expected
    )
    pd.testing.assert_frame_equal(history, original)


def test_performance_triggered_insufficient_history_does_not_trigger(empty_history):
    policy = PerformanceTriggeredPolicy(threshold=0.5)
    decision = pd.Timestamp("2024-01-02T00:00:00Z")
    assert policy.should_retrain(decision, empty_history) is False
    history = make_history(
        ["2024-01-01T12:00:00Z"], strategy="performance_triggered"
    )
    assert policy.should_retrain(decision, history) is False


def test_performance_triggered_ignores_psi(empty_history):
    policy = PerformanceTriggeredPolicy(threshold=2.0, min_periods=1)
    history = make_history(
        ["2024-01-01T12:00:00Z"], strategy="performance_triggered"
    )
    history["psi"] = 1000.0
    assert policy.should_retrain(pd.Timestamp("2024-01-02T00:00:00Z"), history) is False


def test_performance_triggered_loads_threshold_and_window_from_config():
    config = load_config("configs/experiment.yaml")
    config["retraining"]["rolling_rmse_threshold"] = 0.5
    config["retraining"]["rolling_rmse_window_days"] = 1
    policy = PerformanceTriggeredPolicy.from_config(config, min_periods=1)
    history = make_history(
        ["2024-01-01T12:00:00Z"], strategy="performance_triggered"
    )
    assert policy.as_policy_hook()(pd.Timestamp("2024-01-02T00:00:00Z"), history)


@pytest.mark.parametrize(
    "threshold", [-1, float("nan"), float("inf"), -float("inf"), True, "1", None]
)
def test_performance_triggered_rejects_invalid_thresholds(threshold):
    with pytest.raises(ValueError, match="threshold.*finite non-negative"):
        PerformanceTriggeredPolicy(threshold=threshold)


@pytest.mark.parametrize("value", [0, -1, True, 1.5, "7"])
@pytest.mark.parametrize("setting", ["window_days", "min_periods"])
def test_performance_triggered_rejects_invalid_monitor_settings(setting, value):
    with pytest.raises(ValueError, match=f"{setting}.*positive integer"):
        PerformanceTriggeredPolicy(threshold=1.0, **{setting: value})


@pytest.mark.parametrize(
    "config",
    [
        {},
        {"retraining": None},
        {"retraining": {}},
        {"retraining": {"rolling_rmse_threshold": 1.0}},
    ],
)
def test_performance_triggered_requires_monitor_config(config):
    with pytest.raises(ValueError, match="retraining.rolling_rmse_"):
        PerformanceTriggeredPolicy.from_config(config)


def test_performance_triggered_zero_threshold_uses_observed_errors_only():
    policy = PerformanceTriggeredPolicy(threshold=0.0, min_periods=1)
    decision = pd.Timestamp("2024-01-02T00:00:00Z")
    history = make_history(
        ["2024-01-01T12:00:00Z"], strategy="performance_triggered"
    )
    history["error"] = float("nan")
    assert policy.should_retrain(decision, history) is False
    history["error"] = 0.0
    assert policy.should_retrain(decision, history) is False
    history["error"] = 1.0
    assert policy.should_retrain(decision, history) is True


@pytest.mark.parametrize("column", ["timestamp", "forecast_timestamp"])
def test_performance_triggered_rejects_future_history(column):
    policy = PerformanceTriggeredPolicy(threshold=0.5, min_periods=1)
    history = make_history(
        ["2024-01-01T12:00:00Z"], strategy="performance_triggered"
    )
    history[column] = pd.Timestamp("2024-01-03T00:00:00Z")
    with pytest.raises(ValueError, match="must not follow decision_timestamp"):
        policy.should_retrain(pd.Timestamp("2024-01-02T00:00:00Z"), history)


def test_performance_triggered_window_and_default_readiness():
    decision = pd.Timestamp("2024-01-02T00:00:00Z")
    times = pd.date_range(end=decision, periods=25, freq="h")
    history = make_history(
        [timestamp.isoformat() for timestamp in times],
        strategy="performance_triggered",
    )
    policy = PerformanceTriggeredPolicy(threshold=0.5, window_days=1)
    assert policy.should_retrain(decision, history.iloc[:-1]) is False
    assert policy.should_retrain(decision, history) is True
    assert policy.rolling_rmse == 1.0
    assert policy.should_retrain(decision + pd.Timedelta(days=1), history) is False
    assert pd.isna(policy.rolling_rmse)


def test_performance_triggered_rejects_backwards_decisions(empty_history):
    policy = PerformanceTriggeredPolicy(threshold=1.0)
    assert (
        policy.should_retrain(pd.Timestamp("2024-01-02T00:00:00Z"), empty_history)
        is False
    )
    with pytest.raises(ValueError, match="must not move backwards"):
        policy.should_retrain(pd.Timestamp("2024-01-01T00:00:00Z"), empty_history)
