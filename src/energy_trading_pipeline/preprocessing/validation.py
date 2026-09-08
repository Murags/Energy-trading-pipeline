"""Lightweight validation of normalized timestamps and record quality."""

import logging
from typing import Any

import pandas as pd


logger = logging.getLogger(__name__)


def summarize_records(df: pd.DataFrame) -> dict[str, Any]:
    """Count null cells and surplus duplicate instants without changing records.

    Require nonempty data with unique column names and parsed, timezone-aware,
    non-null timestamps. Hourly gaps are left to hourly validation/alignment.
    """
    if not df.columns.is_unique:
        raise ValueError("Duplicate column names are not supported")
    if "timestamp" not in df.columns:
        raise ValueError("Missing required column: timestamp")
    if df.empty:
        raise ValueError("Cannot clean an empty dataset")
    timestamps = df["timestamp"]
    if not isinstance(timestamps.dtype, pd.DatetimeTZDtype):
        raise ValueError("timestamp must contain parsed timezone-aware datetimes")
    if timestamps.isna().any():
        raise ValueError("timestamp contains missing values; normalize before cleaning")
    utc = timestamps.dt.tz_convert("UTC")
    duplicates = utc[utc.duplicated()]
    return {
        "missing_counts": {column: int(count) for column, count in df.isna().sum().items()},
        "duplicate_count": len(duplicates),
        "duplicate_timestamps": [
            value.isoformat() for value in duplicates.drop_duplicates().sort_values()
        ],
        "date_range": {"start": utc.min().isoformat(), "end": utc.max().isoformat()},
    }


def validate_hourly_index(timestamps: pd.Series) -> dict[str, Any]:
    """Report ordering, duplicate instants, UTC off-hour values, and internal gaps.

    Require a nonempty, timezone-aware datetime series without missing values.
    Missing hours are whole UTC hours within the observed endpoints only; this
    does not validate coverage of an external configured date range. Duplicate
    count means surplus rows, and a single on-hour timestamp is valid. No rows
    are removed, rounded, filled, or reordered by this function.
    """
    if timestamps.empty:
        raise ValueError("Cannot validate an empty timestamp series")
    if not isinstance(timestamps.dtype, pd.DatetimeTZDtype):
        raise ValueError("timestamp must contain parsed timezone-aware datetimes")
    if timestamps.isna().any():
        raise ValueError("timestamp contains missing values")

    utc = timestamps.dt.tz_convert("UTC")
    duplicates = utc[utc.duplicated()]
    non_hourly = utc[utc != utc.dt.floor("h")]
    expected = pd.date_range(utc.min().ceil("h"), utc.max().floor("h"), freq="h")
    missing = expected.difference(pd.DatetimeIndex(utc))
    is_sorted = bool(utc.is_monotonic_increasing)
    report = {
        "is_hourly": is_sorted
        and not (len(duplicates) or len(non_hourly) or len(missing)),
        "is_sorted": is_sorted,
        "duplicate_count": len(duplicates),
        "duplicate_timestamps": [
            value.isoformat() for value in duplicates.drop_duplicates().sort_values()
        ],
        "non_hourly_count": len(non_hourly),
        "non_hourly_timestamps": [
            value.isoformat() for value in non_hourly.drop_duplicates().sort_values()
        ],
        "missing_hour_count": len(missing),
        "missing_hours": [value.isoformat() for value in missing],
    }
    if not report["is_hourly"]:
        logger.warning(
            "Timestamp hourly validation: sorted=%s, duplicate_rows=%d, "
            "non_hourly_rows=%d, missing_hours=%d",
            is_sorted,
            len(duplicates),
            len(non_hourly),
            len(missing),
        )
    return report
