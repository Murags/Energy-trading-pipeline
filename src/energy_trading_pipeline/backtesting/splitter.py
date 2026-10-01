"""Generate rolling, half-open UTC windows without reading data or fitting models."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
import re
from typing import Any

import pandas as pd


REQUIRED_BACKTEST_KEYS = (
    "evaluation_start_date",
    "evaluation_end_date",
    "train_window_days",
    "validation_window_days",
    "forecast_horizon_hours",
)


@dataclass(frozen=True)
class TimeWindow:
    """An immutable UTC interval including `start` and excluding `end`.

    Endpoints must be timezone-aware pandas timestamps, representable at
    nanosecond resolution. Other aware timezones are normalized to UTC.
    """

    start: pd.Timestamp
    end: pd.Timestamp

    def __post_init__(self) -> None:
        for name in ("start", "end"):
            value = getattr(self, name)
            if not isinstance(value, pd.Timestamp) or value.tzinfo is None:
                raise ValueError(
                    f"TimeWindow.{name} must be a timezone-aware timestamp"
                )
            try:
                value = value.tz_convert("UTC").as_unit("ns")
            except (ValueError, OverflowError) as exc:
                raise ValueError(
                    f"TimeWindow.{name} is outside timestamp limits"
                ) from exc
            object.__setattr__(self, name, value)
        if self.start >= self.end:
            raise ValueError("TimeWindow.end must be strictly after TimeWindow.start")


@dataclass(frozen=True)
class BacktestWindow:
    """Ordered, non-overlapping train, validation, and forecast intervals."""

    train: TimeWindow
    validation: TimeWindow
    forecast: TimeWindow

    def __post_init__(self) -> None:
        for name in ("train", "validation", "forecast"):
            if not isinstance(getattr(self, name), TimeWindow):
                raise ValueError(f"BacktestWindow.{name} must be a TimeWindow")
        if self.train.end > self.validation.start:
            raise ValueError("train.end must not follow validation.start")
        if self.validation.end > self.forecast.start:
            raise ValueError("validation.end must not follow forecast.start")


def _parse_date(value: Any, field_name: str) -> pd.Timestamp:
    """Accept only calendar dates, never silently truncate a timestamp."""
    message = f"{field_name} must be a valid YYYY-MM-DD calendar date (no time-of-day)"
    if isinstance(value, datetime):
        raise ValueError(message)
    if isinstance(value, str):
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
            raise ValueError(message)
        try:
            value = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(message) from exc
    if not isinstance(value, date):
        raise ValueError(message)
    try:
        return pd.Timestamp(value, tz="UTC").as_unit("ns")
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"{field_name} is outside timestamp limits") from exc


def _parse_duration(value: Any, field_name: str, unit: str) -> pd.Timedelta:
    """Validate positive integer durations before timestamp arithmetic."""
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    try:
        return pd.Timedelta(value, unit=unit).as_unit("ns")
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"{field_name} is outside duration limits") from exc


def generate_backtest_windows(
    start_date: str | date,
    end_date: str | date,
    train_window_days: int,
    forecast_horizon_hours: int,
    *,
    validation_window_days: int,
) -> list[BacktestWindow]:
    """Return rolling candidate windows covering inclusive evaluation dates.

    All output intervals are UTC and half-open `[start, end)`. For forecast
    start `t`, validation ends at `t`, and training ends at validation start.
    History durations are fixed 24-hour days. Forecasts advance by the horizon
    in hours, clipping the final block at midnight after `end_date`.

    Calendar bounds accept strict YYYY-MM-DD strings or date objects, excluding
    datetimes. Durations must be positive integers; validation is explicit.
    Invalid inputs or unrepresentable nanosecond timestamp/duration arithmetic
    raise ValueError before any list is returned.

    These windows do not mandate retraining. Earlier evaluation observations
    may enter later history. The runner must separately validate publication
    timing and feature availability at forecast issuance.
    """
    start = _parse_date(start_date, "start_date")
    end = _parse_date(end_date, "end_date")
    if end < start:
        raise ValueError("end_date must not precede start_date")
    training = _parse_duration(train_window_days, "train_window_days", "D")
    validation = _parse_duration(validation_window_days, "validation_window_days", "D")
    horizon = _parse_duration(forecast_horizon_hours, "forecast_horizon_hours", "h")
    try:
        evaluation_end = end + pd.Timedelta(days=1)
    except (ValueError, OverflowError) as exc:
        raise ValueError(
            "end_date exclusive endpoint is outside timestamp limits"
        ) from exc
    # The first history start is the earliest endpoint in the whole schedule.
    # Validate it eagerly; all subsequent history endpoints move forward.
    try:
        validation_start = start - validation
    except (ValueError, OverflowError) as exc:
        raise ValueError(
            "start_date minus validation_window_days is outside timestamp limits"
        ) from exc
    try:
        train_start = validation_start - training
    except (ValueError, OverflowError) as exc:
        raise ValueError(
            "start_date minus validation_window_days and train_window_days "
            "is outside timestamp limits"
        ) from exc

    windows = []
    forecast_start = start
    while forecast_start < evaluation_end:
        # Integer nanoseconds avoid overflowing a Timedelta for very wide
        # evaluation ranges, or a Timestamp for an oversized final horizon.
        remaining_ns = evaluation_end.value - forecast_start.value
        forecast_end = (
            evaluation_end
            if horizon.value >= remaining_ns
            else forecast_start + horizon
        )
        windows.append(
            BacktestWindow(
                train=TimeWindow(train_start, validation_start),
                validation=TimeWindow(validation_start, forecast_start),
                forecast=TimeWindow(forecast_start, forecast_end),
            )
        )
        forecast_start = forecast_end
        if forecast_start < evaluation_end:
            validation_start = forecast_start - validation
            train_start = validation_start - training
    return windows


def generate_backtest_windows_from_config(
    config: Mapping[str, Any],
) -> list[BacktestWindow]:
    """Read five explicit settings from `config['backtest']`, without defaults."""
    if not isinstance(config, Mapping):
        raise ValueError("config must be a mapping containing 'backtest'")
    backtest = config.get("backtest")
    if not isinstance(backtest, Mapping):
        raise ValueError("config.backtest must be a mapping")
    missing = [key for key in REQUIRED_BACKTEST_KEYS if key not in backtest]
    if missing:
        raise ValueError(f"Missing required backtest setting(s): {missing}")
    # Use config field names in date errors, while retaining the direct API's
    # shorter start_date/end_date parameter names.
    start = _parse_date(
        backtest["evaluation_start_date"], "backtest.evaluation_start_date"
    )
    end = _parse_date(backtest["evaluation_end_date"], "backtest.evaluation_end_date")
    if end < start:
        raise ValueError(
            "backtest.evaluation_end_date must not precede evaluation_start_date"
        )
    return generate_backtest_windows(
        start.date(),
        end.date(),
        backtest["train_window_days"],
        backtest["forecast_horizon_hours"],
        validation_window_days=backtest["validation_window_days"],
    )
