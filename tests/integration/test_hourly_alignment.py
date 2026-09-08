"""Local fixtures flow through normalization, cleaning, and hourly alignment."""

from pathlib import Path

import pandas as pd

from energy_trading_pipeline.config.loader import load_config
from energy_trading_pipeline.data_ingestion.local_loader import load_local_data
from energy_trading_pipeline.preprocessing.alignment import align_hourly_data
from energy_trading_pipeline.preprocessing.cleaning import clean_records
from energy_trading_pipeline.preprocessing.timestamps import normalize_timestamps


def test_align_local_price_and_weather_fixtures(tmp_path):
    root = Path(__file__).resolve().parents[2]
    config = load_config(root / "tests/fixtures/sample_config.yaml")
    cleaned = {}
    for source, required in (
        ("price_de", ["price_de"]),
        ("price_fr", ["price_fr"]),
        ("weather", []),
    ):
        raw = load_local_data(root / config["data"][f"{source}_path"])
        normalized, _ = normalize_timestamps(raw)
        cleaned[source], _ = clean_records(
            normalized,
            required_columns=required,
            optional_columns=[],
            duplicate_policy="keep_first",
            required_missing_policy="raise",
            run_dir=tmp_path / "run_20260908_120000",
            dataset=source,
        )

    result, report = align_hourly_data(
        cleaned["price_de"],
        cleaned["price_fr"],
        weather=cleaned["weather"],
        start_date=config["dates"]["start_date"],
        end_date=config["dates"]["end_date"],
    )

    expected = pd.date_range("2023-01-01", "2023-01-08 23:00", freq="h", tz="UTC")
    pd.testing.assert_index_equal(
        pd.DatetimeIndex(result["timestamp"]), expected, check_names=False
    )
    assert len(result) == 192
    assert result.columns.tolist() == [
        "timestamp",
        "price_de",
        "price_fr",
        "wind_speed_10m_m_s",
        "shortwave_radiation_w_m2",
    ]
    assert not result.isna().any().any()
    for source in cleaned.values():
        for column in source.columns.drop("timestamp"):
            pd.testing.assert_series_equal(result[column], source[column])
    assert report["output_rows"] == 192
