"""Retraining policy contract and the static no-retraining strategy."""

import pandas as pd
import pytest

from energy_trading_pipeline.backtesting.forecast_log import build_forecast_log
from energy_trading_pipeline.retraining.no_retraining import NoRetrainingPolicy
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
