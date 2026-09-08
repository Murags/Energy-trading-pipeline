"""Unit tests for YAML config loading and merging."""

from pathlib import Path

import pytest

from energy_trading_pipeline.config.loader import load_config, load_yaml_file
from energy_trading_pipeline.config.schema import ConfigValidationError

VALID_EXPERIMENT_CONFIG = """
data:
  price_de_path: data/raw/entsoe/prices/de.csv
  price_fr_path: data/raw/entsoe/prices/fr.csv
dates:
  start_date: "2023-01-01"
  end_date: "2023-06-01"
features:
  lag_hours: [1, 24]
model:
  type: xgboost
backtest:
  train_window_days: 90
retraining:
  strategy: fixed_schedule
  rolling_rmse_window_days: 7
evaluation:
  metrics: [rmse, mae]
artifacts:
  run_prefix: run
"""

LOCAL_PATHS_CONFIG = """
data_raw_dir: data/raw
models_dir: models
"""

MODEL_PARAMS_CONFIG = """
n_estimators: 200
max_depth: 5
"""

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _write(path: Path, content: str) -> Path:
    path.write_text(content)
    return path


def test_load_config_with_valid_experiment_config_returns_runtime_config(tmp_path):
    experiment_path = _write(tmp_path / "experiment.yaml", VALID_EXPERIMENT_CONFIG)

    config = load_config(experiment_path)

    assert config["retraining"]["strategy"] == "fixed_schedule"
    assert config["dates"]["start_date"] == "2023-01-01"
    assert "paths" not in config


def test_load_config_merges_local_paths_and_model_params(tmp_path):
    experiment_path = _write(tmp_path / "experiment.yaml", VALID_EXPERIMENT_CONFIG)
    local_paths_path = _write(tmp_path / "local_paths.yaml", LOCAL_PATHS_CONFIG)
    model_params_path = _write(tmp_path / "model_params.yaml", MODEL_PARAMS_CONFIG)

    config = load_config(
        experiment_path,
        local_paths_config_path=local_paths_path,
        model_params_config_path=model_params_path,
        base_dir=tmp_path,
    )

    assert config["paths"]["data_raw_dir"] == (tmp_path / "data" / "raw").resolve()
    assert config["paths"]["models_dir"] == (tmp_path / "models").resolve()
    assert config["model"]["type"] == "xgboost"
    assert config["model"]["params"] == {"n_estimators": 200, "max_depth": 5}


def test_load_config_raises_clear_error_on_missing_required_section(tmp_path):
    incomplete_config = VALID_EXPERIMENT_CONFIG.replace(
        "retraining:\n  strategy: fixed_schedule\n  rolling_rmse_window_days: 7\n",
        "",
    )
    experiment_path = _write(tmp_path / "experiment.yaml", incomplete_config)

    with pytest.raises(ConfigValidationError, match="retraining"):
        load_config(experiment_path)


def test_load_config_raises_on_invalid_date_order(tmp_path):
    bad_config = VALID_EXPERIMENT_CONFIG.replace(
        'start_date: "2023-01-01"\n  end_date: "2023-06-01"',
        'start_date: "2023-06-01"\n  end_date: "2023-01-01"',
    )
    experiment_path = _write(tmp_path / "experiment.yaml", bad_config)

    with pytest.raises(ConfigValidationError, match="start_date"):
        load_config(experiment_path)


def test_load_config_raises_clear_error_when_model_section_is_not_a_mapping(
    tmp_path,
):
    experiment_path = _write(
        tmp_path / "experiment.yaml",
        VALID_EXPERIMENT_CONFIG.replace("model:\n  type: xgboost", "model: xgboost"),
    )
    model_params_path = _write(tmp_path / "model_params.yaml", MODEL_PARAMS_CONFIG)

    with pytest.raises(ConfigValidationError, match="model"):
        load_config(experiment_path, model_params_config_path=model_params_path)


def test_load_config_raises_file_not_found_for_missing_experiment_config(tmp_path):
    missing_path = tmp_path / "does_not_exist.yaml"

    with pytest.raises(FileNotFoundError, match="not found"):
        load_config(missing_path)


def test_load_yaml_file_reads_mapping(tmp_path):
    path = _write(tmp_path / "sample.yaml", "key: value\n")

    assert load_yaml_file(path) == {"key": "value"}


def test_load_yaml_file_raises_clear_error_when_file_missing(tmp_path):
    missing_path = tmp_path / "does_not_exist.yaml"

    with pytest.raises(FileNotFoundError, match="not found"):
        load_yaml_file(missing_path)


def test_load_yaml_file_raises_when_top_level_is_not_a_mapping(tmp_path):
    path = _write(tmp_path / "list.yaml", "- a\n- b\n")

    with pytest.raises(ValueError, match="mapping"):
        load_yaml_file(path)


def test_load_yaml_file_returns_empty_dict_for_empty_file(tmp_path):
    path = _write(tmp_path / "empty.yaml", "")

    assert load_yaml_file(path) == {}


def test_repository_sample_configs_load_with_debug_safe_defaults():
    config = load_config(
        PROJECT_ROOT / "configs" / "experiment.yaml",
        local_paths_config_path=PROJECT_ROOT / "configs" / "local_paths.yaml",
        model_params_config_path=PROJECT_ROOT / "configs" / "model_params.yaml",
        base_dir=PROJECT_ROOT,
    )
    fixture_config = load_config(
        PROJECT_ROOT / "tests" / "fixtures" / "sample_config.yaml"
    )

    assert config["retraining"]["strategy"] == "fixed_schedule"
    assert config["retraining"]["fixed_schedule_interval_days"] == 7
    assert config["retraining"]["rolling_rmse_window_days"] == 7
    assert config["retraining"]["rolling_rmse_threshold"] == 10.0
    assert config["paths"]["price_de_csv_path"] == (
        PROJECT_ROOT / "data" / "raw" / "entsoe" / "prices" / "price_de.csv"
    ).resolve()
    assert config["paths"]["processed_data_parquet_path"] == (
        PROJECT_ROOT / "data" / "processed" / "aligned_hourly" / "prices.parquet"
    ).resolve()
    assert config["model"]["params"]["n_estimators"] == 100
    assert fixture_config["dates"] == {
        "start_date": "2023-01-01",
        "end_date": "2023-01-08",
        "train_start_date": "2023-01-02",
        "train_end_date": "2023-01-06",
        "validation_start_date": "2023-01-07",
        "validation_end_date": "2023-01-08",
    }
    assert fixture_config["retraining"] == {
        "strategy": "fixed_schedule",
        "fixed_schedule_interval_days": 7,
        "rolling_rmse_window_days": 7,
        "rolling_rmse_threshold": 10.0,
    }
