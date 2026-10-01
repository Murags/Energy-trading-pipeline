"""Canonical forecast records and local Parquet/CSV persistence.

``timestamp`` is the target delivery period; ``forecast_timestamp`` is issuance.
Both are required and normalized from timezone-aware inputs to UTC. Errors use
``actual - prediction``. An unavailable actual remains NaN, as do its errors;
callers must only supply actuals once available at their decision time.
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_complex_dtype, is_numeric_dtype


INPUT_COLUMNS = (
    "timestamp",
    "forecast_timestamp",
    "prediction",
    "actual",
    "strategy",
    "model_version",
)
ERROR_COLUMNS = ("error", "squared_error", "absolute_error")
FORECAST_LOG_COLUMNS = (
    *INPUT_COLUMNS[:4],
    *ERROR_COLUMNS,
    *INPUT_COLUMNS[4:],
)
STRATEGIES = frozenset({"no_retraining", "fixed_schedule", "performance_triggered"})


def _require_columns(df: pd.DataFrame, columns: tuple[str, ...]) -> None:
    if not df.columns.is_unique:
        raise ValueError("Duplicate column names are not supported")
    missing = sorted(set(columns) - set(df.columns))
    if missing:
        raise ValueError(f"Missing required forecast log columns: {missing}")


def _utc_timestamps(values: pd.Series, column: str) -> pd.Series:
    """Reject naive/missing inputs rather than silently assuming a timezone."""
    parsed = []
    for value in values:
        message = f"{column} must contain valid timezone-aware timestamps"
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


def _numeric_values(
    values: pd.Series, column: str, *, allow_missing: bool
) -> pd.Series:
    """Use real float arithmetic, avoiding integer wraparound and infinities."""
    message = f"{column} must contain finite real numeric values"
    if not allow_missing and values.isna().any():
        raise ValueError(message)
    if values.empty or (allow_missing and values.isna().all()):
        return pd.Series(np.nan, index=values.index, dtype="float64")
    if (
        not is_numeric_dtype(values.dtype)
        or is_bool_dtype(values.dtype)
        or is_complex_dtype(values.dtype)
    ):
        raise ValueError(message)
    result = values.astype("float64")
    if not np.isfinite(result.dropna()).all():
        raise ValueError(message)
    return result


def build_forecast_log(df: pd.DataFrame) -> pd.DataFrame:
    """Return canonical columns sorted stably by target timestamp, without mutation.

    Require the six INPUT_COLUMNS, including an actual column even when its
    values are missing. Recompute error columns; other input columns are not
    included in the log. Issuance may equal but must not follow the target.
    Strategy must be canonical and model_version a nonblank string. Multiple
    strategies/issuances may share a target timestamp. Empty logs are supported.
    """
    _require_columns(df, INPUT_COLUMNS)
    result = df.loc[:, list(INPUT_COLUMNS)].copy().reset_index(drop=True)
    for column in ("timestamp", "forecast_timestamp"):
        result[column] = _utc_timestamps(result[column], column)
    if (result["forecast_timestamp"] > result["timestamp"]).any():
        raise ValueError("forecast_timestamp must not follow target timestamp")
    for column in ("strategy", "model_version"):
        if any(
            not isinstance(value, str) or not value.strip() for value in result[column]
        ):
            raise ValueError(f"{column} must contain nonempty strings")
        result[column] = result[column].astype(object)
    if not result["strategy"].isin(STRATEGIES).all():
        raise ValueError(f"strategy must be one of {sorted(STRATEGIES)}")
    for column in ("prediction", "actual"):
        result[column] = _numeric_values(
            result[column], column, allow_missing=column == "actual"
        )
    with np.errstate(over="ignore", invalid="ignore"):
        result["error"] = result["actual"] - result["prediction"]
        result["squared_error"] = result["error"] ** 2
        result["absolute_error"] = result["error"].abs()
    for column in ERROR_COLUMNS:
        if not np.isfinite(result.loc[result["actual"].notna(), column]).all():
            raise ValueError(f"{column} calculation produced non-finite values")
    return (
        result.loc[:, list(FORECAST_LOG_COLUMNS)]
        .sort_values("timestamp", kind="stable")
        .reset_index(drop=True)
    )


def _artifact_path(path: Path) -> Path:
    path = Path(path)
    if path.suffix.lower() not in {".parquet", ".csv"}:
        raise ValueError("Unsupported forecast log format; use .parquet or .csv")
    return path


def write_forecast_log(df: pd.DataFrame, output_path: Path) -> Path:
    """Build and write a log without its index, replacing an existing artifact.

    Pass a configured path under the run directory, normally
    ``logs/runs/run_YYYYMMDD_HHMMSS/forecasts.parquet``. Parent directories are
    created after validation. CSV timestamps retain explicit UTC offsets.
    """
    output_path = _artifact_path(output_path)
    result = build_forecast_log(df)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() == ".parquet":
        result.to_parquet(output_path, index=False)
    else:
        result.to_csv(output_path, index=False)
    return output_path


def read_forecast_log(input_path: Path) -> pd.DataFrame:
    """Read, validate, and normalize a complete persisted forecast log.

    Missing columns or inconsistent saved errors fail rather than silently
    repairing an artifact. Float comparisons allow only serialization rounding.
    """
    input_path = _artifact_path(input_path)
    if input_path.suffix.lower() == ".parquet":
        saved = pd.read_parquet(input_path)
    else:
        saved = pd.read_csv(
            input_path,
            dtype={"strategy": str, "model_version": str},
            keep_default_na=False,
            na_values={column: [""] for column in ("actual", *ERROR_COLUMNS)},
            float_precision="round_trip",
        )
    _require_columns(saved, FORECAST_LOG_COLUMNS)
    result = build_forecast_log(saved)
    # Align stored errors with the same stable target ordering as the builder.
    saved["timestamp"] = _utc_timestamps(saved["timestamp"], "timestamp")
    saved = saved.sort_values("timestamp", kind="stable").reset_index(drop=True)
    for column in ERROR_COLUMNS:
        values = _numeric_values(saved[column], column, allow_missing=True)
        if not np.allclose(values, result[column], rtol=1e-12, atol=0, equal_nan=True):
            raise ValueError(f"Saved {column} is inconsistent with actual - prediction")
    return result
