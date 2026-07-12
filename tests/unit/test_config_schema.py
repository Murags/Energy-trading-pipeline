"""Unit tests for experiment config schema validation."""

import pytest

from energy_trading_pipeline.config.schema import (
    ConfigValidationError,
    validate_experiment_config,
)


def _valid_config() -> dict:
    return {
        "data": {},
        "dates": {"start_date": "2023-01-01", "end_date": "2023-06-01"},
        "features": {},
        "model": {},
        "backtest": {},
        "retraining": {},
        "evaluation": {},
        "artifacts": {},
    }


def test_validate_experiment_config_accepts_valid_config():
    validate_experiment_config(_valid_config())


def test_validate_experiment_config_raises_on_missing_required_section():
    config = _valid_config()
    del config["retraining"]

    with pytest.raises(ConfigValidationError, match="retraining"):
        validate_experiment_config(config)


def test_validate_experiment_config_raises_on_multiple_missing_sections():
    config = _valid_config()
    del config["retraining"]
    del config["evaluation"]

    with pytest.raises(ConfigValidationError, match="retraining.*evaluation"):
        validate_experiment_config(config)


def test_validate_experiment_config_raises_when_not_a_mapping():
    with pytest.raises(ConfigValidationError):
        validate_experiment_config([])


def test_validate_experiment_config_raises_on_missing_date_keys():
    config = _valid_config()
    del config["dates"]["end_date"]

    with pytest.raises(ConfigValidationError, match="end_date"):
        validate_experiment_config(config)


def test_validate_experiment_config_raises_on_invalid_date_order():
    config = _valid_config()
    config["dates"] = {"start_date": "2023-06-01", "end_date": "2023-01-01"}

    with pytest.raises(ConfigValidationError, match="start_date"):
        validate_experiment_config(config)


def test_validate_experiment_config_raises_on_equal_start_and_end_date():
    config = _valid_config()
    config["dates"] = {"start_date": "2023-01-01", "end_date": "2023-01-01"}

    with pytest.raises(ConfigValidationError):
        validate_experiment_config(config)


def test_validate_experiment_config_raises_on_unparseable_date():
    config = _valid_config()
    config["dates"] = {"start_date": "not-a-date", "end_date": "2023-06-01"}

    with pytest.raises(ConfigValidationError, match="not-a-date"):
        validate_experiment_config(config)
