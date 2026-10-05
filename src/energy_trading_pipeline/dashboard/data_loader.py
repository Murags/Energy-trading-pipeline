"""Read-only loading of the four Story 8.4 dashboard Parquet exports."""

from pathlib import Path

import pandas as pd
from pyarrow import ArrowException


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


class DashboardArtifactError(ValueError):
	"""An exported artifact is missing, unreadable, or unsuitable for display."""


def _load_artifact(path: Path, name: str) -> pd.DataFrame:
	try:
		data = pd.read_parquet(path)
	except (OSError, ValueError, ArrowException) as exc:
		raise DashboardArtifactError(
			f"Cannot read dashboard export '{path}'. Check file access and "
			"regenerate it with export-dashboard if needed."
		) from exc

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


def load_dashboard_artifacts(
	exports_dir: str | Path = Path("reports/dashboard_exports"),
) -> dict[str, pd.DataFrame]:
	"""Return forecasts, metrics, retraining_events, and model_versions by name.

	The default directory is relative to the working directory; callers may
	supply their configured export directory. Require all four Parquet files
	and their display columns, including schemas on empty tables. Normalize
	timestamps to UTC, sort rows, and reset indexes. Naive timestamps are
	interpreted as UTC. Preserve stored values and missing observations without
	computing metrics, loading models, or writing files. Raise
	DashboardArtifactError with file-specific guidance for invalid exports.
	"""
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
