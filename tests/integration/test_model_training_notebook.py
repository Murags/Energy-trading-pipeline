"""The model training notebook runs end to end on offline fixtures."""

import json
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK_PATH = REPO_ROOT / "notebooks/03_model_training_validation.ipynb"


def load_notebook() -> dict:
    """Load the notebook without requiring notebook-only dependencies."""
    return json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))


def cell_source(cell: dict) -> str:
    """Notebook JSON may store source as a string or a list of lines."""
    return "".join(cell["source"])


def test_notebook_presents_every_training_stage():
    notebook = load_notebook()
    markdown = "\n".join(
        cell_source(cell)
        for cell in notebook["cells"]
        if cell["cell_type"] == "markdown"
    )

    assert notebook["nbformat"] == 4
    assert "Stage 3 - Chronological train/validation split" in markdown
    assert "Stage 4 - Training with the CLI training function" in markdown
    assert "Stage 5 - Reload the artifact and reproduce its metrics" in markdown
    assert "One-step-ahead, not day-ahead" in markdown


def test_all_code_cells_execute_in_fixture_mode(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)
    monkeypatch.setenv("ETP_NOTEBOOK_MODE", "fixture")
    monkeypatch.setenv("MPLBACKEND", "Agg")
    namespace = {"__name__": "__main__"}

    for position, cell in enumerate(load_notebook()["cells"]):
        if cell["cell_type"] != "code":
            continue
        source = cell_source(cell)
        exec(compile(source, f"{NOTEBOOK_PATH.name}:cell-{position}", "exec"), namespace)

    split = namespace["split"]
    run_metadata = namespace["run_metadata"]
    validation_results = namespace["validation_results"]

    # Weather enters only as lags; the same-hour source columns never do.
    features = namespace["features"]
    assert namespace["lagged_weather_columns"]
    assert set(namespace["lagged_weather_columns"]).issubset(features.columns)
    assert not set(namespace["weather_sources"]).intersection(features.columns)

    # Training stays strictly before validation on the selected rows.
    assert split.train_timestamps.max() < split.validation_timestamps.min()
    assert split.metadata["validation_rows"] == 48

    # The notebook trains through train_baseline into its temporary workspace.
    workspace_dir = namespace["WORKSPACE_DIR"]
    assert Path(run_metadata["artifact_paths"]["model"]).is_relative_to(workspace_dir)
    assert Path(run_metadata["artifact_paths"]["run_metadata"]).is_relative_to(
        workspace_dir
    )

    assert validation_results.columns.tolist() == [
        "timestamp",
        "actual",
        "prediction",
        "error",
        "squared_error",
        "absolute_error",
    ]
    rmse = float(np.sqrt(validation_results["squared_error"].mean()))
    np.testing.assert_allclose(rmse, run_metadata["metrics"]["rmse"])
    np.testing.assert_allclose(
        validation_results["absolute_error"].mean(), run_metadata["metrics"]["mae"]
    )

    assert namespace["registry_summary"]["status"].tolist() == ["rescored"]
    assert namespace["canonical_state_after"] == namespace["canonical_state_before"]
    namespace["workspace"].cleanup()
