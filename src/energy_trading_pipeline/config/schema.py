"""Configuration schema validation for the experiment runtime config."""

from datetime import date, datetime
from typing import Any

REQUIRED_TOP_LEVEL_SECTIONS = (
    "data",
    "dates",
    "features",
    "model",
    "backtest",
    "retraining",
    "evaluation",
    "artifacts",
)

REQUIRED_DATE_KEYS = ("start_date", "end_date")


class ConfigValidationError(ValueError):
    """Raised when an experiment configuration fails validation."""


def validate_experiment_config(config: dict[str, Any]) -> None:
    """
    Validate the experiment config against required sections and date ordering.

    Raises:
        ConfigValidationError: If required top-level sections or date keys are
            missing, or if `dates.start_date` is not before `dates.end_date`.
    """
    if not isinstance(config, dict):
        raise ConfigValidationError(
            "Experiment config must be a mapping of top-level sections."
        )

    missing_sections = [
        section for section in REQUIRED_TOP_LEVEL_SECTIONS if section not in config
    ]
    if missing_sections:
        raise ConfigValidationError(
            f"Missing required config section(s): {', '.join(missing_sections)}"
        )

    _validate_dates_section(config["dates"])


def _validate_dates_section(dates_config: Any) -> None:
    if not isinstance(dates_config, dict):
        raise ConfigValidationError("Config section 'dates' must be a mapping.")

    missing_keys = [key for key in REQUIRED_DATE_KEYS if key not in dates_config]
    if missing_keys:
        raise ConfigValidationError(
            f"Missing required date key(s) in 'dates' section: {', '.join(missing_keys)}"
        )

    start_date = _parse_date(dates_config["start_date"], "dates.start_date")
    end_date = _parse_date(dates_config["end_date"], "dates.end_date")

    if start_date >= end_date:
        raise ConfigValidationError(
            "dates.start_date "
            f"({dates_config['start_date']}) must be before dates.end_date "
            f"({dates_config['end_date']})"
        )


def _parse_date(value: Any, field_name: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError as exc:
        raise ConfigValidationError(
            f"Invalid {field_name}: {value!r} is not a valid YYYY-MM-DD date"
        ) from exc
