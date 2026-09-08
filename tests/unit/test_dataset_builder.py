"""Canonical feature dataset assembly from processed hourly data and config."""

import logging

import pandas as pd
import pytest
import yaml

from energy_trading_pipeline.features.dataset_builder import (
    FEATURE_STAGE_ORDER,
    INCOMPLETE_ROW_POLICY,
    NON_FEATURE_COLUMNS,
    TARGET_COLUMN,
    build_feature_dataset,
    save_feature_dataset,
)

HOURS = 48
SOURCE_DATASET = "data/processed/aligned_hourly/prices.parquet"
FEATURE_CONFIG = {
    "lag_hours": [1, 2],
    "rolling_window_hours": [3],
    "calendar_features": ["hour", "is_weekend"],
    "holiday_dates": [],
    "weather_columns": ["temperature_2m_c", "shortwave_radiation_w_m2"],
    "grid_columns": ["load_de"],
}
# The first row with a complete feature vector is at index
# max(max lag, max rolling window), because a shifted window of w hours ends at
# the previous hour and so first completes at row w.
EXPECTED_WARMUP_HOURS = 3


@pytest.fixture
def processed_hourly():
    """Two contiguous UTC days of processed prices, spread, and exogenous data."""
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2023-01-01", periods=HOURS, freq="h", tz="UTC"),
            "price_de": [50.0 + index for index in range(HOURS)],
            "price_fr": [40.0 + 0.5 * index for index in range(HOURS)],
            "spread": [10.0 + 0.5 * index for index in range(HOURS)],
            "temperature_2m_c": [1.5 + index for index in range(HOURS)],
            "load_de": [100.0 + index for index in range(HOURS)],
        }
    )


def build(df, feature_config=None):
    """Build the feature dataset under the shared fixture provenance."""
    return build_feature_dataset(
        df,
        FEATURE_CONFIG if feature_config is None else feature_config,
        source_dataset=SOURCE_DATASET,
    )


def test_dataset_holds_timestamp_target_and_feature_columns_only(processed_hourly):
    result, metadata = build(processed_hourly)

    assert result.columns.tolist() == [
        "timestamp",
        TARGET_COLUMN,
        *metadata["feature_columns"],
    ]


def test_contemporaneous_prices_are_not_features(processed_hourly):
    result, metadata = build(processed_hourly)

    for column in ("price_de", "price_fr"):
        assert column not in result.columns
        assert column not in metadata["feature_columns"]
    assert metadata["excluded_columns"] == ["timestamp", "price_de", "price_fr"]
    assert TARGET_COLUMN not in metadata["feature_columns"]


def test_feature_columns_follow_the_fixed_stage_order(processed_hourly):
    _, metadata = build(processed_hourly)

    assert metadata["feature_columns"] == [
        "spread_lag_1",
        "spread_lag_2",
        "price_de_lag_1",
        "price_de_lag_2",
        "price_fr_lag_1",
        "price_fr_lag_2",
        "spread_rolling_mean_3",
        "spread_rolling_std_3",
        "price_de_rolling_mean_3",
        "price_de_rolling_std_3",
        "price_fr_rolling_mean_3",
        "price_fr_rolling_std_3",
        "hour",
        "is_weekend",
        "temperature_2m_c",
        "load_de",
    ]
    assert list(metadata["feature_stages"]) == list(FEATURE_STAGE_ORDER)


def test_every_feature_column_uses_snake_case(processed_hourly):
    _, metadata = build(processed_hourly)

    for column in metadata["feature_columns"]:
        assert column == column.lower()
        assert " " not in column and "-" not in column


def test_incomplete_warmup_rows_are_dropped(processed_hourly):
    result, metadata = build(processed_hourly)

    assert metadata["incomplete_rows_dropped"] == EXPECTED_WARMUP_HOURS
    assert metadata["incomplete_row_policy"] == INCOMPLETE_ROW_POLICY
    assert metadata["source_rows"] == HOURS
    assert metadata["output_rows"] == HOURS - EXPECTED_WARMUP_HOURS
    assert len(result) == HOURS - EXPECTED_WARMUP_HOURS


def test_every_retained_row_has_a_complete_feature_vector(processed_hourly):
    result, _ = build(processed_hourly)

    assert not result.isna().any().any()


def test_rows_stay_chronological_after_dropping_warmup_rows(processed_hourly):
    result, _ = build(processed_hourly)

    assert result["timestamp"].is_monotonic_increasing
    assert result["timestamp"].iloc[0] == processed_hourly["timestamp"].iloc[
        EXPECTED_WARMUP_HOURS
    ]
    assert result.index.tolist() == list(range(len(result)))


def test_lag_features_align_with_the_source_rows(processed_hourly):
    result, _ = build(processed_hourly)

    merged = result.merge(
        processed_hourly[["timestamp", TARGET_COLUMN]].assign(
            expected_lag_1=processed_hourly[TARGET_COLUMN].shift(1)
        ),
        on="timestamp",
        suffixes=("", "_source"),
    )
    assert merged["spread_lag_1"].tolist() == merged["expected_lag_1"].tolist()


def test_metadata_records_the_target_and_source_provenance(processed_hourly):
    _, metadata = build(processed_hourly)

    assert metadata["stage"] == "features.dataset"
    assert metadata["target_column"] == TARGET_COLUMN
    assert metadata["source_processed_dataset"] == SOURCE_DATASET
    assert metadata["timezone"] == "UTC"


def test_metadata_records_the_retained_and_source_date_ranges(processed_hourly):
    result, metadata = build(processed_hourly)

    assert metadata["date_range"] == {
        "start": result["timestamp"].iloc[0].isoformat(),
        "end": result["timestamp"].iloc[-1].isoformat(),
    }
    assert metadata["source_date_range"] == {
        "start": processed_hourly["timestamp"].iloc[0].isoformat(),
        "end": processed_hourly["timestamp"].iloc[-1].isoformat(),
    }


def test_metadata_records_the_applied_feature_config(processed_hourly):
    _, metadata = build(processed_hourly)

    assert metadata["feature_config"] == {
        "lag_hours": [1, 2],
        "lag_columns": ["spread", "price_de", "price_fr"],
        "rolling_window_hours": [3],
        "rolling_columns": ["spread", "price_de", "price_fr"],
        "calendar_features": ["hour", "is_weekend"],
        "holiday_dates": [],
        "weather_columns": [
            "temperature_2m_c",
            "shortwave_radiation_w_m2",
        ],
        "grid_columns": ["load_de"],
    }


def test_metadata_retains_each_stage_report(processed_hourly):
    _, metadata = build(processed_hourly)

    assert metadata["feature_stages"]["lag"]["stage"] == "features.lag"
    assert metadata["feature_stages"]["rolling"]["shift_hours"] == 1
    assert metadata["feature_stages"]["calendar"]["generated_columns"] == [
        "hour",
        "is_weekend",
    ]
    assert metadata["feature_stages"]["weather"]["missing_columns"] == [
        "shortwave_radiation_w_m2"
    ]
    assert metadata["feature_stages"]["grid"]["selected_columns"] == ["load_de"]


def test_build_is_deterministic_from_processed_data_and_config(processed_hourly):
    first, first_metadata = build(processed_hourly)
    second, second_metadata = build(processed_hourly)

    pd.testing.assert_frame_equal(first, second)
    assert first_metadata == second_metadata


def test_unsorted_processed_input_produces_the_same_dataset(processed_hourly):
    shuffled = processed_hourly.iloc[::-1].reset_index(drop=True)

    result, _ = build(shuffled)
    expected, _ = build(processed_hourly)

    pd.testing.assert_frame_equal(result, expected)


def test_input_dataframe_is_not_mutated(processed_hourly):
    original = processed_hourly.copy(deep=True)

    build(processed_hourly)

    pd.testing.assert_frame_equal(processed_hourly, original)


def test_unavailable_optional_variables_do_not_block_the_build(
    processed_hourly, caplog
):
    caplog.set_level(logging.WARNING)
    prices_only = processed_hourly.drop(columns=["temperature_2m_c", "load_de"])

    result, metadata = build(prices_only)

    assert "temperature_2m_c" not in metadata["feature_columns"]
    assert "load_de" not in metadata["feature_columns"]
    assert metadata["feature_stages"]["weather"]["selected_columns"] == []
    assert metadata["feature_stages"]["grid"]["selected_columns"] == []
    assert len(result) == HOURS - EXPECTED_WARMUP_HOURS
    assert "temperature_2m_c" in caplog.text


def test_absent_optional_config_keys_request_no_exogenous_features(processed_hourly):
    _, metadata = build(
        processed_hourly, {"lag_hours": [1], "rolling_window_hours": [2]}
    )

    assert metadata["feature_config"]["weather_columns"] == []
    assert metadata["feature_config"]["grid_columns"] == []
    assert metadata["feature_config"]["calendar_features"] == [
        "hour",
        "day_of_week",
        "month",
        "is_weekend",
    ]
    assert "temperature_2m_c" not in metadata["feature_columns"]


def test_unknown_feature_config_keys_warn(processed_hourly, caplog):
    caplog.set_level(logging.WARNING)

    build(processed_hourly, {**FEATURE_CONFIG, "calender_features": ["hour"]})

    assert "calender_features" in caplog.text


@pytest.mark.parametrize("key", ["lag_hours", "rolling_window_hours"])
def test_missing_required_feature_config_keys_are_rejected(processed_hourly, key):
    feature_config = {
        name: value for name, value in FEATURE_CONFIG.items() if name != key
    }

    with pytest.raises(ValueError, match="Missing required feature config key"):
        build(processed_hourly, feature_config)


@pytest.mark.parametrize("feature_config", [None, [], "features"])
def test_invalid_feature_config_is_rejected(processed_hourly, feature_config):
    with pytest.raises(ValueError, match="must be the 'features' mapping"):
        build_feature_dataset(
            processed_hourly, feature_config, source_dataset=SOURCE_DATASET
        )


def test_missing_target_column_is_rejected(processed_hourly):
    with pytest.raises(ValueError, match="target column"):
        build(processed_hourly.drop(columns=[TARGET_COLUMN]))


@pytest.mark.parametrize("source_dataset", ["", "   "])
def test_missing_source_provenance_is_rejected(processed_hourly, source_dataset):
    with pytest.raises(ValueError, match="source_dataset"):
        build_feature_dataset(
            processed_hourly, FEATURE_CONFIG, source_dataset=source_dataset
        )


def test_too_little_history_fails_clearly(processed_hourly):
    short = processed_hourly.iloc[:3].reset_index(drop=True)

    with pytest.raises(ValueError, match="complete feature vector"):
        build(short, {"lag_hours": [24], "rolling_window_hours": [24]})


def test_non_feature_columns_are_the_market_and_target_columns():
    assert NON_FEATURE_COLUMNS == ("timestamp", "price_de", "price_fr", "spread")


def test_save_writes_parquet_and_a_metadata_sidecar(processed_hourly, tmp_path):
    output_path = tmp_path / "data/features/feature_dataset.parquet"

    written, metadata_path = save_feature_dataset(
        processed_hourly,
        output_path,
        feature_config=FEATURE_CONFIG,
        source_dataset=SOURCE_DATASET,
    )

    assert written == output_path
    assert metadata_path == output_path.with_suffix(".metadata.yaml")
    assert written.is_file() and metadata_path.is_file()

    expected, expected_metadata = build(processed_hourly)
    pd.testing.assert_frame_equal(pd.read_parquet(written), expected)

    metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
    assert metadata["target_column"] == TARGET_COLUMN
    assert metadata["feature_columns"] == expected_metadata["feature_columns"]
    assert metadata["source_processed_dataset"] == SOURCE_DATASET
    assert metadata["date_range"] == expected_metadata["date_range"]
    assert metadata["feature_config"] == expected_metadata["feature_config"]
    assert metadata["artifact_paths"] == {
        "feature_dataset": str(output_path),
        "metadata": str(metadata_path),
    }


def test_save_replaces_existing_artifacts(processed_hourly, tmp_path):
    output_path = tmp_path / "feature_dataset.parquet"
    save_feature_dataset(
        processed_hourly,
        output_path,
        feature_config=FEATURE_CONFIG,
        source_dataset=SOURCE_DATASET,
    )

    save_feature_dataset(
        processed_hourly.iloc[: HOURS - 1],
        output_path,
        feature_config=FEATURE_CONFIG,
        source_dataset=SOURCE_DATASET,
    )

    assert len(pd.read_parquet(output_path)) == HOURS - 1 - EXPECTED_WARMUP_HOURS


def test_save_rejects_a_non_parquet_output_path(processed_hourly, tmp_path):
    with pytest.raises(ValueError, match=".parquet suffix"):
        save_feature_dataset(
            processed_hourly,
            tmp_path / "feature_dataset.csv",
            feature_config=FEATURE_CONFIG,
            source_dataset=SOURCE_DATASET,
        )


def test_save_does_not_write_anything_when_the_build_fails(
    processed_hourly, tmp_path
):
    output_path = tmp_path / "data/features/feature_dataset.parquet"

    with pytest.raises(ValueError):
        save_feature_dataset(
            processed_hourly,
            output_path,
            feature_config={"lag_hours": [1]},
            source_dataset=SOURCE_DATASET,
        )

    assert not output_path.exists()
    assert not output_path.parent.exists()
