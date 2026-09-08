"""Processed fixtures build one reproducible feature dataset artifact."""

from pathlib import Path

import pandas as pd
import pytest
import yaml

from energy_trading_pipeline.config.loader import load_config
from energy_trading_pipeline.config.paths import resolve_path
from energy_trading_pipeline.data_ingestion.local_loader import load_local_data
from energy_trading_pipeline.features.dataset_builder import (
    TARGET_COLUMN,
    save_feature_dataset,
)
from energy_trading_pipeline.preprocessing.alignment import align_hourly_data
from energy_trading_pipeline.preprocessing.cleaning import clean_records
from energy_trading_pipeline.preprocessing.spread import save_processed_data
from energy_trading_pipeline.preprocessing.timestamps import normalize_timestamps

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_CONFIG = REPO_ROOT / "tests/fixtures/sample_config.yaml"
# The fixture range is 2023-01-01 through 2023-01-08 inclusive.
PROCESSED_HOURS = 192
# features.lag_hours is [1, 24] and features.rolling_window_hours is [24], so
# the first row with a complete feature vector is the 24th hour.
WARMUP_HOURS = 24


@pytest.fixture
def processed_fixture(tmp_path):
    """Run the fixture pipeline up to the persisted processed dataset."""
    config = load_config(FIXTURE_CONFIG)
    cleaned = {}
    for source, required in (
        ("price_de", ["price_de"]),
        ("price_fr", ["price_fr"]),
        ("weather", []),
    ):
        raw = load_local_data(REPO_ROOT / config["data"][f"{source}_path"])
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

    aligned, _ = align_hourly_data(
        cleaned["price_de"],
        cleaned["price_fr"],
        weather=cleaned["weather"],
        start_date=config["dates"]["start_date"],
        end_date=config["dates"]["end_date"],
    )
    processed_path, _ = save_processed_data(
        aligned,
        tmp_path / "data/processed/aligned_hourly/prices.parquet",
        source_files={
            source: REPO_ROOT / config["data"][f"{source}_path"] for source in cleaned
        },
    )
    return config, processed_path, pd.read_parquet(processed_path)


def test_feature_dataset_is_built_from_processed_fixtures(processed_fixture, tmp_path):
    config, processed_path, processed = processed_fixture
    output_path = tmp_path / "data/features/feature_dataset.parquet"

    written, metadata_path = save_feature_dataset(
        processed,
        output_path,
        feature_config=config["features"],
        source_dataset=processed_path,
    )

    assert written.is_file() and metadata_path.is_file()
    features = pd.read_parquet(written)
    metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))

    assert len(processed) == PROCESSED_HOURS
    assert len(features) == PROCESSED_HOURS - WARMUP_HOURS
    assert metadata["incomplete_rows_dropped"] == WARMUP_HOURS
    assert features.columns.tolist() == [
        "timestamp",
        TARGET_COLUMN,
        *metadata["feature_columns"],
    ]
    assert not features.isna().any().any()
    assert features["timestamp"].is_monotonic_increasing


def test_metadata_records_the_modelling_contract(processed_fixture, tmp_path):
    config, processed_path, processed = processed_fixture

    _, metadata_path = save_feature_dataset(
        processed,
        tmp_path / "data/features/feature_dataset.parquet",
        feature_config=config["features"],
        source_dataset=processed_path,
    )
    metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))

    assert metadata["target_column"] == TARGET_COLUMN
    assert metadata["source_processed_dataset"] == str(processed_path)
    assert metadata["date_range"] == {
        "start": "2023-01-02T00:00:00+00:00",
        "end": "2023-01-08T23:00:00+00:00",
    }
    assert metadata["source_date_range"] == {
        "start": "2023-01-01T00:00:00+00:00",
        "end": "2023-01-08T23:00:00+00:00",
    }
    assert metadata["feature_config"]["lag_hours"] == config["features"]["lag_hours"]
    assert (
        metadata["feature_config"]["rolling_window_hours"]
        == config["features"]["rolling_window_hours"]
    )
    assert (
        metadata["feature_config"]["calendar_features"]
        == config["features"]["calendar_features"]
    )
    assert metadata["feature_config"]["holiday_dates"] == ["2023-01-01"]


def test_configured_features_reach_the_artifact(processed_fixture, tmp_path):
    config, processed_path, processed = processed_fixture

    written, _ = save_feature_dataset(
        processed,
        tmp_path / "data/features/feature_dataset.parquet",
        feature_config=config["features"],
        source_dataset=processed_path,
    )
    features = pd.read_parquet(written)

    for column in (
        "spread_lag_1",
        "spread_lag_24",
        "spread_rolling_mean_24",
        "spread_rolling_std_24",
        "hour",
        "day_of_week",
        "month",
        "is_weekend",
        "is_holiday",
        # Retained by alignment from the weather fixture.
        "wind_speed_10m_m_s",
        "shortwave_radiation_w_m2",
    ):
        assert column in features.columns
    # The market prices are the target at their own timestamp.
    for column in ("price_de", "price_fr"):
        assert column not in features.columns


def test_unavailable_optional_variables_do_not_block_the_build(
    processed_fixture, tmp_path
):
    config, processed_path, processed = processed_fixture

    _, metadata_path = save_feature_dataset(
        processed,
        tmp_path / "data/features/feature_dataset.parquet",
        feature_config=config["features"],
        source_dataset=processed_path,
    )
    metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))

    # temperature_2m_c has missing fixture hours and is excluded by alignment;
    # load_de is requested by the fixture config but was never ingested.
    assert metadata["feature_stages"]["weather"]["missing_columns"] == [
        "temperature_2m_c"
    ]
    assert metadata["feature_stages"]["grid"]["missing_columns"] == ["load_de"]
    assert metadata["feature_stages"]["grid"]["selected_columns"] == []
    assert "temperature_2m_c" not in metadata["feature_columns"]
    assert "load_de" not in metadata["feature_columns"]


def test_build_is_reproducible_from_the_same_processed_data_and_config(
    processed_fixture, tmp_path
):
    config, processed_path, processed = processed_fixture

    first, first_metadata_path = save_feature_dataset(
        processed,
        tmp_path / "first/feature_dataset.parquet",
        feature_config=config["features"],
        source_dataset=processed_path,
    )
    second, second_metadata_path = save_feature_dataset(
        processed,
        tmp_path / "second/feature_dataset.parquet",
        feature_config=config["features"],
        source_dataset=processed_path,
    )

    pd.testing.assert_frame_equal(pd.read_parquet(first), pd.read_parquet(second))
    first_metadata = yaml.safe_load(first_metadata_path.read_text(encoding="utf-8"))
    second_metadata = yaml.safe_load(second_metadata_path.read_text(encoding="utf-8"))
    first_metadata.pop("artifact_paths")
    second_metadata.pop("artifact_paths")
    assert first_metadata == second_metadata


def test_configured_feature_dataset_path_is_the_canonical_artifact():
    paths_config = yaml.safe_load(
        (REPO_ROOT / "configs/local_paths.yaml").read_text(encoding="utf-8")
    )

    resolved = resolve_path(REPO_ROOT, paths_config["feature_data_parquet_path"])

    assert resolved == REPO_ROOT / "data/features/feature_dataset.parquet"
