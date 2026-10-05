"""Retraining decisions driven only by observed rolling RMSE degradation."""

from collections.abc import Callable, Mapping
from math import isfinite
from numbers import Real
from typing import Any

import pandas as pd

from energy_trading_pipeline.backtesting.splitter import TimeWindow
from energy_trading_pipeline.monitoring.rolling_rmse import calculate_rolling_rmse
from energy_trading_pipeline.retraining.policies import RetrainingPolicy


class PerformanceTriggeredPolicy(RetrainingPolicy):
	"""Trigger strictly above the threshold, never during metric warm-up.

	Use a fresh instance for each independent run. History must contain only
	observed errors for this strategy. Decisions request a refit; they neither
	train a model nor reset the rolling error history.
	"""

	strategy = "performance_triggered"

	def __init__(
		self,
		threshold: float,
		*,
		window_days: int = 7,
		min_periods: int | None = None,
	) -> None:
		super().__init__()
		if (
			not isinstance(threshold, Real)
			or isinstance(threshold, bool)
			or not isfinite(threshold)
			or threshold < 0
		):
			raise ValueError("threshold must be a finite non-negative number")
		if (
			not isinstance(window_days, int)
			or isinstance(window_days, bool)
			or window_days <= 0
		):
			raise ValueError("window_days must be a positive integer")
		if min_periods is not None and (
			not isinstance(min_periods, int)
			or isinstance(min_periods, bool)
			or min_periods <= 0
		):
			raise ValueError("min_periods must be a positive integer")
		self.threshold = float(threshold)
		self.window_days = window_days
		self.min_periods = min_periods
		self.rolling_rmse = float("nan")

	@classmethod
	def from_config(
		cls, config: Mapping[str, Any], *, min_periods: int | None = None
	) -> "PerformanceTriggeredPolicy":
		"""Read the threshold and monitoring window from experiment config."""
		retraining = config.get("retraining")
		for key in ("rolling_rmse_threshold", "rolling_rmse_window_days"):
			if not isinstance(retraining, Mapping) or key not in retraining:
				raise ValueError(f"retraining.{key} is required")
		return cls(
			threshold=retraining["rolling_rmse_threshold"],
			window_days=retraining["rolling_rmse_window_days"],
			min_periods=min_periods,
		)

	def as_policy_hook(
		self,
		*,
		training_window_provider: Callable[[pd.Timestamp], TimeWindow] | None = None,
		model_version_provider: Callable[[pd.Timestamp], str] | None = None,
		event_logger: Callable[[dict[str, Any]], None] | None = None,
	) -> Callable[[pd.Timestamp, pd.DataFrame], bool]:
		"""Optionally hand off an auditable retraining request to the caller.

		Supply all three callbacks or none. The window and model-version label
		are explicit caller inputs, not inferred from forecast history. The label
		may identify the active or intended replacement model; only the caller
		can confirm a completed refit and its registered version. Callback errors
		propagate. Logging does not alter the bool decision contract.
		"""
		if (
			training_window_provider is None
			and model_version_provider is None
			and event_logger is None
		):
			return super().as_policy_hook()
		if (
			not callable(training_window_provider)
			or not callable(model_version_provider)
			or not callable(event_logger)
		):
			raise ValueError(
				"training_window_provider, model_version_provider, and event_logger "
				"must all be callable"
			)

		def hook(issuance: pd.Timestamp, history: pd.DataFrame) -> bool:
			timestamp = self._normalize_timestamp(issuance)
			window = training_window_provider(timestamp)
			if not isinstance(window, TimeWindow):
				raise ValueError("training_window_provider must return a TimeWindow")
			if window.end > timestamp:
				raise ValueError("training_window must not follow decision_timestamp")
			model_version = model_version_provider(timestamp)
			if not isinstance(model_version, str) or not model_version.strip():
				raise ValueError("model_version_provider must return a nonempty string")
			decision = self.should_retrain(timestamp, history)
			if decision:
				event_logger(
					{
						"timestamp": timestamp.isoformat(),
						"strategy": self.strategy,
						"trigger_reason": "rolling_rmse_exceeds_threshold",
						"threshold": self.threshold,
						"rolling_rmse": self.rolling_rmse,
						"training_window_start": window.start.isoformat(),
						"training_window_end": window.end.isoformat(),
						"model_version": model_version,
					}
				)
			return decision

		return hook

	def _decide(
		self, decision_timestamp: pd.Timestamp, forecast_history: pd.DataFrame
	) -> bool:
		"""Compare observed RMSE to the threshold without consulting PSI."""
		metric = calculate_rolling_rmse(
			forecast_history,
			decision_timestamp,
			window_days=self.window_days,
			min_periods=self.min_periods,
		)
		self.rolling_rmse = metric["rolling_rmse"]
		return self.rolling_rmse > self.threshold
