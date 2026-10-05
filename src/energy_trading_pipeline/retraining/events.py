"""Validated retraining event records and local Parquet persistence."""

from datetime import datetime
from math import isfinite
from numbers import Real
from pathlib import Path

import pandas as pd

from energy_trading_pipeline.backtesting.forecast_log import STRATEGIES


RETRAINING_EVENT_COLUMNS = (
	"timestamp",
	"strategy",
	"trigger_reason",
	"threshold",
	"rolling_rmse",
	"training_window_start",
	"training_window_end",
	"model_version",
)


def _utc_timestamps(values: pd.Series, column: str) -> pd.Series:
	"""Require aware timestamps and normalize them to UTC nanoseconds."""
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


def build_retraining_events(df: pd.DataFrame) -> pd.DataFrame:
	"""Validate and sort event records without mutating the input.

	Training windows are half-open and must end at or before the event time.
	Performance triggers require finite RMSE strictly above a finite threshold.
	Scheduled events may leave these inapplicable values missing. Model versions
	are explicit caller-supplied labels; this builder does not infer or register
	models. A policy request is not proof that retraining succeeded.
	"""
	if not isinstance(df, pd.DataFrame):
		raise ValueError("retraining events must be a pandas DataFrame")
	if not df.columns.is_unique:
		raise ValueError("Duplicate retraining event column names are not supported")
	missing = sorted(set(RETRAINING_EVENT_COLUMNS) - set(df.columns))
	if missing:
		raise ValueError(f"Missing required retraining event columns: {missing}")
	result = df.loc[:, list(RETRAINING_EVENT_COLUMNS)].copy().reset_index(drop=True)
	for column in ("timestamp", "training_window_start", "training_window_end"):
		result[column] = _utc_timestamps(result[column], column)
	if (result["training_window_start"] >= result["training_window_end"]).any():
		raise ValueError("training_window_start must precede training_window_end")
	if (result["training_window_end"] > result["timestamp"]).any():
		raise ValueError("training_window_end must not follow event timestamp")
	for column in ("strategy", "trigger_reason", "model_version"):
		if any(
			not isinstance(value, str) or not value.strip() for value in result[column]
		):
			raise ValueError(f"{column} must contain nonempty strings")
		result[column] = result[column].astype("string")
	if not result["strategy"].isin(STRATEGIES).all():
		raise ValueError(f"strategy must be one of {sorted(STRATEGIES)}")
	performance = result["strategy"] == "performance_triggered"
	for column in ("threshold", "rolling_rmse"):
		values = result[column]
		if values.loc[performance].isna().any() or any(
			not isinstance(value, Real)
			or isinstance(value, bool)
			or not isfinite(value)
			or value < 0
			for value in values.dropna()
		):
			raise ValueError(f"{column} must contain finite non-negative numbers")
		result[column] = pd.Series(
			[float("nan") if pd.isna(value) else float(value) for value in values],
			index=result.index,
			dtype="float64",
		)
	if (
		result.loc[performance, "rolling_rmse"]
		<= result.loc[performance, "threshold"]
	).any():
		raise ValueError("performance_triggered rolling_rmse must exceed threshold")
	return result.sort_values("timestamp", kind="stable").reset_index(drop=True)


def write_retraining_events(df: pd.DataFrame, output_path: Path) -> Path:
	"""Write a validated complete event log, replacing an existing artifact.

	Supply the configured run path, normally
	``logs/runs/run_YYYYMMDD_HHMMSS/retraining_events.parquet``. Parent directories
	are created only after validation. Accumulate events explicitly before writing;
	this function does not append or maintain hidden run state.
	"""
	output_path = Path(output_path)
	if output_path.suffix.lower() != ".parquet":
		raise ValueError("Unsupported retraining event format; use .parquet")
	result = build_retraining_events(df)
	output_path.parent.mkdir(parents=True, exist_ok=True)
	result.to_parquet(output_path, index=False)
	return output_path
