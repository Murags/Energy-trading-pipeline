"""Focused validation and non-calculating projection checks for dashboard exports."""

import numpy as np
import pandas as pd
import pytest

from energy_trading_pipeline.evaluation.exports import write_dashboard_exports
from energy_trading_pipeline.retraining.events import RETRAINING_EVENT_COLUMNS


START = pd.Timestamp("2024-01-01T00:00:00Z")
END = START + pd.Timedelta(hours=2)


@pytest.fixture
def export_inputs():
    return {
        "forecasts": pd.DataFrame({
            "timestamp": pd.date_range(START, periods=2, freq="h"),
            "forecast_timestamp": [START - pd.Timedelta(days=1)] * 2,
            "prediction": [-2.0, -1.0], "actual": [-1.0, np.nan],
            "strategy": ["no_retraining"] * 2,
            "model_version": ["fixture_model"] * 2,
            "spread_lag_24": [99.0, 99.0],
        }),
        "metrics": pd.DataFrame({
            "run_id": ["run_fixture"], "evaluation_start": [START],
            "evaluation_end": [END], "strategy": ["no_retraining"],
            "rmse": [123.0], "mae": [456.0], "retraining_count": [0],
            "retraining_frequency": [0.0], "unneeded_diagnostic": [99.0],
        }),
        "retraining_events": pd.DataFrame(columns=list(RETRAINING_EVENT_COLUMNS)),
        "model_index": {"models": {"fixture_model": {
            "model_version": "fixture_model", "model_type": "xgboost",
            "created_at": "2023-12-31T01:00:00+01:00",
        }}},
    }


def test_missing_monitoring_preserves_missing_values_and_stored_metrics(
    tmp_path, export_inputs
):
    paths = write_dashboard_exports(**export_inputs, exports_dir=tmp_path)
    forecasts = pd.read_parquet(paths["forecasts"])
    metrics = pd.read_parquet(paths["metrics"])
    assert forecasts["rolling_rmse"].isna().all()
    assert forecasts["prediction"].tolist() == [-2.0, -1.0]
    assert metrics["rmse"].tolist() == [123.0]
    assert metrics["mae"].tolist() == [456.0]
    assert "spread_lag_24" not in forecasts
    assert "unneeded_diagnostic" not in metrics
    events = pd.read_parquet(paths["retraining_events"])
    assert events.empty
    assert str(events["timestamp"].dtype) == "datetime64[ns, UTC]"
    assert str(events["strategy"].dtype).startswith("string")
    models = pd.read_parquet(paths["model_versions"])
    assert list(models.columns) == ["model_version", "model_type"]
    assert models["model_version"].tolist() == ["fixture_model"]


def test_half_open_evaluation_window_and_sparse_monitoring(tmp_path, export_inputs):
    outside = export_inputs["forecasts"].iloc[:1].copy()
    outside["timestamp"] = END
    export_inputs["forecasts"] = pd.concat(
        [outside, export_inputs["forecasts"].iloc[::-1]], ignore_index=True
    )
    export_inputs["monitoring"] = pd.DataFrame({
        "timestamp": [START.tz_convert("Europe/Berlin")],
        "strategy": ["no_retraining"], "rolling_rmse": [42.0],
    })
    paths = write_dashboard_exports(**export_inputs, exports_dir=tmp_path)
    forecasts = pd.read_parquet(paths["forecasts"])
    assert forecasts["timestamp"].tolist() == [START, START + pd.Timedelta(hours=1)]
    assert forecasts["rolling_rmse"].iloc[0] == 42.0
    assert pd.isna(forecasts["rolling_rmse"].iloc[1])


@pytest.mark.parametrize(
    "invalid", [
        "model_type", "models_mapping", "model_version", "missing_model_type",
        "missing_run_id", "naive_window", "reversed_window", "infinite_metric",
        "boolean_metric", "count_overflow", "missing_count", "forecast_run_id",
    ],
)
def test_invalid_inputs_preserve_existing_dashboard_snapshot(
    tmp_path, export_inputs, invalid
):
    paths = write_dashboard_exports(**export_inputs, exports_dir=tmp_path)
    original = {name: path.read_bytes() for name, path in paths.items()}
    metadata = export_inputs["model_index"]["models"]["fixture_model"]
    metrics = export_inputs["metrics"]
    if invalid == "model_type":
        metadata["model_type"] = "other_model"
    elif invalid == "models_mapping":
        export_inputs["model_index"] = {"models": []}
    elif invalid == "model_version":
        metadata["model_version"] = "other_version"
    elif invalid == "missing_model_type":
        del metadata["model_type"]
    elif invalid == "missing_run_id":
        metrics["run_id"] = ""
    elif invalid == "naive_window":
        metrics["evaluation_start"] = START.tz_localize(None)
    elif invalid == "reversed_window":
        metrics["evaluation_end"] = START
    elif invalid == "infinite_metric":
        metrics["rmse"] = np.inf
    elif invalid == "boolean_metric":
        metrics["rmse"] = True
    elif invalid == "count_overflow":
        metrics["retraining_count"] = float(2**63)
    elif invalid == "missing_count":
        metrics["retraining_count"] = np.nan
    else:
        export_inputs["forecasts"]["run_id"] = "other_run"
    with pytest.raises(ValueError):
        write_dashboard_exports(**export_inputs, exports_dir=tmp_path)
    for name, path in paths.items():
        assert path.read_bytes() == original[name]