"""Unit tests for local CSV and Parquet data loading."""

import logging
from pathlib import Path

import pandas as pd
import pytest

from energy_trading_pipeline.data_ingestion.local_loader import load_local_data


FIXTURES_DIR = Path(__file__).parents[1] / "fixtures"


@pytest.fixture
def sample_data() -> pd.DataFrame:
    """Provide a small local-data fixture."""
    return pd.DataFrame(
        {
            "timestamp": ["2023-01-01T00:00:00Z", "2023-01-01T01:00:00Z"],
            "price_de": [100.0, 101.5],
            "price_fr": [90.0, 91.5],
        }
    )


@pytest.mark.parametrize(
    ("fixture_name", "expected_column"),
    [
        ("sample_prices_de.csv", "price_de"),
        ("sample_prices_fr.csv", "price_fr"),
        ("sample_weather.csv", "temperature_2m_c"),
    ],
)
def test_load_local_data_reads_checked_in_csv_fixtures_and_logs_source_details(
    fixture_name, expected_column, caplog
):
    csv_path = FIXTURES_DIR / fixture_name

    with caplog.at_level(logging.INFO):
        result = load_local_data(csv_path)

    assert {"timestamp", expected_column}.issubset(result.columns)
    assert str(csv_path) in caplog.text
    assert f"{len(result)} rows" in caplog.text


def test_load_local_data_reads_parquet_and_logs_source_details(
    tmp_path, sample_data, caplog
):
    parquet_path = tmp_path / "prices.parquet"
    sample_data.to_parquet(parquet_path, index=False)

    with caplog.at_level(logging.INFO):
        result = load_local_data(parquet_path)

    pd.testing.assert_frame_equal(result, sample_data)
    assert str(parquet_path) in caplog.text
    assert "2 rows" in caplog.text


def test_load_local_data_raises_clear_error_for_missing_file(tmp_path):
    missing_path = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError, match="Local data file not found"):
        load_local_data(missing_path)


def test_load_local_data_raises_clear_error_for_unsupported_format(tmp_path):
    json_path = tmp_path / "prices.json"
    json_path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported local data format"):
        load_local_data(json_path)
