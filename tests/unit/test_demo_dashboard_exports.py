"""The synthetic demo exports load in the dashboard and stay clearly labelled."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from energy_trading_pipeline.dashboard.data_loader import load_dashboard_artifacts


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/make_demo_dashboard_exports.py"


@pytest.fixture(scope="module")
def demo():
    spec = importlib.util.spec_from_file_location("make_demo", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_demo_exports_load_and_are_marked_synthetic(demo, tmp_path):
    demo.write_demo_exports(tmp_path, start="2025-01-01", end="2025-03-31")
    artifacts = load_dashboard_artifacts(tmp_path)
    assert set(artifacts["metrics"]["run_id"]) == {demo.RUN_ID}
    assert demo.RUN_ID.startswith("synthetic")
    assert (tmp_path / demo.MARKER_FILE).is_file()
    referenced = set(artifacts["forecasts"]["model_version"]) | set(
        artifacts["retraining_events"]["model_version"]
    )
    assert referenced <= set(artifacts["model_versions"]["model_version"])


def test_demo_is_deterministic_and_triggers_respect_threshold(demo):
    first = demo.build_demo_exports()
    second = demo.build_demo_exports()
    assert first["forecasts"].equals(second["forecasts"])
    events = first["retraining_events"]
    triggered = events.loc[events["strategy"] == "performance_triggered"]
    assert (triggered["rolling_rmse"] > triggered["threshold"]).all()
    counts = first["metrics"].set_index("strategy")["retraining_count"]
    assert counts["no_retraining"] == 0
    assert 0 < counts["performance_triggered"] < counts["fixed_schedule"]
    # Each refit model serves from the day after its decision, never earlier.
    forecasts = first["forecasts"]
    for event in triggered.itertuples():
        served = forecasts.loc[forecasts["model_version"] == event.model_version]
        assert served["timestamp"].min() > event.timestamp
    rmse = first["metrics"].set_index("strategy")["rmse"]
    assert np.isfinite(rmse).all()
