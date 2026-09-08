"""Canonical spread arithmetic and processed artifact contracts."""

import numpy as np
import pandas as pd
import pytest
import yaml

from energy_trading_pipeline.preprocessing.spread import (
    calculate_spread,
    save_processed_data,
)


@pytest.fixture
def aligned_prices():
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2023-01-01", periods=4, freq="h", tz="UTC"),
            "price_de": [53.31, -10.0, 0.0, -20.0],
            "price_fr": [51.50, -20.0, 0.0, 10.0],
            "load_de": [100.0, 110.0, 120.0, 130.0],
        }
    )


def test_calculate_spread_preserves_input_and_optional_columns(aligned_prices):
    original = aligned_prices.copy(deep=True)
    result = calculate_spread(aligned_prices)
    assert result["spread"].tolist() == pytest.approx([1.81, 10.0, 0.0, -30.0])
    pd.testing.assert_frame_equal(result.drop(columns="spread"), original)
    pd.testing.assert_frame_equal(aligned_prices, original)


def test_calculate_spread_replaces_stale_target(aligned_prices):
    aligned_prices["spread"] = 999.0
    assert calculate_spread(aligned_prices)["spread"].tolist() == pytest.approx(
        [1.81, 10.0, 0.0, -30.0]
    )


@pytest.mark.parametrize("column", ["timestamp", "price_de", "price_fr"])
def test_missing_required_column_fails(aligned_prices, column):
    with pytest.raises(ValueError, match="Missing required columns"):
        calculate_spread(aligned_prices.drop(columns=column))


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf, "invalid", True, 1j])
@pytest.mark.parametrize("column", ["price_de", "price_fr"])
def test_invalid_required_prices_fail(aligned_prices, column, value):
    aligned_prices[column] = pd.Series([value] * len(aligned_prices))
    with pytest.raises(ValueError, match=column):
        calculate_spread(aligned_prices)


def test_unsigned_prices_do_not_wrap(aligned_prices):
    aligned_prices["price_de"] = pd.Series([0, 10, 20, 30], dtype="uint8")
    aligned_prices["price_fr"] = pd.Series([10, 20, 30, 40], dtype="uint8")
    assert calculate_spread(aligned_prices)["spread"].tolist() == [-10.0] * 4


@pytest.mark.parametrize("problem", ["empty", "duplicate", "gap", "off_hour", "naive"])
def test_invalid_hourly_data_fails(aligned_prices, problem):
    if problem == "empty":
        aligned_prices = aligned_prices.iloc[:0]
    elif problem == "duplicate":
        aligned_prices.loc[1, "timestamp"] = aligned_prices.loc[0, "timestamp"]
    elif problem == "gap":
        aligned_prices = aligned_prices.drop(index=1)
    elif problem == "off_hour":
        aligned_prices["timestamp"] += pd.Timedelta(minutes=30)
    else:
        aligned_prices["timestamp"] = aligned_prices["timestamp"].dt.tz_localize(None)
    with pytest.raises(ValueError):
        calculate_spread(aligned_prices)


def test_spread_sorts_and_converts_aware_timestamps(aligned_prices):
    aligned_prices["timestamp"] = aligned_prices["timestamp"].dt.tz_convert(
        "Europe/Berlin"
    )
    result = calculate_spread(aligned_prices.iloc[::-1])
    assert str(result["timestamp"].dt.tz) == "UTC"
    assert result["timestamp"].is_monotonic_increasing
    assert result["spread"].tolist() == pytest.approx([1.81, 10.0, 0.0, -30.0])


def test_save_processed_parquet_and_metadata(tmp_path, aligned_prices):
    output = tmp_path / "data/processed/aligned_hourly/prices.parquet"
    sources = {"price_de": tmp_path / "de.csv", "price_fr": tmp_path / "fr.csv"}
    report = {"excluded_optional_columns": ["temperature"]}
    parquet_path, metadata_path = save_processed_data(
        aligned_prices, output, source_files=sources, alignment_metadata=report
    )
    assert parquet_path == output
    assert metadata_path == output.with_suffix(".metadata.yaml")
    pd.testing.assert_frame_equal(pd.read_parquet(output), calculate_spread(aligned_prices))
    metadata = yaml.safe_load(metadata_path.read_text())
    assert metadata["source_files"] == {key: str(path) for key, path in sources.items()}
    assert metadata["date_range"] == {
        "start": "2023-01-01T00:00:00+00:00",
        "end": "2023-01-01T03:00:00+00:00",
    }
    assert metadata["target_column"] == "spread"
    assert metadata["spread_formula"] == "price_de - price_fr"
    assert metadata["output_rows"] == 4
    assert metadata["alignment"] == report


@pytest.mark.parametrize(
    "sources",
    [{}, {"price_de": "de.csv"}, {"price_de": "", "price_fr": "fr.csv"}],
)
def test_missing_provenance_fails_before_writing(tmp_path, aligned_prices, sources):
    output = tmp_path / "processed/prices.parquet"
    with pytest.raises(ValueError, match="source_files"):
        save_processed_data(aligned_prices, output, source_files=sources)
    assert not output.parent.exists()


def test_non_parquet_destination_fails_before_writing(tmp_path, aligned_prices):
    with pytest.raises(ValueError, match="parquet"):
        save_processed_data(
            aligned_prices,
            tmp_path / "prices.csv",
            source_files={"price_de": "de.csv", "price_fr": "fr.csv"},
        )
    assert not (tmp_path / "prices.csv").exists()


def test_duplicate_columns_fail(aligned_prices):
    duplicate = pd.concat([aligned_prices, aligned_prices[["price_de"]]], axis=1)
    with pytest.raises(ValueError, match="Duplicate column names"):
        calculate_spread(duplicate)


def test_nullable_numeric_prices_are_supported(aligned_prices):
    aligned_prices["price_de"] = aligned_prices["price_de"].astype("Float64")
    assert calculate_spread(aligned_prices)["spread"].tolist() == pytest.approx(
        [1.81, 10.0, 0.0, -30.0]
    )


def test_overflow_fails_before_writing(tmp_path, aligned_prices):
    aligned_prices["price_de"] = 1e308
    aligned_prices["price_fr"] = -1e308
    output = tmp_path / "processed/prices.parquet"
    with pytest.raises(ValueError, match="spread.*non-finite"):
        save_processed_data(
            aligned_prices,
            output,
            source_files={"price_de": "de.csv", "price_fr": "fr.csv"},
        )
    assert not output.parent.exists()
