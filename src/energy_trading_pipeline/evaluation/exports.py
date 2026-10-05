"""Minimal dashboard Parquet exports from completed, explicitly supplied results."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_complex_dtype, is_numeric_dtype

from energy_trading_pipeline.backtesting.forecast_log import (
	STRATEGIES,
	build_forecast_log,
	read_forecast_log,
)
from energy_trading_pipeline.config.loader import load_yaml_file
from energy_trading_pipeline.evaluation.strategy_comparison import (
	STRATEGY_METRIC_COLUMNS,
)
from energy_trading_pipeline.retraining.events import build_retraining_events


FORECAST_EXPORT_COLUMNS = (
	"timestamp", "prediction", "actual", "strategy", "model_version", "rolling_rmse",
)
METRIC_EXPORT_COLUMNS = (
	"run_id", "evaluation_start", "evaluation_end", *STRATEGY_METRIC_COLUMNS,
)
EVENT_EXPORT_COLUMNS = (
	"timestamp", "strategy", "trigger_reason", "threshold", "rolling_rmse",
	"model_version",
)
MODEL_EXPORT_COLUMNS = ("model_version", "model_type")


def _select(data: pd.DataFrame, columns: tuple[str, ...]) -> pd.DataFrame:
	if not isinstance(data, pd.DataFrame) or not data.columns.is_unique:
		raise ValueError("Export inputs must be DataFrames with unique columns")
	missing = sorted(set(columns) - set(data.columns))
	if missing:
		raise ValueError(f"Missing required export columns: {missing}")
	return data.loc[:, list(columns)].copy().reset_index(drop=True)


def _timestamps(values: pd.Series, column: str) -> pd.Series:
	parsed = []
	message = f"{column} must contain valid timezone-aware timestamps"
	for value in values:
		try:
			timestamp = pd.Timestamp(value)
			if pd.isna(timestamp) or timestamp.tzinfo is None:
				raise ValueError(message)
			parsed.append(timestamp.tz_convert("UTC").as_unit("ns"))
		except (ValueError, TypeError, OverflowError) as exc:
			raise ValueError(message) from exc
	return pd.Series(parsed, index=values.index, dtype="datetime64[ns, UTC]")


def _nonnegative(values: pd.Series, column: str, *, missing: bool) -> pd.Series:
	message = f"{column} must contain finite nonnegative numbers"
	if values.empty or (missing and values.isna().all()):
		return pd.Series(np.nan, index=values.index, dtype="float64")
	if (
		not is_numeric_dtype(values.dtype)
		or is_bool_dtype(values.dtype)
		or is_complex_dtype(values.dtype)
	):
		raise ValueError(message)
	result = values.astype("float64")
	if (
		(not missing and result.isna().any())
		or not np.isfinite(result.dropna()).all()
		or result.lt(0).any()
	):
		raise ValueError(message)
	return result


def _metrics(data: pd.DataFrame) -> pd.DataFrame:
	result = _select(data, METRIC_EXPORT_COLUMNS)
	if not result["strategy"].isin(STRATEGIES).all():
		raise ValueError("Metrics must use canonical strategy identifiers")
	if result["strategy"].duplicated().any():
		raise ValueError("Metrics must have one row per strategy")
	if any(
		not isinstance(value, str) or not value.strip()
		for value in result["run_id"]
	) or result["run_id"].nunique() > 1:
		raise ValueError("Metrics must belong to one nonempty run_id")
	for column in ("evaluation_start", "evaluation_end"):
		result[column] = _timestamps(result[column], column)
		if result[column].nunique() > 1:
			raise ValueError("Metrics must share one evaluation window")
	if result["evaluation_start"].ge(result["evaluation_end"]).any():
		raise ValueError("evaluation_start must precede evaluation_end")
	for column in STRATEGY_METRIC_COLUMNS[1:]:
		result[column] = _nonnegative(
			result[column], column, missing=column in {"rmse", "mae"}
		)
	if (
		result["retraining_count"].mod(1).ne(0).any()
		or result["retraining_count"].ge(2**63).any()
	):
		raise ValueError("retraining_count must contain integer counts")
	result["retraining_count"] = result["retraining_count"].astype("int64")
	return result.astype({"run_id": "string", "strategy": "string"}).sort_values(
		"strategy"
	).reset_index(drop=True)


def _models(index: Mapping[str, Any], versions: set[str]) -> pd.DataFrame:
	if not isinstance(index, Mapping) or not isinstance(index.get("models"), Mapping):
		raise ValueError("Model index must contain a models mapping")
	rows = []
	for version in sorted(versions):
		metadata = index["models"].get(version)
		if not isinstance(metadata, Mapping) or any(
			column not in metadata for column in MODEL_EXPORT_COLUMNS
		):
			raise ValueError(f"Missing model metadata for version: {version}")
		if metadata["model_version"] != version or metadata["model_type"] != "xgboost":
			raise ValueError(f"Invalid model metadata for version: {version}")
		rows.append({column: metadata[column] for column in MODEL_EXPORT_COLUMNS})
	result = pd.DataFrame(rows, columns=list(MODEL_EXPORT_COLUMNS))
	return result.astype({"model_version": "string", "model_type": "string"})


def write_dashboard_exports(
	forecasts: pd.DataFrame,
	metrics: pd.DataFrame,
	retraining_events: pd.DataFrame,
	model_index: Mapping[str, Any],
	*,
	exports_dir: Path,
	monitoring: pd.DataFrame | None = None,
) -> dict[str, Path]:
	"""Write four minimal Parquet files under the configured dashboard directory.

	Supply canonical forecasts/events, one saved Story 8.2 comparison table, and
	the YAML registry's models mapping. Export only the table's half-open UTC
	evaluation window and referenced registry versions. Stored metrics are not
	recalculated. Optional monitoring must use timestamp/strategy keys present
	in the selected forecasts; these timestamps remain the stored decision times,
	not recomputed target-time errors. Unavailable rolling RMSE stays NaN.

	Validate all inputs before creating output files. Inputs are not mutated.
	Repeated calls replace the current dashboard snapshot, not source artifacts.
	No training, backtesting, model loading, or dashboard code is invoked.
	"""
	forecast_data = build_forecast_log(forecasts)
	event_data = build_retraining_events(retraining_events)
	metric_data = _metrics(metrics)
	if not metric_data.empty:
		run_id = metric_data["run_id"].iloc[0]
		for source in (forecasts, retraining_events, monitoring):
			if source is not None and "run_id" in source:
				if not source["run_id"].eq(run_id).all():
					raise ValueError("Export inputs must belong to the same run_id")
		start = metric_data["evaluation_start"].iloc[0]
		end = metric_data["evaluation_end"].iloc[0]
		forecast_data = forecast_data.loc[
			forecast_data["timestamp"].ge(start) & forecast_data["timestamp"].lt(end)
		].reset_index(drop=True)
		event_data = event_data.loc[
			event_data["timestamp"].ge(start) & event_data["timestamp"].lt(end)
		].reset_index(drop=True)
	if set(forecast_data["strategy"]) != set(metric_data["strategy"]):
		raise ValueError("Forecasts and metrics must contain the same strategies")
	if not event_data["strategy"].isin(metric_data["strategy"]).all():
		raise ValueError("Retraining event strategy has no saved metrics")
	if forecast_data.duplicated(["strategy", "timestamp"]).any():
		raise ValueError("Duplicate forecast timestamps per strategy")
	if event_data.duplicated(["strategy", "timestamp"]).any():
		raise ValueError("Duplicate retraining timestamps per strategy")
	histories = [
		history.reset_index(drop=True)
		for _, history in forecast_data.groupby("strategy", sort=True)
	]
	for history in histories[1:]:
		if not history[["timestamp", "actual"]].equals(
			histories[0][["timestamp", "actual"]]
		):
			raise ValueError("Strategies must share evaluation timestamps and actuals")
	forecast_data = _select(forecast_data, FORECAST_EXPORT_COLUMNS[:-1])
	if monitoring is None:
		forecast_data["rolling_rmse"] = np.nan
	else:
		rolling = _select(monitoring, ("timestamp", "strategy", "rolling_rmse"))
		rolling["timestamp"] = _timestamps(rolling["timestamp"], "timestamp")
		rolling["rolling_rmse"] = _nonnegative(
			rolling["rolling_rmse"], "rolling_rmse", missing=True
		)
		keys = ["timestamp", "strategy"]
		if rolling.duplicated(keys).any():
			raise ValueError("Duplicate monitoring timestamps per strategy")
		known = pd.MultiIndex.from_frame(forecast_data[keys])
		if not pd.MultiIndex.from_frame(rolling[keys]).isin(known).all():
			raise ValueError("Monitoring keys must match selected forecast timestamps")
		forecast_data = forecast_data.merge(rolling, on=keys, how="left", sort=False)
	forecast_data = forecast_data.astype(
		{"strategy": "string", "model_version": "string"}
	)
	versions = set(forecast_data["model_version"]) | set(event_data["model_version"])
	frames = {
		"forecasts": forecast_data,
		"metrics": metric_data,
		"retraining_events": _select(event_data, EVENT_EXPORT_COLUMNS),
		"model_versions": _models(model_index, versions),
	}
	paths = {
		name: Path(exports_dir) / f"{name}.parquet" for name in frames
	}
	Path(exports_dir).mkdir(parents=True, exist_ok=True)
	for name, frame in frames.items():
		frame.to_parquet(paths[name], index=False)
	return paths


def export_dashboard_artifacts(
	*,
	forecasts_path: Path,
	metrics_path: Path,
	retraining_events_path: Path,
	exports_dir: Path,
	model_index_path: Path | None = None,
	run_metadata_paths: list[Path] | None = None,
	monitoring_path: Path | None = None,
) -> dict[str, Path]:
	"""Read saved Parquet/YAML inputs and export without running pipeline stages.

	Supply either the training registry index or backtest run metadata files for
	all referenced models. Backtest metadata supplies model version/type through
	its recorded model_version and config.model.type; model files are never read.
	All paths are explicit; the output is one replaceable dashboard snapshot.
	"""
	if bool(model_index_path) == bool(run_metadata_paths):
		raise ValueError("Supply either a model index or saved run metadata files")
	table_paths = [forecasts_path, metrics_path, retraining_events_path]
	if monitoring_path is not None:
		table_paths.append(monitoring_path)
	if any(Path(path).suffix.lower() != ".parquet" for path in table_paths):
		raise ValueError("Dashboard input tables must use .parquet")
	source_paths = [*table_paths, *(run_metadata_paths or [])]
	if model_index_path is not None:
		source_paths.append(model_index_path)
	outputs = {
		(Path(exports_dir) / f"{name}.parquet").resolve()
		for name in ("forecasts", "metrics", "retraining_events", "model_versions")
	}
	if any(Path(path).resolve() in outputs for path in source_paths):
		raise ValueError("Dashboard exports must not overwrite source artifacts")
	if model_index_path is not None:
		model_index = load_yaml_file(model_index_path)
	else:
		models = {}
		for path in run_metadata_paths or []:
			metadata = load_yaml_file(path)
			try:
				version = metadata["model_version"]
				model_type = metadata["config"]["model"]["type"]
			except (KeyError, TypeError) as exc:
				raise ValueError(
					f"Missing model version/type in run metadata: {path}"
				) from exc
			if not isinstance(version, str) or not version.strip():
				raise ValueError(f"Invalid model_version in run metadata: {path}")
			models[version] = {"model_version": version, "model_type": model_type}
		model_index = {"models": models}
	return write_dashboard_exports(
		read_forecast_log(forecasts_path),
		pd.read_parquet(metrics_path),
		pd.read_parquet(retraining_events_path),
		model_index,
		exports_dir=exports_dir,
		monitoring=(
			pd.read_parquet(monitoring_path) if monitoring_path is not None else None
		),
	)
