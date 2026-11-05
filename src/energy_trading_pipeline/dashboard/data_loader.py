"""Read-only loading of the four Story 8.4 dashboard Parquet exports."""

from math import isfinite
from pathlib import Path
from typing import Any

import pandas as pd
from pyarrow import ArrowException

from energy_trading_pipeline.forecasting.store import (
	ArtifactStore,
	build_store,
	strategy_keys,
)


_EXPORT_COLUMNS = {
	"forecasts": (
		"timestamp", "prediction", "actual", "strategy", "model_version",
		"rolling_rmse",
	),
	"metrics": (
		"run_id", "evaluation_start", "evaluation_end", "strategy", "rmse",
		"mae", "retraining_count", "retraining_frequency",
	),
	"retraining_events": (
		"timestamp", "strategy", "trigger_reason", "threshold", "rolling_rmse",
		"model_version",
	),
	"model_versions": ("model_version", "model_type"),
}
_TIMESTAMP_COLUMNS = {
	"forecasts": ("timestamp",),
	"metrics": ("evaluation_start", "evaluation_end"),
	"retraining_events": ("timestamp",),
	"model_versions": (),
}

LIVE_STRATEGIES = (
	"no_retraining",
	"fixed_schedule",
	"performance_triggered",
)
_LIVE_FORECAST_COLUMNS = (
	"timestamp",
	"forecast_timestamp",
	"delivery_date",
	"prediction",
	"actual",
	"strategy",
	"model_version",
)
_LIVE_EVENT_COLUMNS = (
	"timestamp",
	"strategy",
	"trigger_reason",
	"threshold",
	"rolling_rmse",
	"training_window_start",
	"training_window_end",
	"model_version",
)
_LIVE_STATE_COLUMNS = (
	"strategy",
	"model_version",
	"last_issuance",
	"last_delivery_date",
	"retraining_count",
	"updated_at",
)


class DashboardArtifactError(ValueError):
	"""An exported artifact is missing, unreadable, or unsuitable for display."""


def _normalize_export(
	data: pd.DataFrame, name: str, source: str | Path
) -> pd.DataFrame:
	"""Validate and normalize one local or S3 dashboard export."""
	path = str(source)
	if not data.columns.is_unique:
		raise DashboardArtifactError(
			f"Dashboard export '{path}' must have unique column names."
		)
	missing = sorted(set(_EXPORT_COLUMNS[name]) - set(data.columns))
	if missing:
		raise DashboardArtifactError(
			f"Dashboard export '{path}' is missing required columns: {missing}. "
			"Regenerate the exports with export-dashboard."
		)
	result = data.loc[:, list(_EXPORT_COLUMNS[name])].copy()
	for column in _TIMESTAMP_COLUMNS[name]:
		try:
			parsed = pd.to_datetime(
				result[column], utc=True, errors="raise", format="mixed"
			)
			if parsed.isna().any():
				raise ValueError("Missing timestamps")
			result[column] = parsed.astype("datetime64[ns, UTC]")
		except (ValueError, TypeError, OverflowError) as exc:
			raise DashboardArtifactError(
				f"Dashboard export '{path}' has invalid timestamps in '{column}'."
			) from exc
	sort_columns = (
		["timestamp", "strategy"]
		if "timestamp" in result
		else ["strategy"] if "strategy" in result else ["model_version"]
	)
	return result.sort_values(sort_columns, kind="stable").reset_index(drop=True)


def _load_artifact(path: Path, name: str) -> pd.DataFrame:
	try:
		data = pd.read_parquet(path)
	except (OSError, ValueError, ArrowException) as exc:
		raise DashboardArtifactError(
			f"Cannot read dashboard export '{path}'. Check file access and "
			"regenerate it with export-dashboard if needed."
		) from exc

	return _normalize_export(data, name, path)


def _load_s3_exports(
	exports_dir: str, *, client: Any = None
) -> dict[str, pd.DataFrame]:
	"""Read the four historical exports from an S3 directory without writes."""
	try:
		store = build_store(exports_dir, client=client)
	except (TypeError, ValueError) as exc:
		raise DashboardArtifactError(
			f"Invalid dashboard export store {exports_dir!r}."
		) from exc
	keys = {name: f"{name}.parquet" for name in _EXPORT_COLUMNS}
	try:
		missing = [
			f"{exports_dir.rstrip('/')}/{key}"
			for key in keys.values()
			if not store.exists(key)
		]
	except Exception as exc:
		raise DashboardArtifactError(
			f"Cannot access dashboard export store '{exports_dir}'. Check the "
			"AWS dependency, credentials, region, and task-role permissions."
		) from exc
	if missing:
		raise DashboardArtifactError(
			f"Missing dashboard exports: {', '.join(missing)}. Upload artifacts "
			"produced by export-dashboard before opening the dashboard."
		)
	loaded = {}
	for name, key in keys.items():
		source = f"{exports_dir.rstrip('/')}/{key}"
		try:
			frame = store.read_frame(key)
		except Exception as exc:
			raise DashboardArtifactError(
				f"Cannot read dashboard export '{source}'. Check object access and "
				"regenerate it with export-dashboard if needed."
			) from exc
		loaded[name] = _normalize_export(frame, name, source)
	return loaded


def load_dashboard_artifacts(
	exports_dir: str | Path = Path("reports/dashboard_exports"),
	*,
	client: Any = None,
) -> dict[str, pd.DataFrame]:
	"""Return the four historical exports from a local or S3 directory.

	The default directory is relative to the working directory; callers may
	supply their configured export directory. Require all four Parquet files
	and their display columns, including schemas on empty tables. Normalize
	timestamps to UTC, sort rows, and reset indexes. Naive timestamps are
	interpreted as UTC. Preserve stored values and missing observations without
	computing metrics, loading models, or writing files. Raise
	DashboardArtifactError with file-specific guidance for invalid exports.
	"""
	if str(exports_dir).startswith("s3://"):
		return _load_s3_exports(str(exports_dir), client=client)
	paths = {
		name: Path(exports_dir) / f"{name}.parquet" for name in _EXPORT_COLUMNS
	}
	missing = [str(path) for path in paths.values() if not path.is_file()]
	if missing:
		raise DashboardArtifactError(
			f"Missing dashboard exports: {', '.join(missing)}. "
			"Run export-dashboard on saved experiment artifacts before "
			"opening the dashboard."
		)
	return {name: _load_artifact(path, name) for name, path in paths.items()}


def _normalize_live_frame(
	frame: pd.DataFrame,
	*,
	key: str,
	columns: tuple[str, ...],
	timestamp_columns: tuple[str, ...],
	expected_strategy: str,
) -> pd.DataFrame:
	"""Validate one live artifact and normalize its timestamps for display."""
	if not frame.columns.is_unique:
		raise DashboardArtifactError(
			f"Live artifact '{key}' must have unique column names."
		)
	missing = sorted(set(columns) - set(frame.columns))
	if missing:
		raise DashboardArtifactError(
			f"Live artifact '{key}' is missing required columns: {missing}."
		)
	result = frame.loc[:, list(columns)].copy()
	if key.endswith("/forecasts.parquet") and result.empty:
		raise DashboardArtifactError(f"Live artifact '{key}' is empty.")
	strategies = set(result["strategy"].dropna().astype(str))
	if strategies and strategies != {expected_strategy}:
		raise DashboardArtifactError(
			f"Live artifact '{key}' contains strategies {sorted(strategies)}, "
			f"expected only {expected_strategy!r}."
		)
	if result["strategy"].isna().any():
		raise DashboardArtifactError(
			f"Live artifact '{key}' contains a missing strategy."
		)
	for column in timestamp_columns:
		try:
			parsed = pd.to_datetime(
				result[column], utc=True, errors="raise", format="mixed"
			)
			if parsed.isna().any():
				raise ValueError("Missing timestamps")
			result[column] = parsed.astype("datetime64[ns, UTC]")
		except (ValueError, TypeError, OverflowError) as exc:
			raise DashboardArtifactError(
				f"Live artifact '{key}' has invalid timestamps in '{column}'."
			) from exc
	if "delivery_date" in result:
		try:
			parsed_dates = pd.to_datetime(
				result["delivery_date"], errors="raise", format="%Y-%m-%d"
			)
			if parsed_dates.isna().any():
				raise ValueError("Missing delivery dates")
			result["delivery_date"] = parsed_dates.dt.strftime("%Y-%m-%d")
		except (ValueError, TypeError, OverflowError) as exc:
			raise DashboardArtifactError(
				f"Live artifact '{key}' has invalid delivery dates."
			) from exc
	for column in ("prediction", "actual", "threshold", "rolling_rmse"):
		if column not in result:
			continue
		try:
			result[column] = pd.to_numeric(result[column], errors="raise")
		except (ValueError, TypeError) as exc:
			raise DashboardArtifactError(
				f"Live artifact '{key}' has non-numeric values in '{column}'."
			) from exc
		if not result[column].dropna().map(isfinite).all():
			raise DashboardArtifactError(
				f"Live artifact '{key}' has non-finite values in '{column}'."
			)
	return result.sort_values(["timestamp", "strategy"], kind="stable").reset_index(
		drop=True
	)


def _read_live_frame(
	store: ArtifactStore,
	key: str,
	columns: tuple[str, ...],
	timestamp_columns: tuple[str, ...],
	expected_strategy: str,
) -> pd.DataFrame:
	"""Read one required live Parquet artifact with a dashboard-facing error."""
	try:
		if not store.exists(key):
			raise KeyError(key)
		frame = store.read_frame(key)
	except ModuleNotFoundError as exc:
		if exc.name == "boto3":
			raise DashboardArtifactError(
				"Reading live S3 artifacts requires the optional AWS dependency. "
				"Install it with 'uv sync --extra aws --extra dashboard'."
			) from exc
		raise
	except Exception as exc:
		raise DashboardArtifactError(
			f"Cannot read required live artifact '{key}'. Run the daily forecast "
			"successfully before opening the Live tab."
		) from exc
	try:
		return _normalize_live_frame(
			frame,
			key=key,
			columns=columns,
			timestamp_columns=timestamp_columns,
			expected_strategy=expected_strategy,
		)
	except DashboardArtifactError:
		raise
	except Exception as exc:
		raise DashboardArtifactError(
			f"Cannot normalize live artifact '{key}' for display."
		) from exc


def _read_live_yaml(store: ArtifactStore, key: str) -> dict[str, Any]:
	"""Read one required live YAML artifact with a clear error."""
	try:
		if not store.exists(key):
			raise KeyError(key)
		payload = store.read_yaml(key)
	except Exception as exc:
		raise DashboardArtifactError(
			f"Cannot read required live artifact '{key}'. Run the daily forecast "
			"successfully before opening the Live tab."
		) from exc
	if not isinstance(payload, dict):
		raise DashboardArtifactError(f"Live artifact '{key}' must contain a mapping.")
	return payload


def load_live_artifacts(
	destination: str | Path,
	*,
	client: Any = None,
) -> dict[str, Any]:
	"""Load the three strategies' live forecast state from local storage or S3.

	``destination`` accepts the same local directory or ``s3://bucket/prefix``
	contract as the daily forecast. The optional client exists for credential-free
	tests; production uses boto3's role-based default credential chain lazily.
	This function only reads persisted artifacts and never invokes the pipeline.
	"""
	if not str(destination).strip():
		raise DashboardArtifactError("A live artifact store is required.")
	try:
		store = build_store(destination, client=client)
	except (TypeError, ValueError) as exc:
		raise DashboardArtifactError(
			f"Invalid live artifact store {str(destination)!r}."
		) from exc
	latest_before = _read_live_yaml(store, "live/latest_run.yaml")
	forecasts = []
	events = []
	states = []
	for strategy in LIVE_STRATEGIES:
		keys = strategy_keys(strategy)
		forecasts.append(
			_read_live_frame(
				store,
				keys["forecasts"],
				_LIVE_FORECAST_COLUMNS,
				("timestamp", "forecast_timestamp"),
				strategy,
			)
		)
		events.append(
			_read_live_frame(
				store,
				keys["events"],
				_LIVE_EVENT_COLUMNS,
				("timestamp", "training_window_start", "training_window_end"),
				strategy,
			)
		)
		state = _read_live_yaml(store, keys["state"])
		missing = sorted(set(_LIVE_STATE_COLUMNS) - set(state))
		if missing:
			raise DashboardArtifactError(
				f"Live artifact '{keys['state']}' is missing required fields: {missing}."
			)
		if state["strategy"] != strategy:
			raise DashboardArtifactError(
				f"Live artifact '{keys['state']}' identifies strategy "
				f"{state['strategy']!r}, expected {strategy!r}."
			)
		states.append({column: state[column] for column in _LIVE_STATE_COLUMNS})

	state_frame = pd.DataFrame(states, columns=_LIVE_STATE_COLUMNS)
	for column in ("last_issuance", "updated_at"):
		try:
			state_frame[column] = pd.to_datetime(
				state_frame[column], utc=True, errors="raise", format="mixed"
			).astype("datetime64[ns, UTC]")
			if state_frame[column].isna().any():
				raise ValueError("Missing timestamps")
		except (ValueError, TypeError, OverflowError) as exc:
			raise DashboardArtifactError(
				f"Live strategy states have invalid timestamps in '{column}'."
			) from exc

	latest_after = _read_live_yaml(store, "live/latest_run.yaml")
	if latest_before != latest_after:
		raise DashboardArtifactError(
			"Live artifacts changed while the dashboard was reading them. Retry "
			"after the daily forecast finishes."
		)
	for field in ("ran_at", "issuance", "market_through"):
		try:
			value = pd.Timestamp(latest_after[field])
			if pd.isna(value) or value.tzinfo is None:
				raise ValueError("Timestamp must be timezone-aware")
		except (KeyError, ValueError, TypeError, OverflowError) as exc:
			raise DashboardArtifactError(
				f"Live artifact 'live/latest_run.yaml' has invalid '{field}'."
			) from exc
	try:
		pd.to_datetime(
			latest_after["delivery_date"], errors="raise", format="%Y-%m-%d"
		)
	except (KeyError, ValueError, TypeError, OverflowError) as exc:
		raise DashboardArtifactError(
			"Live artifact 'live/latest_run.yaml' has an invalid 'delivery_date'."
		) from exc
	latest_rows = latest_after.get("strategies")
	if not isinstance(latest_rows, list):
		raise DashboardArtifactError(
			"Live artifact 'live/latest_run.yaml' must contain strategy summaries."
		)
	summaries = {
		row.get("strategy"): row for row in latest_rows if isinstance(row, dict)
	}
	if set(summaries) != set(LIVE_STRATEGIES):
		raise DashboardArtifactError(
			"Live artifact 'live/latest_run.yaml' does not contain exactly the "
			"three canonical strategies."
		)
	for state in states:
		summary = summaries[state["strategy"]]
		for state_field, summary_field in (
			("model_version", "model_version"),
			("last_delivery_date", "delivery_date"),
		):
			if state[state_field] != summary.get(summary_field):
				raise DashboardArtifactError(
					f"Live state for {state['strategy']!r} does not match the latest "
					f"run field {summary_field!r}. Retry after the run finishes."
				)

	combined_forecasts = pd.concat(forecasts, ignore_index=True).sort_values(
			["timestamp", "strategy"], kind="stable"
		).reset_index(drop=True)
	for strategy, summary in summaries.items():
		latest_rows_for_strategy = combined_forecasts.loc[
			(combined_forecasts["strategy"] == strategy)
			& (combined_forecasts["delivery_date"] == summary.get("delivery_date"))
		]
		if latest_rows_for_strategy.empty or set(
			latest_rows_for_strategy["model_version"].astype(str)
		) != {str(summary.get("model_version"))}:
			raise DashboardArtifactError(
				f"Live forecasts for {strategy!r} do not match the latest run. "
				"Retry after the run finishes."
			)

	return {
		"forecasts": combined_forecasts,
		"retraining_events": pd.concat(events, ignore_index=True).sort_values(
			["timestamp", "strategy"], kind="stable"
		).reset_index(drop=True),
		"states": state_frame.sort_values("strategy", kind="stable").reset_index(
			drop=True
		),
		"latest_run": latest_after,
	}
