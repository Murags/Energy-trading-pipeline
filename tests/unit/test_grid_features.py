"""Optional grid predictor selection for the feature dataset."""

import logging

import pandas as pd
import pytest

from energy_trading_pipeline.features.grid_features import (
    DEFAULT_GRID_COLUMNS,
    GRID_STAGE,
    build_grid_features,
)

HOURS = 8


@pytest.fixture
def aligned_hourly():
    """Eight contiguous UTC hours carrying one of the optional grid series."""
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2023-01-01", periods=HOURS, freq="h", tz="UTC"),
            "price_de": [50.0 + index for index in range(HOURS)],
            "price_fr": [40.0 + index for index in range(HOURS)],
            "spread": [10.0] * HOURS,
            "load_de": [100 + index for index in range(HOURS)],
        }
    )


def test_default_columns_are_the_optional_load_and_generation_series():
    assert DEFAULT_GRID_COLUMNS == (
        "load_de",
        "load_fr",
        "generation_de",
        "generation_fr",
    )


def test_available_default_columns_are_passed_through(aligned_hourly):
    result, metadata = build_grid_features(aligned_hourly)

    assert metadata["stage"] == GRID_STAGE
    assert metadata["group"] == "grid"
    assert metadata["selected_columns"] == ["load_de"]
    assert result["load_de"].tolist() == aligned_hourly["load_de"].astype(
        float
    ).tolist()


def test_uningested_grid_columns_warn_and_continue(aligned_hourly, caplog):
    caplog.set_level(logging.WARNING)

    result, metadata = build_grid_features(aligned_hourly)

    assert metadata["missing_columns"] == [
        "load_fr",
        "generation_de",
        "generation_fr",
    ]
    assert "load_fr" in caplog.text
    assert len(result) == HOURS


def test_grid_columns_are_config_driven(aligned_hourly):
    _, metadata = build_grid_features(aligned_hourly, columns=["load_de"])

    assert metadata["requested_columns"] == ["load_de"]
    assert metadata["selected_columns"] == ["load_de"]
    assert metadata["missing_columns"] == []


def test_no_grid_columns_can_be_requested(aligned_hourly):
    result, metadata = build_grid_features(aligned_hourly, columns=[])

    assert metadata["selected_columns"] == []
    pd.testing.assert_frame_equal(result, aligned_hourly)


def test_a_dataset_without_grid_data_still_builds(caplog):
    caplog.set_level(logging.WARNING)
    prices = pd.DataFrame(
        {
            "timestamp": pd.date_range("2023-01-01", periods=HOURS, freq="h", tz="UTC"),
            "price_de": [50.0] * HOURS,
            "price_fr": [40.0] * HOURS,
            "spread": [10.0] * HOURS,
        }
    )

    result, metadata = build_grid_features(prices)

    assert metadata["selected_columns"] == []
    assert metadata["missing_columns"] == list(DEFAULT_GRID_COLUMNS)
    assert len(result) == HOURS
    assert "grid" in caplog.text


def test_input_dataframe_is_not_mutated(aligned_hourly):
    original = aligned_hourly.copy(deep=True)

    build_grid_features(aligned_hourly)

    pd.testing.assert_frame_equal(aligned_hourly, original)
