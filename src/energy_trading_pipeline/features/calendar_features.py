"""Deterministic calendar features derived from the normalized UTC timestamp."""

from collections.abc import Sequence
from datetime import date, datetime
import logging
from typing import Any

import pandas as pd

from energy_trading_pipeline.preprocessing.validation import summarize_records


logger = logging.getLogger(__name__)

# Canonical emission order. Columns are always appended in this order, so the
# order they appear in configuration never changes the generated dataset.
CALENDAR_FEATURE_COLUMNS: tuple[str, ...] = (
    "hour",
    "day_of_week",
    "month",
    "is_weekend",
    "is_holiday",
)
# ``is_holiday`` is opt-in because it also requires configured holiday dates.
DEFAULT_CALENDAR_FEATURES: tuple[str, ...] = (
    "hour",
    "day_of_week",
    "month",
    "is_weekend",
)
# pandas numbers Monday as 0, so Saturday and Sunday are 5 and 6.
WEEKEND_DAYS_OF_WEEK: tuple[int, ...] = (5, 6)
# Fixed width so the artifact dtype does not depend on the host platform.
CALENDAR_INTEGER_DTYPE = "int16"
HOLIDAY_DATE_FORMAT = "%Y-%m-%d"
HOLIDAY_DATE_BASIS = "utc_calendar_date"
UNCONFIGURED_HOLIDAY_POLICY = "warn_and_skip_is_holiday"


def build_calendar_features(
    df: pd.DataFrame,
    *,
    features: Sequence[str] = DEFAULT_CALENDAR_FEATURES,
    holiday_dates: Sequence[str | date] = (),
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Append the configured calendar columns and describe them in metadata.

    Every calendar column is a pure function of the row's own UTC timestamp, so
    the output is deterministic and cannot leak information from other rows.
    Require ``timestamp`` to hold parsed, timezone-aware, unique instants; the
    result is a sorted UTC copy, the input is not mutated, and existing calendar
    columns with the same name are recomputed. Hourly gaps are tolerated because
    no calendar column looks beyond its own row.

    ``features`` selects the columns to generate from
    ``CALENDAR_FEATURE_COLUMNS``; an unsupported name fails rather than being
    ignored, because it can only be a configuration mistake. ``is_holiday`` is
    optional: when it is requested without any ``holiday_dates``, it is skipped
    with a warning and reported under ``skipped_features`` instead of emitting a
    column that is uniformly false. Holidays are matched on the UTC calendar
    date.
    """
    requested = _validate_features(features)
    holidays = _validate_holiday_dates(holiday_dates)
    quality = summarize_records(df)
    if quality["duplicate_count"]:
        raise ValueError(
            "Duplicate timestamps are not supported; clean before feature generation"
        )

    result = df.copy()
    result["timestamp"] = result["timestamp"].dt.tz_convert("UTC")
    result = result.sort_values("timestamp").reset_index(drop=True)

    skipped: list[str] = []
    if "is_holiday" in requested and not holidays:
        skipped.append("is_holiday")
        logger.warning(
            "Optional calendar feature skipped: is_holiday "
            "(no holiday dates are configured)"
        )
    if holidays and "is_holiday" not in requested:
        logger.warning(
            "Configured holiday dates are unused because is_holiday "
            "was not requested"
        )

    generated: list[str] = []
    for name in requested:
        if name in skipped:
            continue
        result[name] = _calendar_column(result["timestamp"], name, holidays)
        generated.append(name)
    # Move any recomputed pre-existing calendar columns to the appended position.
    base_columns = [column for column in result.columns if column not in generated]
    result = result[base_columns + generated]

    metadata = {
        "stage": "features.calendar",
        "requested_features": requested,
        "generated_columns": generated,
        "skipped_features": skipped,
        "unconfigured_holiday_policy": UNCONFIGURED_HOLIDAY_POLICY,
        "weekend_days_of_week": list(WEEKEND_DAYS_OF_WEEK),
        "holiday_dates": [value.isoformat() for value in sorted(holidays)],
        "holiday_date_basis": HOLIDAY_DATE_BASIS,
        "timezone": "UTC",
        "output_rows": len(result),
    }
    return result, metadata


def _calendar_column(
    timestamps: pd.Series, name: str, holidays: set[date]
) -> pd.Series:
    """Return one calendar column derived from each row's own UTC timestamp."""
    if name == "hour":
        return timestamps.dt.hour.astype(CALENDAR_INTEGER_DTYPE)
    if name == "day_of_week":
        return timestamps.dt.dayofweek.astype(CALENDAR_INTEGER_DTYPE)
    if name == "month":
        return timestamps.dt.month.astype(CALENDAR_INTEGER_DTYPE)
    if name == "is_weekend":
        return timestamps.dt.dayofweek.isin(WEEKEND_DAYS_OF_WEEK)
    return timestamps.dt.date.isin(holidays)


def _validate_features(features: Any) -> list[str]:
    """Return the requested features de-duplicated in canonical emission order."""
    supported = list(CALENDAR_FEATURE_COLUMNS)
    if isinstance(features, (str, bytes)) or not isinstance(features, Sequence):
        raise ValueError(
            "features must be a nonempty sequence of calendar feature names; "
            f"supported: {supported}"
        )
    if len(features) == 0:
        raise ValueError(
            "features must be a nonempty sequence of calendar feature names; "
            f"supported: {supported}"
        )
    for name in features:
        if not isinstance(name, str):
            raise ValueError(
                f"Calendar feature names must be strings; got {name!r}. "
                f"Supported: {supported}"
            )
    unknown = sorted(set(features) - set(CALENDAR_FEATURE_COLUMNS))
    if unknown:
        raise ValueError(
            f"Unsupported calendar features: {unknown}; supported: {supported}"
        )
    return [name for name in CALENDAR_FEATURE_COLUMNS if name in set(features)]


def _validate_holiday_dates(holiday_dates: Any) -> set[date]:
    """Return the configured holidays as UTC calendar dates."""
    if isinstance(holiday_dates, (str, bytes)) or not isinstance(
        holiday_dates, Sequence
    ):
        raise ValueError(
            "holiday_dates must be a sequence of ISO YYYY-MM-DD calendar dates"
        )
    holidays: set[date] = set()
    for value in holiday_dates:
        # datetime is a date subclass, so reject it before the date branch: an
        # instant would make holiday matching depend on an unstated timezone.
        if isinstance(value, datetime):
            raise ValueError(
                f"Invalid holiday date: {value!r} is an instant, not a calendar date"
            )
        if isinstance(value, date):
            holidays.add(value)
            continue
        if not isinstance(value, str):
            raise ValueError(
                f"Invalid holiday date: {value!r} is not an ISO YYYY-MM-DD date"
            )
        try:
            holidays.add(datetime.strptime(value, HOLIDAY_DATE_FORMAT).date())
        except ValueError as exc:
            raise ValueError(
                f"Invalid holiday date: {value!r} is not an ISO YYYY-MM-DD date"
            ) from exc
    return holidays
