"""Baseline training CLI runs only on local, small feature artifacts."""

from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest
import yaml

from energy_trading_pipeline.cli import main
from energy_trading_pipeline.models.xgboost_model import XGBoostSpreadModel

FIXTURE_CONFIG = Path(__file__).resolve().parents[1] / "fixtures/sample_config.yaml"


@pytest.fixture
def training_files(tmp_path):
    """Write a two-day feature fixture and explicit configs in a temp directory."""
    config = yaml.safe_load(FIXTURE_CONFIG.read_text())
    config["dates"].update(
        train_start_date="2023-01-01",
        train_end_date="2023-01-01",
        validation_start_date="2023-01-02",
        validation_end_date="2023-01-02",
    )
    config_path = tmp_path / "experiment.yaml"
    config_path.write_text(yaml.safe_dump(config))
    features = pd.DataFrame(
        {
            "timestamp": pd.date_range("2023-01-01", periods=48, freq="h", tz="UTC"),
            "spread": np.arange(48, dtype=float),
            "spread_lag_24": np.arange(48, dtype=float) - 24,
            "hour": list(range(24)) * 2,
        }
    )
    feature_path = tmp_path / "features.parquet"
    features.to_parquet(feature_path, index=False)
    paths = {
        "feature_data_parquet_path": str(feature_path),
        "models_dir": str(tmp_path / "models"),
        "logs_dir": str(tmp_path / "logs"),
    }
    paths_path = tmp_path / "paths.yaml"
    paths_path.write_text(yaml.safe_dump(paths))
    params = {"n_estimators": 3, "max_depth": 1, "random_state": 7, "n_jobs": 1}
    params_path = tmp_path / "params.yaml"
    params_path.write_text(yaml.safe_dump(params))
    return config_path, paths_path, params_path, feature_path, features, params


def training_args(files):
    """Use the public command and explicit companion configuration flags."""
    return [
        "train",
        "--config",
        str(files[0]),
        "--paths-config",
        str(files[1]),
        "--model-params-config",
        str(files[2]),
    ]


def test_training_cli_persists_configured_model_and_held_out_metrics(
    tmp_path, training_files
):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_trading_pipeline.cli",
            *training_args(training_files),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Run ID:" in result.stdout
    assert "Model version:" in result.stdout
    assert "Run metadata written to:" in result.stdout
    model_path = next((tmp_path / "models/artifacts").glob("model_*/model.json"))
    model = XGBoostSpreadModel.load(model_path)
    assert model.params == training_files[5]
    features = training_files[4]
    predictors = ["spread_lag_24", "hour"]
    expected = XGBoostSpreadModel(training_files[5]).fit(
        features.iloc[:24][predictors], features.iloc[:24]["spread"]
    )
    predictions = model.predict(features.iloc[24:])
    np.testing.assert_array_equal(predictions, expected.predict(features.iloc[24:]))
    errors = features.iloc[24:]["spread"].to_numpy() - predictions
    metadata = yaml.safe_load(model_path.with_name("metadata.yaml").read_text())
    assert metadata["validation_metrics"] == pytest.approx(
        {"rmse": float(np.sqrt(np.mean(errors**2))), "mae": float(np.mean(abs(errors)))}
    )
    run_path = next((tmp_path / "logs/runs").glob("run_*/run_metadata.yaml"))
    run = yaml.safe_load(run_path.read_text())
    assert run["run_id"] == run_path.parent.name
    assert run["config_file_path"] == str(training_files[0])
    assert run["model_version"] == model_path.parent.name
    assert run["feature_columns"] == predictors
    assert run["target_column"] == "spread"
    assert run["model_parameters"] == training_files[5]
    assert run["metrics"] == metadata["validation_metrics"]
    assert run["training_windows"][0]["train_rows"] == 24
    assert run["training_windows"][0]["validation_rows"] == 24
    assert run["evaluation_window"]["start"] == "2023-01-02T00:00:00+00:00"
    assert run["artifact_paths"]["model"] == str(model_path)
    assert run["config"]["paths"]["feature_data_parquet_path"] == str(training_files[3])


def test_missing_feature_dataset_fails_clearly(tmp_path, training_files, capsys):
    training_files[3].unlink()
    assert main(training_args(training_files)) == 1
    assert "Feature dataset not found" in capsys.readouterr().err
    assert not (tmp_path / "models").exists()
    assert not (tmp_path / "logs").exists()


def test_overlapping_windows_fail_without_artifacts(tmp_path, training_files, capsys):
    config = yaml.safe_load(training_files[0].read_text())
    config["dates"]["train_end_date"] = "2023-01-02"
    training_files[0].write_text(yaml.safe_dump(config))
    assert main(training_args(training_files)) == 1
    assert "overlap" in capsys.readouterr().err
    assert not (tmp_path / "models").exists()


def test_training_requires_configured_paths(training_files, capsys):
    assert main(["train", "--config", str(training_files[0])]) == 1
    assert "paths" in capsys.readouterr().err


def test_training_requires_explicit_model_parameters(training_files, capsys):
    assert main(training_args(training_files)[:-2]) == 1
    assert "model.params" in capsys.readouterr().err


def test_training_rejects_contemporaneous_prices(tmp_path, training_files, capsys):
    features = training_files[4].assign(price_de=50.0, price_fr=30.0)
    features.to_parquet(training_files[3], index=False)
    assert main(training_args(training_files)) == 1
    assert "contemporaneous" in capsys.readouterr().err
    assert not (tmp_path / "models").exists()


@pytest.mark.parametrize("strategy", [None, "unknown"])
def test_invalid_strategy_fails_before_artifact_writes(
    tmp_path, training_files, capsys, strategy
):
    config = yaml.safe_load(training_files[0].read_text())
    config["retraining"] = {} if strategy is None else {"strategy": strategy}
    training_files[0].write_text(yaml.safe_dump(config))
    assert main(training_args(training_files)) == 1
    assert "retraining.strategy" in capsys.readouterr().err
    assert not (tmp_path / "models").exists()
    assert not (tmp_path / "logs").exists()


def test_training_accepts_inline_paths_and_parameters(tmp_path, training_files):
    config = yaml.safe_load(training_files[0].read_text())
    config["paths"] = yaml.safe_load(training_files[1].read_text())
    config["model"]["params"] = training_files[5]
    training_files[0].write_text(yaml.safe_dump(config))
    assert main(["train", "--config", str(training_files[0])]) == 0
    model_path = next((tmp_path / "models/artifacts").glob("model_*/model.json"))
    assert XGBoostSpreadModel.load(model_path).params == training_files[5]
