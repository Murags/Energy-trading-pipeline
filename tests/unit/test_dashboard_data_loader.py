"""Read-only dashboard loading checks using small exported Parquet fixtures."""

import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from energy_trading_pipeline.dashboard.data_loader import (
    DashboardArtifactError,
    load_dashboard_artifacts,
)


@pytest.fixture
def dashboard_frames():
    timestamps = pd.date_range("2024-01-01", periods=2, freq="h", tz="UTC")
    frames = {
        "forecasts": pd.DataFrame({
            "timestamp": timestamps,
            "prediction": [-2.0, -1.0],
            "actual": [-1.0, np.nan],
            "strategy": ["fixed_schedule"] * 2,
            "model_version": ["fixture_model"] * 2,
            "rolling_rmse": [np.nan, 42.0],
        }),
        "metrics": pd.DataFrame({
            "run_id": ["run_fixture"],
            "evaluation_start": [timestamps[0]],
            "evaluation_end": [timestamps[-1] + pd.Timedelta(hours=1)],
            "strategy": ["fixed_schedule"],
            "rmse": [123.0], "mae": [456.0],
            "retraining_count": [1], "retraining_frequency": [12.0],
        }),
        "retraining_events": pd.DataFrame({
            "timestamp": timestamps,
            "strategy": ["fixed_schedule"] * 2,
            "trigger_reason": ["scheduled"] * 2,
            "threshold": [np.nan] * 2,
            "rolling_rmse": [np.nan, 42.0],
            "model_version": ["fixture_model"] * 2,
        }),
        "model_versions": pd.DataFrame({
            "model_version": ["fixture_model"], "model_type": ["xgboost"],
        }),
    }
    for frame in frames.values():
        for column in ("timestamp", "evaluation_start", "evaluation_end"):
            if column in frame:
                frame[column] = frame[column].astype("datetime64[ns, UTC]")
    return frames


@pytest.fixture
def dashboard_exports(tmp_path, dashboard_frames):
    exports_dir = tmp_path / "reports" / "dashboard_exports"
    exports_dir.mkdir(parents=True)
    for name, frame in dashboard_frames.items():
        frame.to_parquet(exports_dir / f"{name}.parquet", index=False)
    return exports_dir


@pytest.fixture
def streamlit_exports(dashboard_exports, dashboard_frames):
    strategies = ["no_retraining", "fixed_schedule", "performance_triggered"]
    frames = {name: frame.copy() for name, frame in dashboard_frames.items()}
    for name in ("forecasts", "metrics"):
        frames[name] = pd.concat(
            [frames[name].assign(strategy=strategy) for strategy in strategies],
            ignore_index=True,
        )
    frames["forecasts"].loc[3, "model_version"] = "new_model"
    frames["retraining_events"] = frames["retraining_events"].iloc[-1:].copy()
    frames["retraining_events"]["model_version"] = "new_model"
    frames["model_versions"] = pd.DataFrame({
        "model_version": ["fixture_model", "new_model"],
        "model_type": ["xgboost", "xgboost"],
    })
    for name, frame in frames.items():
        frame.to_parquet(dashboard_exports / f"{name}.parquet", index=False)
    return dashboard_exports


def run_dashboard(monkeypatch, working_dir):
    testing = pytest.importorskip("streamlit.testing.v1")
    monkeypatch.chdir(working_dir)
    for name in ("ENTSOE_API_KEY", "ENTSOE_API_TOKEN", "AWS_ACCESS_KEY_ID",
                 "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    app_path = (
        Path(__file__).resolve().parents[2]
        / "src/energy_trading_pipeline/dashboard/app.py"
    )
    return testing.AppTest.from_file(str(app_path)).run(timeout=15)


def test_streamlit_dashboard_views_filters_and_read_only_exports(
    streamlit_exports, monkeypatch
):
    before = {path: path.read_bytes() for path in streamlit_exports.iterdir()}
    app = run_dashboard(monkeypatch, streamlit_exports.parents[1])
    assert not app.exception
    assert not app.error
    assert [tab.label for tab in app.tabs] == [
        "Forecasts", "Rolling RMSE", "Retraining", "Models", "Comparison",
    ]
    assert len(app.get("plotly_chart")) == 5
    assert len(app.dataframe) == 6
    assert app.dataframe[0].value["rmse"].tolist() == [123.0] * 3
    assert app.dataframe[0].value["mae"].tolist() == [456.0] * 3
    app.sidebar.multiselect[0].set_value(["no_retraining"]).run()
    assert not app.exception
    for table in app.dataframe:
        if "strategy" in table.value:
            assert set(table.value["strategy"]) <= {"no_retraining"}
        if "model_type" in table.value:
            assert set(table.value["model_version"]) == {"fixture_model"}
    for element in app.get("plotly_chart"):
        figure = json.loads(element.proto.spec)
        for trace in figure["data"]:
            if trace["type"] == "scatter":
                assert "no_retraining" in trace["name"]
    assert any("No retraining events" in info.value for info in app.info)
    app.sidebar.multiselect[0].set_value([]).run()
    assert not app.exception
    assert any("No strategies selected" in info.value for info in app.info)
    assert not app.get("plotly_chart")
    assert {path: path.read_bytes() for path in streamlit_exports.iterdir()} == before


@pytest.mark.parametrize("scenario", ["empty", "no_events", "no_scores"])
def test_streamlit_dashboard_handles_sparse_exports(
    streamlit_exports, monkeypatch, scenario
):
    for path in streamlit_exports.iterdir():
        frame = pd.read_parquet(path)
        if scenario == "empty" or (
            scenario == "no_events" and path.stem == "retraining_events"
        ):
            frame = frame.iloc[:0]
        elif scenario == "no_scores":
            if path.stem == "forecasts":
                frame[["actual", "rolling_rmse"]] = np.nan
            elif path.stem == "metrics":
                frame[["rmse", "mae"]] = np.nan
        frame.to_parquet(path, index=False)
    app = run_dashboard(monkeypatch, streamlit_exports.parents[1])
    assert not app.exception
    assert not app.error
    if scenario == "empty":
        assert any("No exported strategies" in info.value for info in app.info)
    elif scenario == "no_events":
        assert any("No retraining events" in info.value for info in app.info)
    else:
        assert app.dataframe[0].value[["rmse", "mae"]].isna().all().all()
        assert any("Rolling RMSE unavailable" in info.value for info in app.info)


def test_streamlit_dashboard_missing_exports_and_custom_directory(
    streamlit_exports, tmp_path, monkeypatch
):
    working_dir = tmp_path / "other"
    working_dir.mkdir()
    app = run_dashboard(monkeypatch, working_dir)
    assert not app.exception
    assert len(app.error) == 1
    assert "export-dashboard" in app.error[0].value
    app.sidebar.text_input[0].set_value(str(streamlit_exports)).run()
    assert not app.exception
    assert not app.error
    assert len(app.get("plotly_chart")) == 5


def test_loads_default_exports_without_changing_files(
    tmp_path, monkeypatch, dashboard_exports, dashboard_frames
):
    monkeypatch.chdir(tmp_path)
    before = {path: path.read_bytes() for path in dashboard_exports.iterdir()}
    loaded = load_dashboard_artifacts()
    assert set(loaded) == set(dashboard_frames)
    for name, expected in dashboard_frames.items():
        assert_frame_equal(loaded[name], expected)
    assert {path: path.read_bytes() for path in dashboard_exports.iterdir()} == before


@pytest.mark.parametrize(
    "name", ["forecasts", "metrics", "retraining_events", "model_versions"]
)
def test_missing_export_has_actionable_message(dashboard_exports, name):
    missing = dashboard_exports / f"{name}.parquet"
    missing.unlink()
    with pytest.raises(DashboardArtifactError) as caught:
        load_dashboard_artifacts(dashboard_exports)
    message = str(caught.value)
    assert str(missing) in message
    assert "export-dashboard" in message


def test_missing_directory_is_not_created(tmp_path):
    missing = tmp_path / "dashboard_exports"
    with pytest.raises(DashboardArtifactError, match="forecasts.parquet"):
        load_dashboard_artifacts(missing)
    assert not missing.exists()


@pytest.mark.parametrize(
    "name,column", [
        ("forecasts", "actual"), ("metrics", "evaluation_start"),
        ("retraining_events", "trigger_reason"), ("model_versions", "model_type"),
    ],
)
def test_missing_columns_identify_file_and_column(
    dashboard_exports, dashboard_frames, name, column
):
    path = dashboard_exports / f"{name}.parquet"
    dashboard_frames[name].drop(columns=column).to_parquet(path, index=False)
    with pytest.raises(DashboardArtifactError) as caught:
        load_dashboard_artifacts(dashboard_exports)
    assert str(path) in str(caught.value)
    assert column in str(caught.value)


@pytest.mark.parametrize(
    "name", ["forecasts", "metrics", "retraining_events", "model_versions"]
)
def test_invalid_parquet_has_user_facing_error(dashboard_exports, name):
    path = dashboard_exports / f"{name}.parquet"
    path.write_bytes(b"not a parquet file")
    with pytest.raises(DashboardArtifactError) as caught:
        load_dashboard_artifacts(dashboard_exports)
    assert str(path) in str(caught.value)
    assert caught.value.__cause__ is not None


def test_empty_exports_keep_schemas(dashboard_exports, dashboard_frames):
    for name, frame in dashboard_frames.items():
        frame.iloc[:0].to_parquet(dashboard_exports / f"{name}.parquet", index=False)
    loaded = load_dashboard_artifacts(dashboard_exports)
    for name, frame in dashboard_frames.items():
        assert_frame_equal(loaded[name], frame.iloc[:0])


def test_extra_columns_are_not_returned(dashboard_exports, dashboard_frames):
    for name, frame in dashboard_frames.items():
        frame.assign(unneeded_diagnostic=99).to_parquet(
            dashboard_exports / f"{name}.parquet", index=False
        )
    loaded = load_dashboard_artifacts(dashboard_exports)
    for name, expected in dashboard_frames.items():
        assert_frame_equal(loaded[name], expected)


def test_read_access_error_is_wrapped(dashboard_exports, monkeypatch):
    def denied(path):
        raise PermissionError("Access denied")

    monkeypatch.setattr(pd, "read_parquet", denied)
    with pytest.raises(DashboardArtifactError, match="forecasts.parquet") as caught:
        load_dashboard_artifacts(dashboard_exports)
    assert isinstance(caught.value.__cause__, PermissionError)


def test_duplicate_columns_are_rejected(dashboard_exports, monkeypatch):
    monkeypatch.setattr(
        pd, "read_parquet", lambda path: pd.DataFrame(columns=["actual", "actual"])
    )
    with pytest.raises(DashboardArtifactError, match="unique column names"):
        load_dashboard_artifacts(dashboard_exports)


def test_timestamps_are_utc_chronological_and_indexes_are_reset(
    dashboard_exports, dashboard_frames
):
    for name in ("forecasts", "retraining_events"):
        frame = dashboard_frames[name].iloc[::-1].copy()
        frame["timestamp"] = frame["timestamp"].dt.tz_convert("Europe/Berlin")
        frame.to_parquet(dashboard_exports / f"{name}.parquet", index=True)
    metrics = dashboard_frames["metrics"].copy()
    for column in ("evaluation_start", "evaluation_end"):
        metrics[column] = metrics[column].dt.tz_convert("Europe/Paris").astype(str)
    metrics.to_parquet(dashboard_exports / "metrics.parquet", index=False)
    loaded = load_dashboard_artifacts(str(dashboard_exports))
    for name in ("forecasts", "retraining_events", "metrics"):
        assert_frame_equal(loaded[name], dashboard_frames[name])


@pytest.mark.parametrize(
    "name,column", [
        ("forecasts", "timestamp"), ("retraining_events", "timestamp"),
        ("metrics", "evaluation_start"), ("metrics", "evaluation_end"),
    ],
)
@pytest.mark.parametrize("value", ["invalid-date", None])
def test_invalid_timestamps_identify_file_and_column(
    dashboard_exports, dashboard_frames, name, column, value
):
    frame = dashboard_frames[name].copy()
    frame[column] = value
    path = dashboard_exports / f"{name}.parquet"
    frame.to_parquet(path, index=False)
    with pytest.raises(DashboardArtifactError) as caught:
        load_dashboard_artifacts(dashboard_exports)
    assert str(path) in str(caught.value)
    assert column in str(caught.value)


@pytest.mark.parametrize("module_name", ["data_loader", "app", "charts"])
def test_dashboard_modules_never_import_pipeline_stages(
    dashboard_exports, module_name
):
    code = """
import importlib
import importlib.abc
import sys

class BlockPipelineImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        forbidden = (
            'energy_trading_pipeline.backtesting',
            'energy_trading_pipeline.models',
            'energy_trading_pipeline.data_ingestion',
            'energy_trading_pipeline.retraining',
            'energy_trading_pipeline.evaluation',
            'streamlit',
        )
        if fullname.startswith(forbidden):
            raise AssertionError('Forbidden pipeline import: ' + fullname)

sys.meta_path.insert(0, BlockPipelineImports())
module = importlib.import_module('energy_trading_pipeline.dashboard.' + sys.argv[2])
from energy_trading_pipeline.dashboard.data_loader import load_dashboard_artifacts
if sys.argv[2] == 'data_loader':
    assert len(load_dashboard_artifacts(sys.argv[1])) == 4
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(dashboard_exports), module_name],
        cwd=dashboard_exports,
        env=os.environ | {
            "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src"),
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr