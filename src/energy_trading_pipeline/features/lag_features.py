"""Leakage-safe lag feature generation for the spread and price columns."""

from collections.abc import Sequence
from typing import Any

import pandas as pd
from pandas.api.types import is_bool_dtype, is_complex_dtype, is_numeric_dtype

from energy_trading_pipeline.preprocessing.validation import validate_hourly_index

DEFAULT_LAG_SOURCE_COLUMNS: tuple[str, ...] = ("spread", "price_de", "price_fr")
INSUFFICIENT_HISTORY_POLICY = "retain_rows_with_null_lags"


def lag_column_name(column: str, lag_hours: int) -> str:
    """Return the canonical ``snake_case`` name, e.g. ``spread_lag_24``."""
    return f"{column}_lag_{lag_hours}"


def build_lag_features(
    df: pd.DataFrame,
    lag_hours: Sequence[int],
    *,
    columns: Sequence[str] = DEFAULT_LAG_SOURCE_COLUMNS,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Append ``<column>_lag_<hours>`` features and describe them in metadata.

    Require ``timestamp`` plus every source column on unique, contiguous hourly
    rows so that a shift of ``n`` rows equals a lag of exactly ``n`` hours. The
    result is a sorted UTC copy; the input is not mutated and existing lag
    columns with the same name are recomputed. Each lag is strictly positive, so
    a row's own value never feeds its own feature. Rows without ``n`` hours of
    history keep null lag values rather than being dropped; the metadata reports
    that policy, the generated columns, and how many rows lack full history.
    """
    lags = _validate_lag_hours(lag_hours)
    if not df.columns.is_unique:
        raise ValueError("Duplicate column names are not supported")
    sources = _validate_source_columns(df, columns)
    if df.empty:
        raise ValueError("Cannot build lag features from an empty dataset")

    result = df.copy()
    if not isinstance(result["timestamp"].dtype, pd.DatetimeTZDtype):
        raise ValueError("timestamp must contain parsed timezone-aware datetimes")
    result["timestamp"] = result["timestamp"].dt.tz_convert("UTC")
    result = result.sort_values("timestamp").reset_index(drop=True)
    if not validate_hourly_index(result["timestamp"])["is_hourly"]:
        raise ValueError("Expected unique, contiguous hourly timestamps; align first")

    generated: list[str] = []
    for column in sources:
        values = result[column].astype("float64")
        for lag in lags:
            name = lag_column_name(column, lag)
            result[name] = values.shift(lag)
            generated.append(name)
    # Move any recomputed pre-existing lag columns to the appended position.
    base_columns = [column for column in result.columns if column not in generated]
    result = result[base_columns + generated]

    min_history = max(lags)
    metadata = {
        "stage": "features.lag",
        "source_columns": list(sources),
        "lag_hours": lags,
        "generated_columns": generated,
        "insufficient_history_policy": INSUFFICIENT_HISTORY_POLICY,
        "min_history_hours": min_history,
        "incomplete_history_rows": min(min_history, len(result)),
        "output_rows": len(result),
    }
    return result, metadata


def _validate_lag_hours(lag_hours: Any) -> list[int]:
    """Return sorted, unique, strictly positive integer lags."""
    if isinstance(lag_hours, (str, bytes)) or not isinstance(lag_hours, Sequence):
        raise ValueError("lag_hours must be a nonempty sequence of positive integers")
    if len(lag_hours) == 0:
        raise ValueError("lag_hours must be a nonempty sequence of positive integers")
    for lag in lag_hours:
        if isinstance(lag, bool) or not isinstance(lag, int) or lag < 1:
            raise ValueError(
                f"lag_hours must contain positive integers only; got {lag!r}. "
                "A lag of zero would use the target timestamp's own value."
            )
    return sorted(set(int(lag) for lag in lag_hours))


def _validate_source_columns(df: pd.DataFrame, columns: Sequence[str]) -> list[str]:
    """Return the source columns after checking presence and numeric dtype."""
    if isinstance(columns, (str, bytes)) or len(columns) == 0:
        raise ValueError("columns must be a nonempty sequence of column names")
    sources = list(dict.fromkeys(columns))
    if "timestamp" in sources:
        raise ValueError("timestamp cannot be lagged as a feature source")
    missing = sorted({"timestamp", *sources} - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    for column in sources:
        dtype = df[column].dtype
        if (
            not is_numeric_dtype(dtype)
            or is_bool_dtype(dtype)
            or is_complex_dtype(dtype)
        ):
            raise ValueError(f"{column} must contain real numeric values to be lagged")
    return sources
