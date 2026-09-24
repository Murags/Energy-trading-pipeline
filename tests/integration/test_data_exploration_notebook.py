"""The data exploration notebook runs end to end on offline fixtures."""

import json
from pathlib import Path

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK_PATH = REPO_ROOT / "notebooks/01_data_exploration.ipynb"


def load_notebook() -> dict:
    """Load the notebook without requiring notebook-only dependencies."""
    return json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))


def test_notebook_has_linear_presentation_structure():
    notebook = load_notebook()
    markdown = "\n".join(
        cell["source"]
        for cell in notebook["cells"]
        if cell["cell_type"] == "markdown"
    )

    assert notebook["nbformat"] == 4
    assert "Data lineage" in markdown
    assert "Cleanup decisions" in markdown
    assert "Exact hourly alignment" in markdown
    assert "Daylight-saving time" in markdown
    assert "Modelling handoff" in markdown
    assert "ERA5" in markdown


def test_all_code_cells_execute_in_fixture_mode(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)
    monkeypatch.setenv("ETP_NOTEBOOK_MODE", "fixture")
    monkeypatch.setenv("MPLBACKEND", "Agg")
    namespace = {"__name__": "__main__"}

    for position, cell in enumerate(load_notebook()["cells"]):
        if cell["cell_type"] != "code":
            continue
        source = cell["source"]
        exec(compile(source, f"{NOTEBOOK_PATH.name}:cell-{position}", "exec"), namespace)

    prepared_data = namespace["prepared_data"]
    required = ["timestamp", "price_de", "price_fr", "spread"]
    retained_weather = [
        "wind_speed_10m_m_s",
        "shortwave_radiation_w_m2",
    ]

    assert len(prepared_data) == 192
    assert prepared_data["timestamp"].is_monotonic_increasing
    assert prepared_data["timestamp"].is_unique
    assert str(prepared_data["timestamp"].dt.tz) == "UTC"
    assert not prepared_data[required + retained_weather].isna().any().any()
    assert np.isfinite(prepared_data[["price_de", "price_fr", "spread"]]).all().all()
    np.testing.assert_allclose(
        prepared_data["spread"],
        prepared_data["price_de"] - prepared_data["price_fr"],
    )
    assert "temperature_2m_c" not in prepared_data.columns
    assert namespace["alignment_report"]["output_rows"] == 192
    assert namespace["dst_day_audit"].empty
    assert namespace["final_audit"]["spread_formula_verified"]
