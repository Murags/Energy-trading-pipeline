"""Common retraining policy contract shared by every strategy.

A policy answers one question at a time: given an issuance timestamp and the
forecast history already observable at that moment, should the model be
retrained before issuing the next block? The backtest runner owns execution and
model lifecycle, so policies stay side-effect free and interchangeable.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from typing import Any

import pandas as pd

from energy_trading_pipeline.backtesting.forecast_log import (
    FORECAST_LOG_COLUMNS,
    STRATEGIES,
)


class RetrainingPolicy(ABC):
    """Base contract returning retrain/no-retrain decisions in chronological order.

    Subclasses declare a canonical ``strategy`` identifier and implement
    ``_decide``. The base class validates the decision timestamp and forecast
    history, so strategy code never has to re-check leakage preconditions.
    """

    strategy: str

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if getattr(cls, "strategy", None) not in STRATEGIES:
            raise ValueError(f"strategy must be one of {sorted(STRATEGIES)}")

    def __init__(self) -> None:
        self._last_decision_timestamp: pd.Timestamp | None = None

    def should_retrain(
        self, decision_timestamp: pd.Timestamp, forecast_history: pd.DataFrame
    ) -> bool:
        """Decide whether to retrain at `decision_timestamp`.

        Args:
            decision_timestamp: Timezone-aware issuance time, normalized to UTC.
                Decisions must be requested in non-decreasing chronological order.
            forecast_history: Canonical forecast log already restricted by the
                caller to records observable at the decision time. Not mutated.

        Returns:
            True when the strategy requires retraining before the next forecast
            block, otherwise False.
        """
        issuance = self._normalize_timestamp(decision_timestamp)
        history = self._validate_history(forecast_history, issuance)
        decision = self._decide(issuance, history)
        if not isinstance(decision, bool):
            raise ValueError(
                f"{type(self).__name__}._decide must return a bool decision"
            )
        self._last_decision_timestamp = issuance
        return decision

    def as_policy_hook(self) -> Callable[[pd.Timestamp, pd.DataFrame], bool]:
        """Return a callable matching the backtest runner's policy hook signature."""
        return self.should_retrain

    def state(self) -> dict[str, Any]:
        """Serialize decision state so a later process resumes the same schedule.

        A daily job runs as a fresh process, so the decision sequence must carry
        across runs explicitly rather than living only in memory. Timestamps are
        ISO-8601 UTC strings; ``None`` means no decision has been made yet.
        """
        last = self._last_decision_timestamp
        return {
            "strategy": self.strategy,
            "last_decision_timestamp": None if last is None else last.isoformat(),
        }

    def restore(self, state: Mapping[str, Any]) -> None:
        """Resume from state produced by ``state()`` for this same strategy."""
        if not isinstance(state, Mapping):
            raise ValueError("Policy state must be a mapping")
        recorded = state.get("strategy")
        if recorded != self.strategy:
            raise ValueError(
                f"Policy state is for {recorded!r}, not {self.strategy!r}"
            )
        self._last_decision_timestamp = self._restore_timestamp(
            state.get("last_decision_timestamp"), "last_decision_timestamp"
        )

    @staticmethod
    def _restore_timestamp(value: Any, name: str) -> pd.Timestamp | None:
        """Parse an optional aware timestamp from serialized policy state."""
        if value is None:
            return None
        try:
            timestamp = pd.Timestamp(value)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"{name} must be a valid timestamp") from exc
        if pd.isna(timestamp) or timestamp.tzinfo is None:
            raise ValueError(f"{name} must be timezone-aware")
        return timestamp.tz_convert("UTC").as_unit("ns")

    @abstractmethod
    def _decide(
        self, decision_timestamp: pd.Timestamp, forecast_history: pd.DataFrame
    ) -> bool:
        """Return the strategy-specific decision for already validated inputs."""

    def _normalize_timestamp(self, value: pd.Timestamp) -> pd.Timestamp:
        """Require an aware pandas timestamp rather than assuming a timezone."""
        if (
            not isinstance(value, pd.Timestamp)
            or pd.isna(value)
            or value.tzinfo is None
        ):
            raise ValueError(
                "decision_timestamp must be a timezone-aware pandas timestamp"
            )
        issuance = value.tz_convert("UTC").as_unit("ns")
        last = self._last_decision_timestamp
        if last is not None and issuance < last:
            raise ValueError("decision_timestamp must not move backwards in time")
        return issuance

    def _validate_history(
        self, forecast_history: pd.DataFrame, decision_timestamp: pd.Timestamp
    ) -> pd.DataFrame:
        """Reject malformed or future-looking history before any decision logic."""
        if not isinstance(forecast_history, pd.DataFrame):
            raise ValueError("forecast_history must be a pandas DataFrame")
        if not forecast_history.columns.is_unique:
            raise ValueError("forecast_history has duplicate column names")
        missing = sorted(set(FORECAST_LOG_COLUMNS) - set(forecast_history.columns))
        if missing:
            raise ValueError(f"Missing required forecast log columns: {missing}")
        history = forecast_history.loc[:, list(FORECAST_LOG_COLUMNS)].copy(deep=True)
        for column in ("timestamp", "forecast_timestamp"):
            try:
                values = pd.to_datetime(history[column], utc=True)
            except (ValueError, TypeError) as exc:
                raise ValueError(
                    f"forecast_history {column} must contain valid timestamps"
                ) from exc
            if (values > decision_timestamp).any():
                raise ValueError(
                    f"forecast_history {column} must not follow decision_timestamp"
                )
            history[column] = values
        return history
