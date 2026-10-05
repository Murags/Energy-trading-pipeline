"""Fixture-only CLI backtests, artifact provenance, and failure reporting."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest
import yaml

from energy_trading_pipeline.backtesting import backtest_runner
from energy_trading_pipeline.backtesting.forecast_log import FORECAST_LOG_COLUMNS
from energy_trading_pipeline.cli import main
from energy_trading_pipeline.models.xgboost_model import XGBoostSpreadModel

FIXTURE_CONFIG = Path(__file__).resolve().parents[1] / "fixtures/sample_config.yaml"


@pytest.fixture
def backtest_files(tmp_path):
    """Persist four synthetic days with calendar predictors known before issuance."""
    timestamps = pd.date_range("2024-01-01", periods=96, freq="h", tz="UTC")
    frame = pd.DataFrame(
        {
            "timestamp": timestamps,
            "spread": np.sin(np.arange(96)),
            "hour": timestamps.hour,
            "feature_available_at": timestamps - pd.Timedelta(days=1),
            "actual_available_at": timestamps + pd.Timedelta(hours=2),
        }
    )
    feature_path = tmp_path / "features.parquet"
    frame.sample(frac=1, random_state=7).to_parquet(feature_path, index=False)
    config = yaml.safe_load(FIXTURE_CONFIG.read_text())
    config["dates"] = {"start_date": "2024-01-01", "end_date": "2024-01-04"}
    config["backtest"] = {
        "evaluation_start_date": "2024-01-03",
        "evaluation_end_date": "2024-01-04",
        "train_window_days": 1,
        "validation_window_days": 1,
        "forecast_horizon_hours": 24,
        "feature_columns": ["hour"],
    }
    config["model"]["params"] = {
        "n_estimators": 3,
        "max_depth": 2,
        "n_jobs": 1,
        "random_state": 7,
    }
    config["retraining"]["strategy"] = "no_retraining"
    config["paths"] = {
        "feature_data_parquet_path": str(feature_path),
        "models_dir": str(tmp_path / "models"),
        "logs_dir": str(tmp_path / "logs"),
    }
    config_path = tmp_path / "experiment.yaml"
    config_path.write_text(yaml.safe_dump(config))
    return config_path, config, frame


@pytest.mark.parametrize("horizon", [24, 7])
def test_backtest_cli_writes_traceable_outputs_without_credentials(
    tmp_path, backtest_files, horizon
):
    config_path, config, frame = backtest_files
    config["backtest"]["forecast_horizon_hours"] = horizon
    config_path.write_text(yaml.safe_dump(config))
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("AWS_", "ENTSOE_", "ENTSO_E_"))
    }
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "energy_trading_pipeline.cli",
            "backtest",
            "--config",
            str(config_path),
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    (run_dir,) = (tmp_path / "logs/runs").glob("run_*")
    assert re.fullmatch(r"run_\d{8}_\d{6}", run_dir.name)
    assert f"Run ID: {run_dir.name}" in result.stdout
    assert "Forecast log:" in result.stdout
    assert "Backtest log:" in result.stdout
    assert "Run metadata written to:" in result.stdout
    forecasts = pd.read_parquet(run_dir / "forecasts.parquet")
    assert list(forecasts.columns) == list(FORECAST_LOG_COLUMNS)
    assert len(forecasts) == 48
    assert forecasts["timestamp"].tolist() == frame["timestamp"].iloc[48:].tolist()
    assert forecasts["forecast_timestamp"].nunique() == (48 + horizon - 1) // horizon
    np.testing.assert_allclose(forecasts["actual"], frame["spread"].iloc[48:])
    np.testing.assert_allclose(
        forecasts["error"], forecasts["actual"] - forecasts["prediction"]
    )
    run = yaml.safe_load((run_dir / "run_metadata.yaml").read_text())
    assert run["run_id"] == run_dir.name
    assert run["config_file_path"] == str(config_path)
    assert run["config"] == config
    assert run["strategy"] == "no_retraining"
    assert run["feature_columns"] == ["hour"]
    assert run["target_column"] == "spread"
    assert run["model_parameters"] == config["model"]["params"]
    assert run["data_date_range"] == {
        "start": "2024-01-01T00:00:00+00:00",
        "end": "2024-01-04T23:00:00+00:00",
    }
    assert run["training_windows"] == [
        {"start": "2024-01-01T00:00:00+00:00", "end": "2024-01-02T00:00:00+00:00"}
    ]
    assert run["evaluation_window"] == {
        "start": "2024-01-03T00:00:00+00:00",
        "end": "2024-01-05T00:00:00+00:00",
    }
    assert run["window_convention"] == "[start, end)"
    assert run["metrics"] == {}  # Aggregate evaluation is a later story.
    assert re.fullmatch(r"model_\d{8}_\d{6}", run["model_version"])
    assert forecasts["model_version"].unique().tolist() == [run["model_version"]]
    assert forecasts["strategy"].unique().tolist() == ["no_retraining"]
    for artifact in run["artifact_paths"].values():
        assert Path(artifact).is_file()
    model_path = Path(run["artifact_paths"]["model"])
    assert model_path.parent == tmp_path / "models/artifacts" / run["model_version"]
    model = XGBoostSpreadModel.load(model_path)
    assert model.params == config["model"]["params"]
    expected = XGBoostSpreadModel(model.params).fit(
        frame.iloc[:24][["hour"]], frame.iloc[:24]["spread"]
    )
    np.testing.assert_array_equal(
        forecasts["prediction"], expected.predict(frame.iloc[48:])
    )
    events = [
        json.loads(line)
        for line in (run_dir / "backtest_log.jsonl").read_text().splitlines()
    ]
    assert [event["event"] for event in events] == [
        "backtest_started", "backtest_completed"
    ]
    assert events[-1]["forecast_rows"] == 48
    for event in events:
        assert event["run_id"] == run_dir.name
        assert event["model_version"] == run["model_version"]
        assert event["strategy"] == "no_retraining"
        assert event["stage"] == "backtesting"
        assert event["evaluation_window"] == run["evaluation_window"]


def test_backtest_cli_accepts_companion_configs(tmp_path, backtest_files):
    config_path, config, _ = backtest_files
    paths_path = tmp_path / "paths.yaml"
    paths_path.write_text(yaml.safe_dump(config.pop("paths")))
    params_path = tmp_path / "params.yaml"
    params_path.write_text(yaml.safe_dump(config["model"].pop("params")))
    config_path.write_text(yaml.safe_dump(config))
    assert main(
        [
            "backtest",
            "--config",
            str(config_path),
            "--paths-config",
            str(paths_path),
            "--model-params-config",
            str(params_path),
        ]
    ) == 0
    run_path = next((tmp_path / "logs/runs").glob("run_*/run_metadata.yaml"))
    run = yaml.safe_load(run_path.read_text())
    assert run["config"]["paths"] == yaml.safe_load(paths_path.read_text())
    assert run["model_parameters"] == yaml.safe_load(params_path.read_text())


@pytest.mark.parametrize(
    ("fault", "message"),
    [
        ("missing_file", "Feature dataset not found"),
        ("paths", "paths"),
        ("params", "model.params"),
        ("feature_columns", "feature_columns"),
        ("strategy", "no_retraining"),
        ("window", "evaluation_end_date"),
    ],
)
def test_invalid_backtest_config_fails_clearly(
    tmp_path, backtest_files, capsys, fault, message
):
    config_path, config, _ = backtest_files
    if fault == "missing_file":
        Path(config["paths"]["feature_data_parquet_path"]).unlink()
    elif fault == "paths":
        del config["paths"]
    elif fault == "params":
        del config["model"]["params"]
    elif fault == "feature_columns":
        del config["backtest"]["feature_columns"]
    elif fault == "strategy":
        config["retraining"]["strategy"] = "fixed_schedule"
    else:
        config["backtest"]["evaluation_end_date"] = "2024-01-02"
    config_path.write_text(yaml.safe_dump(config))
    assert main(["backtest", "--config", str(config_path)]) == 1
    assert message in capsys.readouterr().err
    assert not (tmp_path / "logs").exists()
    assert not (tmp_path / "models").exists()


@pytest.mark.parametrize("fault", ["missing_availability", "late_feature"])
def test_backtest_cli_preserves_availability_checks(
    tmp_path, backtest_files, capsys, fault
):
    config_path, config, frame = backtest_files
    if fault == "missing_availability":
        frame = frame.drop(columns="feature_available_at")
        message = "feature_available_at"
    else:
        frame.loc[49, "feature_available_at"] = frame.loc[49, "timestamp"]
        message = "unavailable at issuance"
    frame.to_parquet(config["paths"]["feature_data_parquet_path"], index=False)
    assert main(["backtest", "--config", str(config_path)]) == 1
    assert message in capsys.readouterr().err
    (run_dir,) = (tmp_path / "logs/runs").glob("run_*")
    assert not (run_dir / "run_metadata.yaml").exists()
    assert not (run_dir / "forecasts.parquet").exists()
    assert not list((tmp_path / "models").rglob("model.json"))
    events = [
        json.loads(line)
        for line in (run_dir / "backtest_log.jsonl").read_text().splitlines()
    ]
    assert events[-1]["event"] == "backtest_failed"
    assert message in events[-1]["error"]


@pytest.mark.parametrize("collision", ["run", "model"])
def test_backtest_cli_never_overwrites_existing_artifacts(
    tmp_path, backtest_files, monkeypatch, capsys, collision
):
    monkeypatch.setattr(
        backtest_runner, "generate_run_id", lambda: "run_20240101_000000"
    )
    directory = (
        tmp_path / "logs/runs/run_20240101_000000"
        if collision == "run"
        else tmp_path / "models/artifacts/model_20240101_000000"
    )
    directory.mkdir(parents=True)
    existing = directory / ("run_metadata.yaml" if collision == "run" else "model.json")
    existing.write_text("existing artifact")
    assert main(["backtest", "--config", str(backtest_files[0])]) == 1
    assert "Error:" in capsys.readouterr().err
    assert existing.read_text() == "existing artifact"
