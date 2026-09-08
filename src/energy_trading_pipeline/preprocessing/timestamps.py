"""Normalize source timestamps to UTC without cleaning or filling records."""

from numbers import Number
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd

from energy_trading_pipeline.preprocessing.validation import validate_hourly_index


def normalize_timestamps(
    df: pd.DataFrame, *, source_timezone: str = "UTC"
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Return a chronologically sorted copy and serializable timestamp metadata.

    Naive timestamps are interpreted in ``source_timezone`` (UTC by default).
    Aware timestamps retain their stated instant, even with mixed UTC offsets.
    Ambiguous/nonexistent local DST times and invalid values raise ValueError;
    supply explicit offsets to disambiguate repeated fall-back hours. Numeric
    epochs are rejected because their unit cannot safely be inferred.

    Hourly issues are reported in metadata and warnings, not repaired. Metadata
    is returned explicitly for the caller to persist alongside stage artifacts.
    """
    if "timestamp" not in df.columns:
        raise ValueError("Missing required column: timestamp")
    if df.empty:
        raise ValueError("Cannot normalize an empty timestamp column")
    try:
        timezone = ZoneInfo(source_timezone)
    except (ZoneInfoNotFoundError, ValueError, TypeError) as exc:
        raise ValueError(f"Invalid source_timezone: {source_timezone!r}") from exc

    normalized = []
    source_timezones = set()
    naive_timestamp_count = 0
    # Parse individually so mixed naive/aware values never silently assume UTC.
    for row, value in enumerate(df["timestamp"]):
        try:
            if isinstance(value, Number):
                raise ValueError("Numeric epoch timestamps require an explicit unit")
            timestamp = pd.Timestamp(value)
            if pd.isna(timestamp):
                raise ValueError("Missing timestamp")
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValueError(f"Invalid timestamp at row {row}: {value!r}") from exc

        if timestamp.tzinfo is None:
            naive_timestamp_count += 1
            timestamp = timestamp.tz_localize(timezone, ambiguous="NaT", nonexistent="NaT")
            if pd.isna(timestamp):
                raise ValueError(
                    f"Ambiguous or nonexistent local timestamp at row {row}: "
                    f"{value!r} in {source_timezone}; supply an explicit UTC offset"
                )
        else:
            source_timezones.add(str(timestamp.tzinfo))
        normalized.append(timestamp.tz_convert("UTC"))

    result = df.copy()
    result["timestamp"] = pd.DatetimeIndex(normalized)
    result = result.sort_values("timestamp", kind="stable").reset_index(drop=True)
    metadata = {
        "source_timezone": source_timezone,
        "source_timezones": sorted(source_timezones),
        "normalized_timezone": "UTC",
        "naive_timestamp_count": naive_timestamp_count,
        "dst_policy": {
            "ambiguous": "raise",
            "nonexistent": "raise",
            "aware": "preserve_instant",
        },
        "hourly_validation": validate_hourly_index(result["timestamp"]),
    }
    return result, metadata
