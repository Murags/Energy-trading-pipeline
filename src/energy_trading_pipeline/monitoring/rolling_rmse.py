"""Decision-time rolling RMSE over observed errors in an elapsed UTC window."""

from datetime import datetime

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_complex_dtype, is_numeric_dtype


def _utc_timestamps(values: pd.Series, column: str) -> pd.Series:
	"""Normalize aware timestamps without assuming a timezone for naive values."""
	parsed = []
	message = f"{column} must contain valid timezone-aware timestamps"
	for value in values:
		if not isinstance(value, (str, datetime, pd.Timestamp)):
			raise ValueError(message)
		try:
			timestamp = pd.Timestamp(value)
			if pd.isna(timestamp) or timestamp.tzinfo is None:
				raise ValueError(message)
			parsed.append(timestamp.tz_convert("UTC").as_unit("ns"))
		except (ValueError, TypeError, OverflowError) as exc:
			raise ValueError(message) from exc
	return pd.Series(parsed, index=values.index, dtype="datetime64[ns, UTC]")


def calculate_rolling_rmse(
	forecast_history: pd.DataFrame,
	decision_timestamp: pd.Timestamp,
	*,
	window_days: int = 7,
	min_periods: int | None = None,
) -> dict[str, float]:
	"""Return `rolling_rmse` using only errors observable at this decision.

	Require timezone-aware `timestamp` values and real numeric `error` values.
	Select the elapsed UTC interval (decision - window_days, decision]. When
	`forecast_timestamp` is present, issuance must also be at or before the
	decision. Callers must leave errors missing until actuals are available,
	as required by the canonical forecast log contract; timestamps alone cannot
	establish whether an actual was published late.

	Missing errors do not count toward `min_periods`, which defaults to
	window_days * 24 for hourly forecasts. Return NaN when fewer errors are
	available. A supplied strategy column must identify one strategy, and
	observed target timestamps must be unique: callers select the strategy
	and issuance rather than mixing comparisons or double-counting targets.
	Model-version changes do not reset history. Input is never mutated.
	"""
	if (
		not isinstance(window_days, int)
		or isinstance(window_days, bool)
		or window_days <= 0
	):
		raise ValueError("window_days must be a positive integer")
	if min_periods is None:
		min_periods = window_days * 24
	if (
		not isinstance(min_periods, int)
		or isinstance(min_periods, bool)
		or min_periods <= 0
	):
		raise ValueError("min_periods must be a positive integer")
	if (
		not isinstance(decision_timestamp, pd.Timestamp)
		or pd.isna(decision_timestamp)
		or decision_timestamp.tzinfo is None
	):
		raise ValueError("decision_timestamp must be a timezone-aware pandas timestamp")
	try:
		decision = decision_timestamp.tz_convert("UTC").as_unit("ns")
		window_start = decision - pd.Timedelta(days=window_days)
	except (ValueError, OverflowError) as exc:
		raise ValueError(
			"window_days and decision_timestamp exceed timestamp bounds"
		) from exc
	if not isinstance(forecast_history, pd.DataFrame):
		raise ValueError("forecast_history must be a pandas DataFrame")
	if not forecast_history.columns.is_unique:
		raise ValueError("forecast_history has duplicate column names")
	missing = sorted({"timestamp", "error"} - set(forecast_history.columns))
	if missing:
		raise ValueError(f"Missing required forecast history columns: {missing}")

	timestamps = _utc_timestamps(forecast_history["timestamp"], "timestamp")
	available = (timestamps > window_start) & (timestamps <= decision)
	if "forecast_timestamp" in forecast_history:
		issuance = _utc_timestamps(
			forecast_history["forecast_timestamp"], "forecast_timestamp"
		)
		available &= issuance <= decision
	history = forecast_history.loc[available].copy()
	history["timestamp"] = timestamps.loc[available]
	history = history.loc[history["error"].notna()].sort_values(
		"timestamp", kind="stable"
	)
	if "strategy" in history and history["strategy"].nunique(dropna=False) > 1:
		raise ValueError("forecast_history must contain a single strategy")
	if history["timestamp"].duplicated().any():
		raise ValueError("forecast_history contains duplicate target timestamps")
	errors = history["error"].infer_objects()
	message = "error must contain finite real numeric values"
	if not errors.empty and (
		not is_numeric_dtype(errors.dtype)
		or is_bool_dtype(errors.dtype)
		or is_complex_dtype(errors.dtype)
	):
		raise ValueError(message)
	errors = errors.astype("float64")
	if not np.isfinite(errors).all():
		raise ValueError(message)
	if len(errors) < min_periods:
		return {"rolling_rmse": float("nan")}

	scale = float(errors.abs().max())
	rolling_rmse = (
		scale * float(np.sqrt(((errors / scale) ** 2).mean())) if scale else 0.0
	)
	return {"rolling_rmse": rolling_rmse}
