"""The data preprocessing notebook runs end to end on offline fixtures."""

import json
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK_PATH = REPO_ROOT / "notebooks/02_data_preprocessing.ipynb"


def load_notebook() -> dict:
    """Load the notebook without requiring notebook-only dependencies."""
    return json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))


def test_notebook_presents_every_preprocessing_stage():
    notebook = load_notebook()
    markdown = "\n".join(
        cell["source"]
        for cell in notebook["cells"]
        if cell["cell_type"] == "markdown"
    )

    assert notebook["nbformat"] == 4
    assert "Stage 1 - Raw source records" in markdown
    assert "Stage 3 - Timestamp normalization" in markdown
    assert "Stage 4 - Cleaning rules" in markdown
    assert "Stage 5 - Combining energy and weather into one dataframe" in markdown
    assert "Stage 6 - Spread target" in markdown


def test_all_code_cells_execute_in_fixture_mode(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)
    monkeypatch.setenv("ETP_NOTEBOOK_MODE", "fixture")
    namespace = {"__name__": "__main__"}

    for position, cell in enumerate(load_notebook()["cells"]):
        if cell["cell_type"] != "code":
            continue
        source = cell["source"]
        exec(compile(source, f"{NOTEBOOK_PATH.name}:cell-{position}", "exec"), namespace)

    cleanup_reports = namespace["cleanup_reports"]
    combined_data = namespace["combined_data"]
    prepared_data = namespace["prepared_data"]

    # The duplicated fixture hour is removed, and the gapped weather column
    # is excluded rather than imputed.
    assert cleanup_reports["price_de"]["duplicate_rows_removed"] == 1
    assert cleanup_reports["weather"]["excluded_optional_columns"] == [
        "temperature_2m_c"
    ]

    assert len(combined_data) == 192
    assert "temperature_2m_c" not in combined_data.columns
    assert {"price_de", "price_fr", "wind_speed_10m_m_s"}.issubset(
        combined_data.columns
    )

    assert len(prepared_data) == 192
    assert prepared_data["timestamp"].is_monotonic_increasing
    assert prepared_data["timestamp"].is_unique
    assert str(prepared_data["timestamp"].dt.tz) == "UTC"
    assert not prepared_data.isna().any().any()
    np.testing.assert_allclose(
        prepared_data["spread"],
        prepared_data["price_de"] - prepared_data["price_fr"],
    )
    assert namespace["final_audit"]["hourly_index_valid"]
    assert namespace["reloaded_data"].columns.tolist() == prepared_data.columns.tolist()
