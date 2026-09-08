"""Optional weather predictor selection for the feature dataset."""

import logging

import pandas as pd
import pytest

from energy_trading_pipeline.features.weather_features import (
    DEFAULT_WEATHER_COLUMNS,
    WEATHER_STAGE,
    build_weather_features,
)

HOURS = 8


@pytest.fixture
def aligned_hourly():
    """Eight contiguous UTC hours carrying two of the three weather variables."""
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2023-01-01", periods=HOURS, freq="h", tz="UTC"),
            "price_de": [50.0 + index for index in range(HOURS)],
            "price_fr": [40.0 + index for index in range(HOURS)],
            "spread": [10.0] * HOURS,
            "wind_speed_10m_m_s": [4.2 + index for index in range(HOURS)],
            "shortwave_radiation_w_m2": [0.0] * HOURS,
        }
    )


def test_default_columns_are_the_canonical_open_meteo_variables():
    assert DEFAULT_WEATHER_COLUMNS == (
        "temperature_2m_c",
        "wind_speed_10m_m_s",
        "shortwave_radiation_w_m2",
    )


def test_available_default_columns_are_passed_through(aligned_hourly):
    result, metadata = build_weather_features(aligned_hourly)

    assert metadata["stage"] == WEATHER_STAGE
    assert metadata["group"] == "weather"
    assert metadata["selected_columns"] == [
        "wind_speed_10m_m_s",
        "shortwave_radiation_w_m2",
    ]
    for column in metadata["selected_columns"]:
        assert result[column].tolist() == aligned_hourly[column].tolist()


def test_unavailable_weather_columns_warn_and_continue(aligned_hourly, caplog):
    caplog.set_level(logging.WARNING)

    result, metadata = build_weather_features(aligned_hourly)

    assert metadata["missing_columns"] == ["temperature_2m_c"]
    assert "temperature_2m_c" in caplog.text
    assert len(result) == HOURS


def test_weather_columns_are_config_driven(aligned_hourly):
    _, metadata = build_weather_features(
        aligned_hourly, columns=["shortwave_radiation_w_m2"]
    )

    assert metadata["requested_columns"] == ["shortwave_radiation_w_m2"]
    assert metadata["selected_columns"] == ["shortwave_radiation_w_m2"]


def test_no_weather_columns_can_be_requested(aligned_hourly):
    result, metadata = build_weather_features(aligned_hourly, columns=[])

    assert metadata["selected_columns"] == []
    pd.testing.assert_frame_equal(result, aligned_hourly)


def test_a_price_only_dataset_still_builds(caplog):
    caplog.set_level(logging.WARNING)
    prices = pd.DataFrame(
        {
            "timestamp": pd.date_range("2023-01-01", periods=HOURS, freq="h", tz="UTC"),
            "price_de": [50.0] * HOURS,
            "price_fr": [40.0] * HOURS,
            "spread": [10.0] * HOURS,
        }
    )

    result, metadata = build_weather_features(prices)

    assert metadata["selected_columns"] == []
    assert metadata["missing_columns"] == list(DEFAULT_WEATHER_COLUMNS)
    assert len(result) == HOURS
    assert "weather" in caplog.text


def test_input_dataframe_is_not_mutated(aligned_hourly):
    original = aligned_hourly.copy(deep=True)

    build_weather_features(aligned_hourly)

    pd.testing.assert_frame_equal(aligned_hourly, original)
