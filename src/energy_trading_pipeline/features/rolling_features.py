"""Leakage-safe rolling feature generation for the spread and price columns."""

from collections.abc import Sequence
from typing import Any

import pandas as pd
from pandas.api.types import is_bool_dtype, is_complex_dtype, is_numeric_dtype

from energy_trading_pipeline.preprocessing.validation import validate_hourly_index

DEFAULT_ROLLING_SOURCE_COLUMNS: tuple[str, ...] = ("spread", "price_de", "price_fr")
ROLLING_STATISTICS: tuple[str, ...] = ("mean", "std")
INSUFFICIENT_WINDOW_POLICY = "retain_rows_with_null_rolling_features"
# Every window is shifted by one hour so a row's own value is never aggregated.
ROLLING_SHIFT_HOURS = 1
# A standard deviation needs at least two observations, so one-hour windows are
# rejected rather than silently emitting an all-null ``_rolling_std_1`` column.
MIN_ROLLING_WINDOW_HOURS = 2
STD_DDOF = 1


def rolling_column_name(column: str, statistic: str, window_hours: int) -> str:
    """Return the canonical ``snake_case`` name, e.g. ``spread_rolling_mean_24``."""
    return f"{column}_rolling_{statistic}_{window_hours}"


def build_rolling_features(
    df: pd.DataFrame,
    window_hours: Sequence[int],
    *,
    columns: Sequence[str] = DEFAULT_ROLLING_SOURCE_COLUMNS,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Append shifted rolling mean/std features and describe them in metadata.

    Require ``timestamp`` plus every source column on unique, contiguous hourly
    rows so that a window of ``n`` rows equals exactly ``n`` hours. The result is
    a sorted UTC copy; the input is not mutated and existing rolling columns with
    the same name are recomputed.

    Each source is shifted by ``ROLLING_SHIFT_HOURS`` *before* aggregation, so a
    row's window covers the ``n`` hours strictly before it and never includes its
    own or any later value. Windows are only aggregated when complete
    (``min_periods`` equals the window), so partial windows and windows spanning a
    null source value yield nulls instead of a shorter-window value. Those rows
    are retained rather than dropped; the metadata reports that policy, the
    generated columns, and how many rows lack a full window.
    """
    windows = _validate_window_hours(window_hours)
    if not df.columns.is_unique:
        raise ValueError("Duplicate column names are not supported")
    sources = _validate_source_columns(df, columns)
    if df.empty:
        raise ValueError("Cannot build rolling features from an empty dataset")

    result = df.copy()
    if not isinstance(result["timestamp"].dtype, pd.DatetimeTZDtype):
        raise ValueError("timestamp must contain parsed timezone-aware datetimes")
    result["timestamp"] = result["timestamp"].dt.tz_convert("UTC")
    result = result.sort_values("timestamp").reset_index(drop=True)
    if not validate_hourly_index(result["timestamp"])["is_hourly"]:
        raise ValueError("Expected unique, contiguous hourly timestamps; align first")

    generated: list[str] = []
    for column in sources:
        # Shift first: the window then ends at the previous hour, not this one.
        shifted = result[column].astype("float64").shift(ROLLING_SHIFT_HOURS)
        for window in windows:
            # Only complete windows aggregate, so a partial window stays null
            # instead of quietly becoming a shorter-window statistic.
            rolling = shifted.rolling(window=window, min_periods=window)
            aggregated = {"mean": rolling.mean(), "std": rolling.std(ddof=STD_DDOF)}
            for statistic in ROLLING_STATISTICS:
                name = rolling_column_name(column, statistic, window)
                result[name] = aggregated[statistic]
                generated.append(name)
    # Move any recomputed pre-existing rolling columns to the appended position.
    base_columns = [column for column in result.columns if column not in generated]
    result = result[base_columns + generated]

    min_history = max(windows)
    metadata = {
        "stage": "features.rolling",
        "source_columns": list(sources),
        "window_hours": windows,
        "statistics": list(ROLLING_STATISTICS),
        "generated_columns": generated,
        "shift_hours": ROLLING_SHIFT_HOURS,
        "std_ddof": STD_DDOF,
        "insufficient_window_policy": INSUFFICIENT_WINDOW_POLICY,
        "min_history_hours": min_history,
        "incomplete_window_rows": min(min_history, len(result)),
        "output_rows": len(result),
    }
    return result, metadata


def _validate_window_hours(window_hours: Any) -> list[int]:
    """Return sorted, unique integer windows of at least the minimum length."""
    if isinstance(window_hours, (str, bytes)) or not isinstance(
        window_hours, Sequence
    ):
        raise ValueError(
            "window_hours must be a nonempty sequence of integers "
            f"of at least {MIN_ROLLING_WINDOW_HOURS}"
        )
    if len(window_hours) == 0:
        raise ValueError(
            "window_hours must be a nonempty sequence of integers "
            f"of at least {MIN_ROLLING_WINDOW_HOURS}"
        )
    for window in window_hours:
        if (
            isinstance(window, bool)
            or not isinstance(window, int)
            or window < MIN_ROLLING_WINDOW_HOURS
        ):
            raise ValueError(
                f"window_hours must contain integers of at least "
                f"{MIN_ROLLING_WINDOW_HOURS}; got {window!r}. Shorter windows "
                "cannot produce a standard deviation."
            )
    return sorted(set(int(window) for window in window_hours))


def _validate_source_columns(df: pd.DataFrame, columns: Sequence[str]) -> list[str]:
    """Return the source columns after checking presence and numeric dtype."""
    if isinstance(columns, (str, bytes)) or len(columns) == 0:
        raise ValueError("columns must be a nonempty sequence of column names")
    sources = list(dict.fromkeys(columns))
    if "timestamp" in sources:
        raise ValueError("timestamp cannot be a rolling feature source")
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
            raise ValueError(
                f"{column} must contain real numeric values to be aggregated"
            )
    return sources
