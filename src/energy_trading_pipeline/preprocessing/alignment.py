"""Exact hourly joins of normalized market and optional exogenous records."""

from datetime import date
import logging
from typing import Any

import pandas as pd

from energy_trading_pipeline.preprocessing.validation import summarize_records


logger = logging.getLogger(__name__)


def align_hourly_data(
    prices_de: pd.DataFrame,
    prices_fr: pd.DataFrame,
    *,
    start_date: str | date,
    end_date: str | date,
    weather: pd.DataFrame | None = None,
    grid: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Return an aligned copy and a report for inclusive UTC calendar dates.

    Pass ``config["dates"]`` values explicitly. Inputs must have parsed, aware,
    unique, on-hour timestamps; normalize and clean sources before calling.
    Required prices must cover every requested hour. Optional columns with any
    missing aligned values are excluded with warnings, never filled. Grid may
    contain load and generation columns. No resampling or features are computed.
    """
    try:
        start = date.fromisoformat(str(start_date))
        end = date.fromisoformat(str(end_date))
    except ValueError as exc:
        raise ValueError("start_date and end_date must be ISO calendar dates") from exc
    if start > end:
        raise ValueError("start_date must not be after end_date")
    timeline = pd.date_range(
        pd.Timestamp(start, tz="UTC"),
        pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1),
        freq="h",
        inclusive="left",
        name="timestamp",
    )
    result = pd.DataFrame(index=timeline)
    report: dict[str, Any] = {
        "stage": "preprocessing",
        "operation": "hourly_alignment",
        "timezone": "UTC",
        "date_bounds": "inclusive_calendar_dates",
        "date_range": {
            "start": timeline[0].isoformat(),
            "end": timeline[-1].isoformat(),
        },
        "missing_optional_sources": [],
        "excluded_optional_columns": [],
        "missing_counts": {},
    }
    seen_columns: set[str] = set()
    for name, frame, required in (
        ("prices_de", prices_de, ["price_de"]),
        ("prices_fr", prices_fr, ["price_fr"]),
        ("weather", weather, []),
        ("grid", grid, []),
    ):
        if not required and (frame is None or frame.empty):
            report["missing_optional_sources"].append(name)
            logger.warning("Optional source unavailable: %s (hourly_alignment)", name)
            continue
        if frame is None:
            raise ValueError(f"Missing required source: {name}")
        quality = summarize_records(frame)
        absent = sorted(set(required) - set(frame.columns))
        if absent:
            raise ValueError(f"Missing required columns in {name}: {absent}")
        if quality["duplicate_count"]:
            raise ValueError(f"Duplicate timestamps in {name}; clean before alignment")
        utc = frame["timestamp"].dt.tz_convert("UTC")
        if (utc != utc.dt.floor("h")).any():
            raise ValueError(f"Non-hourly timestamps in {name}; resampling is not implicit")
        columns = set(frame.columns) - {"timestamp"}
        overlap = sorted(seen_columns & columns)
        if overlap:
            raise ValueError(f"Overlapping columns in {name}: {overlap}")
        seen_columns.update(columns)
        aligned = frame.assign(timestamp=utc).set_index("timestamp").reindex(timeline)
        counts = {column: int(count) for column, count in aligned.isna().sum().items()}
        report["missing_counts"].update(counts)
        missing_required = {
            column: counts[column] for column in required if counts[column]
        }
        if missing_required:
            raise ValueError(
                f"Missing required hourly values in {name}: {missing_required} "
                f"for {start} through {end} UTC"
            )
        excluded = [
            column for column, count in counts.items() if count and column not in required
        ]
        if excluded:
            report["excluded_optional_columns"].extend(excluded)
            logger.warning(
                "Optional columns excluded due to missing hourly values: %s "
                "(hourly_alignment, source=%s)",
                excluded,
                name,
            )
        result = result.join(aligned.drop(columns=excluded))

    result = result.reset_index()
    report.update(output_rows=len(result), retained_columns=result.columns.tolist())
    logger.info(
        "Hourly alignment completed: rows=%d, start=%s, end=%s, columns=%s",
        len(result),
        start,
        end,
        report["retained_columns"],
    )
    return result, report
