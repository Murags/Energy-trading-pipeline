"""Dashboard exports from small saved research artifacts, without pipeline work."""

from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest
import yaml

from energy_trading_pipeline.backtesting.forecast_log import write_forecast_log
from energy_trading_pipeline import cli
from energy_trading_pipeline.evaluation import exports
from energy_trading_pipeline.evaluation.strategy_comparison import (
    write_strategy_comparison,
)
from energy_trading_pipeline.retraining.events import (
    RETRAINING_EVENT_COLUMNS,
    write_retraining_events,
)


START = pd.Timestamp("2024-01-01T00:00:00Z")
END = START + pd.Timedelta(hours=4)
RUN_ID = "run_20261005_120000"
SCHEMAS = {
    "forecasts": [
        "timestamp", "prediction", "actual", "strategy", "model_version",
        "rolling_rmse",
    ],
    "metrics": [
        "run_id", "evaluation_start", "evaluation_end", "strategy", "rmse",
        "mae", "retraining_count", "retraining_frequency",
    ],
    "retraining_events": [
        "timestamp", "strategy", "trigger_reason", "threshold", "rolling_rmse",
        "model_version",
    ],
    "model_versions": ["model_version", "model_type"],
}


@pytest.fixture
def saved_results(tmp_path):
    timestamps = pd.date_range(START, periods=4, freq="h")
    strategies = ["no_retraining", "fixed_schedule", "performance_triggered"]
    forecasts = pd.DataFrame(
        [
            {
                "timestamp": timestamp,
                "forecast_timestamp": timestamp - pd.Timedelta(days=1),
                "prediction": float(position - 2),
                "actual": np.nan if position == 1 else float(position - 1),
                "strategy": strategy,
                "model_version": "fixture_model",
            }
            for strategy in strategies
            for position, timestamp in enumerate(timestamps)
        ]
    )
    events = pd.DataFrame(
        [{
            "timestamp": timestamps[2], "strategy": "fixed_schedule",
            "trigger_reason": "scheduled", "threshold": np.nan,
            "rolling_rmse": np.nan,
            "training_window_start": START - pd.Timedelta(days=10),
            "training_window_end": timestamps[2],
            "model_version": "event_model",
        }],
        columns=list(RETRAINING_EVENT_COLUMNS),
    )
    inputs_dir = tmp_path / "logs" / "runs" / RUN_ID
    paths = {
        "forecasts": write_forecast_log(
            forecasts, inputs_dir / "forecasts.parquet"
        ),
        "retraining_events": write_retraining_events(
            events, inputs_dir / "retraining_events.parquet"
        ),
        "metrics": write_strategy_comparison(
            forecasts, events, run_id=RUN_ID,
            evaluation_start=START, evaluation_end=END,
            tables_dir=tmp_path / "reports" / "tables",
        )["parquet"],
    }
    monitoring = forecasts[["timestamp", "strategy"]].copy()
    monitoring["rolling_rmse"] = [np.nan, np.nan, 1.0, 2.0] * 3
    paths["monitoring"] = inputs_dir / "rolling_rmse.parquet"
    monitoring.to_parquet(paths["monitoring"], index=False)
    index = {
        "models": {
            version: {
                "model_version": version, "model_type": "xgboost",
                "created_at": "2024-01-01T00:00:00+01:00",
                "artifact_paths": {"model": "/private/not_exported.json"},
                "feature_columns": ["spread_lag_24"],
            }
            for version in ["fixture_model", "event_model", "unrelated_model"]
        }
    }
    paths["model_index"] = inputs_dir / "models_index.yaml"
    paths["model_index"].write_text(yaml.safe_dump(index), encoding="utf-8")
    return paths


def load_results(paths):
    return {
        name: pd.read_parquet(path)
        for name, path in paths.items()
        if name != "model_index"
    } | {"model_index": yaml.safe_load(paths["model_index"].read_text())}


@pytest.mark.parametrize("scenario", ["normal", "no_events", "no_scores", "empty"])
def test_saved_results_export_four_minimal_parquet_schemas(
    tmp_path, saved_results, scenario
):
    data = load_results(saved_results)
    if scenario in {"no_events", "empty"}:
        data["retraining_events"] = data["retraining_events"].iloc[:0]
    if scenario == "no_scores":
        data["forecasts"]["actual"] = np.nan
        data["metrics"][["rmse", "mae"]] = np.nan
    if scenario == "empty":
        for name in ["forecasts", "metrics", "monitoring"]:
            data[name] = data[name].iloc[:0]
    originals = {
        name: frame.copy(deep=True)
        for name, frame in data.items() if isinstance(frame, pd.DataFrame)
    }
    input_bytes = {name: path.read_bytes() for name, path in saved_results.items()}
    output_dir = tmp_path / "reports" / "dashboard_exports"
    paths = exports.write_dashboard_exports(**data, exports_dir=output_dir)
    assert paths == {name: output_dir / f"{name}.parquet" for name in SCHEMAS}
    assert set(output_dir.iterdir()) == set(paths.values())
    for name, columns in SCHEMAS.items():
        frame = pd.read_parquet(paths[name])
        assert list(frame.columns) == columns
        if scenario == "empty":
            assert frame.empty
        for column in frame.select_dtypes(include="datetimetz"):
            assert str(frame[column].dtype) == "datetime64[ns, UTC]"
    forecast = pd.read_parquet(paths["forecasts"])
    assert len(forecast) == len(data["forecasts"])
    assert forecast["timestamp"].is_monotonic_increasing
    assert forecast["actual"].isna().sum() == data["forecasts"]["actual"].isna().sum()
    assert forecast["rolling_rmse"].tolist() == pytest.approx(
        data["monitoring"].sort_values("timestamp", kind="stable")
        ["rolling_rmse"].tolist(), nan_ok=True,
    )
    metrics = pd.read_parquet(paths["metrics"])
    pd.testing.assert_frame_equal(
        metrics, data["metrics"].sort_values("strategy").reset_index(drop=True)
    )
    models = pd.read_parquet(paths["model_versions"])
    expected = set(data["forecasts"]["model_version"]) | set(
        data["retraining_events"]["model_version"]
    )
    assert set(models["model_version"]) == expected
    assert set(models["model_type"]) <= {"xgboost"}
    assert "unrelated_model" not in set(models["model_version"])
    for name, original in originals.items():
        pd.testing.assert_frame_equal(data[name], original)
    for name, path in saved_results.items():
        assert path.read_bytes() == input_bytes[name]
    exports.write_dashboard_exports(**data, exports_dir=output_dir)
    assert len(list(output_dir.iterdir())) == 4


@pytest.mark.parametrize(
    "invalid", [
        "forecasts", "metrics", "events", "model_index", "unknown_version",
        "duplicate_metric", "mixed_runs", "mixed_windows", "negative_rmse",
        "fractional_count", "duplicate_forecast", "naive_monitoring",
        "duplicate_monitoring", "unknown_monitoring", "negative_rolling",
    ],
)
def test_invalid_saved_results_fail_before_creating_exports(
    tmp_path, saved_results, invalid
):
    data = load_results(saved_results)
    if invalid == "forecasts":
        data["forecasts"] = data["forecasts"].drop(columns="prediction")
    elif invalid == "metrics":
        data["metrics"] = data["metrics"].drop(columns="rmse")
    elif invalid == "events":
        data["retraining_events"] = data["retraining_events"].drop(
            columns="model_version"
        )
    elif invalid == "model_index":
        data["model_index"] = {"models": []}
    elif invalid == "unknown_version":
        del data["model_index"]["models"]["fixture_model"]
    elif invalid == "duplicate_metric":
        data["metrics"] = pd.concat([data["metrics"], data["metrics"].iloc[:1]])
    elif invalid == "mixed_runs":
        data["metrics"].loc[0, "run_id"] = "other_run"
    elif invalid == "mixed_windows":
        data["metrics"].loc[0, "evaluation_end"] = END + pd.Timedelta(hours=1)
    elif invalid == "negative_rmse":
        data["metrics"].loc[0, "rmse"] = -1.0
    elif invalid == "fractional_count":
        data["metrics"]["retraining_count"] = 0.5
    elif invalid == "duplicate_forecast":
        data["forecasts"] = pd.concat(
            [data["forecasts"], data["forecasts"].iloc[:1]]
        )
    elif invalid == "naive_monitoring":
        data["monitoring"]["timestamp"] = (
            data["monitoring"]["timestamp"].dt.tz_localize(None)
        )
    elif invalid == "duplicate_monitoring":
        data["monitoring"] = pd.concat(
            [data["monitoring"], data["monitoring"].iloc[:1]]
        )
    elif invalid == "unknown_monitoring":
        data["monitoring"].loc[0, "strategy"] = "unknown"
    else:
        data["monitoring"].loc[0, "rolling_rmse"] = -1.0
    output_dir = tmp_path / "reports" / "dashboard_exports"
    with pytest.raises(ValueError):
        exports.write_dashboard_exports(**data, exports_dir=output_dir)
    assert not output_dir.exists()


@pytest.fixture
def export_command(tmp_path, saved_results):
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "sample_config.yaml"
    config = yaml.safe_load(fixture.read_text())
    config["paths"] = {"reports_dir": str(tmp_path / "reports")}
    config_path = tmp_path / "experiment.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    args = ["export-dashboard", "--config", str(config_path)]
    for option, name in [
        ("--forecasts", "forecasts"), ("--metrics", "metrics"),
        ("--retraining-events", "retraining_events"),
        ("--rolling-rmse", "monitoring"), ("--model-index", "model_index"),
    ]:
        args.extend([option, str(saved_results[name])])
    return args, config_path, config


@pytest.mark.parametrize("mode", ["registry", "run_metadata", "no_monitoring"])
def test_export_command_is_independent_of_pipeline_stages(
    tmp_path, export_command, saved_results, monkeypatch, capsys, mode
):
    args, config_path, config = export_command

    def forbidden(*args, **kwargs):
        pytest.fail("Dashboard export must not invoke any pipeline execution")

    for name in ["train_baseline", "run_configured_backtest", "create_run_directory"]:
        monkeypatch.setattr(cli, name, forbidden)
    monkeypatch.setattr(cli, "generate_run_id", forbidden)
    if mode == "no_monitoring":
        position = args.index("--rolling-rmse")
        del args[position:position + 2]
    elif mode == "run_metadata":
        position = args.index("--model-index")
        del args[position:position + 2]
        for version in ["fixture_model", "event_model"]:
            metadata_path = tmp_path / f"{version}_run_metadata.yaml"
            metadata_path.write_text(yaml.safe_dump({
                "model_version": version, "run_id": RUN_ID,
                "config": {"model": {"type": "xgboost"}},
                "artifact_paths": {"model": "/not_loaded/model.json"},
            }), encoding="utf-8")
            args.extend(["--run-metadata", str(metadata_path)])
    original = {name: path.read_bytes() for name, path in saved_results.items()}
    assert cli.main(args) == 0
    output_dir = tmp_path / "reports" / "dashboard_exports"
    for name, schema in SCHEMAS.items():
        output = output_dir / f"{name}.parquet"
        assert list(pd.read_parquet(output).columns) == schema
    assert "Dashboard exports written to:" in capsys.readouterr().out
    for name, path in saved_results.items():
        assert path.read_bytes() == original[name]
    assert not (tmp_path / "models").exists()
    if mode == "no_monitoring":
        frame = pd.read_parquet(output_dir / "forecasts.parquet")
        assert frame["rolling_rmse"].isna().all()


def test_export_command_accepts_companion_paths_and_runs_as_a_module(
    tmp_path, export_command
):
    args, config_path, config = export_command
    paths_path = tmp_path / "paths.yaml"
    paths_path.write_text(yaml.safe_dump(config.pop("paths")), encoding="utf-8")
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    args.extend(["--paths-config", str(paths_path)])
    result = subprocess.run(
        [sys.executable, "-m", "energy_trading_pipeline.cli", *args],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Dashboard exports written to:" in result.stdout
    assert len(list((tmp_path / "reports/dashboard_exports").glob("*.parquet"))) == 4


@pytest.mark.parametrize(
    "fault", ["missing_input", "metrics_schema", "reports_path", "model_yaml"]
)
def test_export_command_fails_clearly_without_running_pipeline(
    tmp_path, export_command, saved_results, capsys, fault
):
    args, config_path, config = export_command
    if fault == "missing_input":
        saved_results["forecasts"].unlink()
    elif fault == "metrics_schema":
        pd.DataFrame({"unexpected": [1]}).to_parquet(saved_results["metrics"])
    elif fault == "reports_path":
        del config["paths"]["reports_dir"]
        config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    else:
        saved_results["model_index"].write_text("models: [", encoding="utf-8")
    assert cli.main(args) == 1
    assert "Error:" in capsys.readouterr().err
    assert not (tmp_path / "reports" / "dashboard_exports").exists()
    assert not (tmp_path / "models").exists()


@pytest.mark.parametrize(
    "option", ["--forecasts", "--metrics", "--retraining-events", "--model-index"]
)
def test_export_command_requires_explicit_saved_inputs(export_command, option):
    args, _, _ = export_command
    position = args.index(option)
    del args[position:position + 2]
    with pytest.raises(SystemExit) as exc:
        cli.parse_args(args)
    assert exc.value.code == 2


def test_export_command_rejects_source_output_collision(
    tmp_path, export_command, saved_results, capsys
):
    args, _, _ = export_command
    source = tmp_path / "reports" / "dashboard_exports" / "forecasts.parquet"
    source.parent.mkdir(parents=True)
    original = saved_results["forecasts"].read_bytes()
    source.write_bytes(original)
    args[args.index("--forecasts") + 1] = str(source)
    assert cli.main(args) == 1
    assert "must not overwrite source artifacts" in capsys.readouterr().err
    assert source.read_bytes() == original
    assert list(source.parent.iterdir()) == [source]


@pytest.mark.parametrize("fault", ["missing_type", "missing_version", "non_parquet"])
def test_export_command_rejects_invalid_metadata_and_formats(
    tmp_path, export_command, capsys, fault
):
    args, _, _ = export_command
    if fault == "non_parquet":
        args[args.index("--metrics") + 1] = str(tmp_path / "metrics.csv")
    else:
        position = args.index("--model-index")
        del args[position:position + 2]
        metadata = {
            "model_version": "fixture_model", "config": {"model": {"type": "xgboost"}}
        }
        if fault == "missing_type":
            metadata["config"] = {}
        else:
            del metadata["model_version"]
        path = tmp_path / "run_metadata.yaml"
        path.write_text(yaml.safe_dump(metadata), encoding="utf-8")
        args.extend(["--run-metadata", str(path)])
    assert cli.main(args) == 1
    assert "Error:" in capsys.readouterr().err
    assert not (tmp_path / "reports" / "dashboard_exports").exists()


@pytest.mark.parametrize("command", ["train", "backtest", None])
def test_export_flags_are_rejected_for_other_commands(export_command, command):
    args, _, _ = export_command
    if command is None:
        args.pop(0)
    else:
        args[0] = command
    with pytest.raises(SystemExit) as exc:
        cli.parse_args(args)
    assert exc.value.code == 2