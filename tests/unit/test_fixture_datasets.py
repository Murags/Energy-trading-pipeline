"""Contract tests for checked-in local dataset fixtures."""

from pathlib import Path

import pandas as pd

from energy_trading_pipeline.config.loader import load_config
from energy_trading_pipeline.data_ingestion.local_loader import load_local_data


FIXTURES_DIR = Path(__file__).parents[1] / "fixtures"


def test_fixture_datasets_have_expected_columns_and_small_date_range():
    prices_de = load_local_data(FIXTURES_DIR / "sample_prices_de.csv")
    prices_fr = load_local_data(FIXTURES_DIR / "sample_prices_fr.csv")
    weather = load_local_data(FIXTURES_DIR / "sample_weather.csv")

    assert list(prices_de.columns) == ["timestamp", "price_de"]
    assert list(prices_fr.columns) == ["timestamp", "price_fr"]
    assert list(weather.columns) == [
        "timestamp",
        "temperature_2m_c",
        "wind_speed_10m_m_s",
        "shortwave_radiation_w_m2",
    ]

    all_timestamps = pd.concat(
        [prices_de["timestamp"], prices_fr["timestamp"], weather["timestamp"]]
    )
    parsed_timestamps = pd.to_datetime(all_timestamps, utc=True)
    assert parsed_timestamps.max() - parsed_timestamps.min() == pd.Timedelta(days=7, hours=23)

    expected_timestamps = pd.date_range(
        "2023-01-01T00:00:00Z", periods=192, freq="h"
    )
    for dataframe in (prices_de, prices_fr, weather):
        actual_timestamps = pd.DatetimeIndex(
            pd.to_datetime(dataframe["timestamp"], utc=True).drop_duplicates()
        )
        assert actual_timestamps.equals(expected_timestamps)


def test_fixture_datasets_include_validation_cases():
    prices_de = load_local_data(FIXTURES_DIR / "sample_prices_de.csv")
    weather = load_local_data(FIXTURES_DIR / "sample_weather.csv")

    assert prices_de["timestamp"].duplicated().sum() == 1
    assert weather["temperature_2m_c"].isna().sum() == 1


def test_sample_config_references_checked_in_fixture_datasets():
    config = load_config(FIXTURES_DIR / "sample_config.yaml")

    assert config["data"] == {
        "price_de_path": "tests/fixtures/sample_prices_de.csv",
        "price_fr_path": "tests/fixtures/sample_prices_fr.csv",
        "weather_path": "tests/fixtures/sample_weather.csv",
    }
