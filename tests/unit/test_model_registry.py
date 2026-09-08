"""Filesystem model persistence and index integrity on tiny fitted models."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from energy_trading_pipeline.models.registry import save_model_artifacts
from energy_trading_pipeline.models.xgboost_model import XGBoostSpreadModel

NOW = datetime(2026, 9, 8, 12, 30, 0, tzinfo=timezone.utc)
WINDOW = {
    "train_start_date": "2023-01-01",
    "train_end_date": "2023-01-02",
    "validation_start_date": "2023-01-03",
    "validation_end_date": "2023-01-03",
}
METRICS = {"rmse": 1.5, "mae": 1.0}


@pytest.fixture
def model():
    """Fit a small deterministic model without historical data."""
    return XGBoostSpreadModel({"n_estimators": 2, "random_state": 42}).fit(
        pd.DataFrame({"spread_lag_24": [1.0, 2.0, 3.0]}),
        pd.Series([2.0, 3.0, 4.0], name="spread"),
    )


def test_save_records_metadata_and_reloadable_model(tmp_path, model):
    result = save_model_artifacts(model, tmp_path, WINDOW, METRICS, now=NOW)

    version = "model_20260908_123000"
    directory = tmp_path / "artifacts" / version
    metadata = yaml.safe_load((directory / "metadata.yaml").read_text())
    assert result == metadata
    assert metadata["model_version"] == version
    assert metadata["created_at"] == NOW.isoformat()
    assert metadata["training_window"] == WINDOW
    assert metadata["feature_columns"] == ["spread_lag_24"]
    assert metadata["target_column"] == "spread"
    assert metadata["model_parameters"] == model.params
    assert metadata["validation_metrics"] == METRICS
    restored = XGBoostSpreadModel.load(directory / "model.json")
    features = pd.DataFrame({"spread_lag_24": [2.0, 4.0]})
    np.testing.assert_array_equal(model.predict(features), restored.predict(features))
    index = yaml.safe_load((tmp_path / "registry/models_index.yaml").read_text())
    assert index == {"models": {version: metadata}}


def test_index_preserves_previous_versions(tmp_path, model):
    first = save_model_artifacts(model, tmp_path, WINDOW, METRICS, now=NOW)
    second = save_model_artifacts(
        model, tmp_path, WINDOW, METRICS, now=NOW + timedelta(seconds=1)
    )
    index = yaml.safe_load((tmp_path / "registry/models_index.yaml").read_text())
    assert index["models"] == {
        first["model_version"]: first,
        second["model_version"]: second,
    }


def test_version_collision_leaves_existing_files_unchanged(tmp_path, model):
    save_model_artifacts(model, tmp_path, WINDOW, METRICS, now=NOW)
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    with pytest.raises(FileExistsError, match="model_20260908_123000"):
        save_model_artifacts(model, tmp_path, WINDOW, METRICS, now=NOW)
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize("contents", ["", "[]", "models: []", "models: [", "other: 1"])
def test_malformed_index_fails_without_writing_artifacts(tmp_path, model, contents):
    index = tmp_path / "registry/models_index.yaml"
    index.parent.mkdir()
    index.write_text(contents)
    with pytest.raises(ValueError, match="model index"):
        save_model_artifacts(model, tmp_path, WINDOW, METRICS, now=NOW)
    assert index.read_text() == contents
    assert not (tmp_path / "artifacts").exists()


def test_unfitted_model_is_rejected_before_writing(tmp_path):
    with pytest.raises(ValueError, match="not fitted"):
        save_model_artifacts(XGBoostSpreadModel(), tmp_path, WINDOW, METRICS)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("metrics", [{}, {"rmse": float("nan")}, {"rmse": -1.0}])
def test_invalid_metrics_are_rejected(tmp_path, model, metrics):
    with pytest.raises(ValueError, match="validation_metrics"):
        save_model_artifacts(model, tmp_path, WINDOW, metrics)
    assert list(tmp_path.iterdir()) == []


def test_failed_save_preserves_index_and_removes_partial_version(
    tmp_path, model, monkeypatch
):
    save_model_artifacts(model, tmp_path, WINDOW, METRICS, now=NOW)
    index = tmp_path / "registry/models_index.yaml"
    before = index.read_bytes()

    def fail_save(path: Path) -> Path:
        path.write_text("partial")
        raise OSError("disk failure")

    monkeypatch.setattr(model, "save", fail_save)
    with pytest.raises(OSError, match="disk failure"):
        save_model_artifacts(
            model, tmp_path, WINDOW, METRICS, now=NOW + timedelta(seconds=1)
        )
    assert index.read_bytes() == before
    assert not (tmp_path / "artifacts/model_20260908_123001").exists()
