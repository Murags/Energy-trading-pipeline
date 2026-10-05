"""Fixed-schedule decisions using elapsed UTC time and a configurable interval."""

from collections.abc import Callable, Mapping
from typing import Any

import pandas as pd

from energy_trading_pipeline.backtesting.splitter import TimeWindow
from energy_trading_pipeline.retraining.policies import RetrainingPolicy


class FixedSchedulePolicy(RetrainingPolicy):
	"""Retrain every configured number of days, with a weekly default.

	The first decision anchors the already-created model's schedule and returns
	False. A positive decision resets the interval to its issuance timestamp,
	avoiding repeated triggers at the same time or catch-up retraining bursts.
	Use a fresh policy instance for each independent backtest run.
	"""

	strategy = "fixed_schedule"

	def __init__(self, interval_days: int = 7) -> None:
		super().__init__()
		if (
			not isinstance(interval_days, int)
			or isinstance(interval_days, bool)
			or interval_days <= 0
		):
			raise ValueError("interval_days must be a positive integer")
		self._interval = pd.Timedelta(days=interval_days)
		self._schedule_timestamp: pd.Timestamp | None = None

	@classmethod
	def from_config(cls, config: Mapping[str, Any]) -> "FixedSchedulePolicy":
		"""Read the interval from the full experiment configuration."""
		retraining = config.get("retraining")
		if not isinstance(retraining, Mapping) or (
			"fixed_schedule_interval_days" not in retraining
		):
			raise ValueError("retraining.fixed_schedule_interval_days is required")
		return cls(interval_days=retraining["fixed_schedule_interval_days"])

	def as_policy_hook(
		self,
		*,
		training_window_provider: Callable[[pd.Timestamp], TimeWindow] | None = None,
		event_logger: Callable[[dict[str, Any]], None] | None = None,
	) -> Callable[[pd.Timestamp, pd.DataFrame], bool]:
		"""Adapt decisions with an optional explicit training-window logging handoff.

		Supply both callbacks or neither. The provider supplies the actual
		candidate training window, including any held-out validation gap; the
		policy never infers training bounds from forecast history. The logger
		receives a scheduled request, not confirmation of a successful refit.
		Callback failures propagate to the caller. Model versions, execution,
		and event persistence remain the caller's responsibility.
		"""
		if training_window_provider is None and event_logger is None:
			return super().as_policy_hook()
		if not callable(training_window_provider) or not callable(event_logger):
			raise ValueError(
				"training_window_provider and event_logger must both be callable"
			)

		def hook(issuance: pd.Timestamp, history: pd.DataFrame) -> bool:
			timestamp = self._normalize_timestamp(issuance)
			window = training_window_provider(timestamp)
			if not isinstance(window, TimeWindow):
				raise ValueError("training_window_provider must return a TimeWindow")
			if window.end > timestamp:
				raise ValueError("training_window must not follow decision_timestamp")
			decision = self.should_retrain(timestamp, history)
			if decision:
				event_logger(
					{
						"timestamp": timestamp.isoformat(),
						"strategy": self.strategy,
						"trigger_reason": "fixed_schedule_interval_elapsed",
						"interval_days": self._interval.days,
						"training_window": {
							"start": window.start.isoformat(),
							"end": window.end.isoformat(),
						},
					}
				)
			return decision

		return hook

	def _decide(
		self, decision_timestamp: pd.Timestamp, forecast_history: pd.DataFrame
	) -> bool:
		"""Trigger once when the configured interval has elapsed."""
		if self._schedule_timestamp is None:
			self._schedule_timestamp = decision_timestamp
			return False
		if decision_timestamp - self._schedule_timestamp < self._interval:
			return False
		self._schedule_timestamp = decision_timestamp
		return True
