"""Leakage-safe lag feature generation for spread and price columns."""

import numpy as np
import pandas as pd
import pytest

from energy_trading_pipeline.features.lag_features import (
    DEFAULT_LAG_SOURCE_COLUMNS,
    INSUFFICIENT_HISTORY_POLICY,
    build_lag_features,
)


@pytest.fixture
def processed_hourly():
    """Six contiguous UTC hours with distinct, easily traceable values."""
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2023-01-01", periods=6, freq="h", tz="UTC"),
            "price_de": [10.0, 11.0, 12.0, 13.0, 14.0, 15.0],
            "price_fr": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "spread": [9.0, 9.0, 9.0, 9.0, 9.0, 9.0],
            "load_de": [100.0, 110.0, 120.0, 130.0, 140.0, 150.0],
        }
    )


def test_lag_values_are_shifted_by_the_configured_hours(processed_hourly):
    result, _ = build_lag_features(processed_hourly, lag_hours=[1, 3])

    nan = np.nan
    assert result["price_de_lag_1"].tolist() == pytest.approx(
        [nan, 10.0, 11.0, 12.0, 13.0, 14.0], nan_ok=True
    )
    assert result["price_de_lag_3"].tolist() == pytest.approx(
        [nan, nan, nan, 10.0, 11.0, 12.0], nan_ok=True
    )
    assert result["price_fr_lag_1"].tolist() == pytest.approx(
        [nan, 1.0, 2.0, 3.0, 4.0, 5.0], nan_ok=True
    )
    assert result["spread_lag_3"].tolist() == pytest.approx(
        [nan, nan, nan, 9.0, 9.0, 9.0], nan_ok=True
    )


def test_generated_columns_follow_snake_case_and_are_appended_in_order(
    processed_hourly,
):
    result, metadata = build_lag_features(processed_hourly, lag_hours=[24, 1])

    expected = [
        "spread_lag_1",
        "spread_lag_24",
        "price_de_lag_1",
        "price_de_lag_24",
        "price_fr_lag_1",
        "price_fr_lag_24",
    ]
    assert metadata["generated_columns"] == expected
    assert result.columns.tolist() == processed_hourly.columns.tolist() + expected
    assert all(column == column.lower() and " " not in column for column in expected)


def test_current_timestamp_value_never_feeds_its_own_lag(processed_hourly):
    baseline, _ = build_lag_features(processed_hourly, lag_hours=[1, 2])
    perturbed_input = processed_hourly.copy()
    perturbed_input.loc[3, ["price_de", "price_fr", "spread"]] = [999.0, -999.0, 1998.0]
    perturbed, _ = build_lag_features(perturbed_input, lag_hours=[1, 2])

    lag_columns = [column for column in baseline.columns if "_lag_" in column]
    pd.testing.assert_frame_equal(
        baseline.loc[[3], lag_columns], perturbed.loc[[3], lag_columns]
    )
    # The perturbed value appears only at strictly later timestamps.
    assert perturbed.loc[4, "price_de_lag_1"] == 999.0
    assert perturbed.loc[5, "price_de_lag_2"] == 999.0


def test_rows_without_sufficient_history_are_retained_with_null_lags(
    processed_hourly,
):
    result, metadata = build_lag_features(processed_hourly, lag_hours=[2, 4])

    assert len(result) == len(processed_hourly)
    lag_columns = metadata["generated_columns"]
    assert result.loc[:1, lag_columns].isna().all().all()
    assert result.loc[4:, lag_columns].notna().all().all()
    assert metadata["insufficient_history_policy"] == INSUFFICIENT_HISTORY_POLICY
    assert metadata["min_history_hours"] == 4
    assert metadata["incomplete_history_rows"] == 4


def test_metadata_records_configuration_and_generated_columns(processed_hourly):
    _, metadata = build_lag_features(processed_hourly, lag_hours=[1, 24])

    assert metadata["stage"] == "features.lag"
    assert metadata["lag_hours"] == [1, 24]
    assert metadata["source_columns"] == list(DEFAULT_LAG_SOURCE_COLUMNS)
    assert metadata["generated_columns"] == [
        "spread_lag_1",
        "spread_lag_24",
        "price_de_lag_1",
        "price_de_lag_24",
        "price_fr_lag_1",
        "price_fr_lag_24",
    ]
    assert metadata["output_rows"] == 6


def test_duplicate_lags_are_deduplicated_and_sorted(processed_hourly):
    _, metadata = build_lag_features(processed_hourly, lag_hours=[24, 1, 24])
    assert metadata["lag_hours"] == [1, 24]
    assert metadata["generated_columns"].count("spread_lag_24") == 1


def test_input_is_not_mutated_and_existing_columns_are_preserved(processed_hourly):
    original = processed_hourly.copy(deep=True)
    result, _ = build_lag_features(processed_hourly, lag_hours=[1])

    pd.testing.assert_frame_equal(processed_hourly, original)
    pd.testing.assert_frame_equal(result[original.columns], original)


def test_unsorted_input_is_lagged_in_chronological_order(processed_hourly):
    shuffled = processed_hourly.iloc[[3, 0, 5, 1, 4, 2]]
    result, _ = build_lag_features(shuffled, lag_hours=[1])

    assert result["timestamp"].is_monotonic_increasing
    assert result.index.tolist() == list(range(6))
    assert result["price_fr_lag_1"].tolist() == pytest.approx(
        [np.nan, 1.0, 2.0, 3.0, 4.0, 5.0], nan_ok=True
    )


def test_non_utc_aware_timestamps_are_normalized(processed_hourly):
    processed_hourly["timestamp"] = processed_hourly["timestamp"].dt.tz_convert(
        "Europe/Paris"
    )
    result, _ = build_lag_features(processed_hourly, lag_hours=[1])
    assert str(result["timestamp"].dt.tz) == "UTC"


def test_existing_lag_columns_are_recomputed(processed_hourly):
    processed_hourly["spread_lag_1"] = 12345.0
    result, _ = build_lag_features(processed_hourly, lag_hours=[1])
    assert result["spread_lag_1"].tolist()[1:] == [9.0] * 5
    assert result.columns.tolist().count("spread_lag_1") == 1


@pytest.mark.parametrize("lag_hours", [[], [0], [-1], [1.5], ["1"], [True], None, 24])
def test_invalid_lag_hours_fail(processed_hourly, lag_hours):
    with pytest.raises(ValueError, match="lag_hours"):
        build_lag_features(processed_hourly, lag_hours=lag_hours)


@pytest.mark.parametrize("column", ["timestamp", "price_de", "price_fr", "spread"])
def test_missing_required_columns_fail(processed_hourly, column):
    with pytest.raises(ValueError, match="Missing required columns"):
        build_lag_features(processed_hourly.drop(columns=column), lag_hours=[1])


def test_custom_source_columns_are_supported(processed_hourly):
    result, metadata = build_lag_features(
        processed_hourly, lag_hours=[1], columns=["load_de"]
    )
    assert metadata["generated_columns"] == ["load_de_lag_1"]
    assert result["load_de_lag_1"].tolist()[1:] == [100.0, 110.0, 120.0, 130.0, 140.0]


@pytest.mark.parametrize("columns", [[], ["missing"], ["timestamp"]])
def test_invalid_source_columns_fail(processed_hourly, columns):
    with pytest.raises(ValueError):
        build_lag_features(processed_hourly, lag_hours=[1], columns=columns)


@pytest.mark.parametrize("problem", ["empty", "duplicate", "gap", "off_hour", "naive"])
def test_non_contiguous_hourly_data_fails(processed_hourly, problem):
    if problem == "empty":
        processed_hourly = processed_hourly.iloc[:0]
    elif problem == "duplicate":
        processed_hourly.loc[1, "timestamp"] = processed_hourly.loc[0, "timestamp"]
    elif problem == "gap":
        processed_hourly = processed_hourly.drop(index=2)
    elif problem == "off_hour":
        processed_hourly["timestamp"] += pd.Timedelta(minutes=30)
    else:
        processed_hourly["timestamp"] = processed_hourly["timestamp"].dt.tz_localize(
            None
        )
    with pytest.raises(ValueError):
        build_lag_features(processed_hourly, lag_hours=[1])


def test_non_numeric_source_column_fails(processed_hourly):
    processed_hourly["spread"] = "text"
    with pytest.raises(ValueError, match="spread"):
        build_lag_features(processed_hourly, lag_hours=[1])


def test_lag_longer_than_history_yields_all_nulls_and_is_reported(processed_hourly):
    result, metadata = build_lag_features(processed_hourly, lag_hours=[24])
    assert result["spread_lag_24"].isna().all()
    assert metadata["incomplete_history_rows"] == 6


def test_duplicate_input_columns_fail(processed_hourly):
    duplicate = pd.concat([processed_hourly, processed_hourly[["spread"]]], axis=1)
    with pytest.raises(ValueError, match="Duplicate column names"):
        build_lag_features(duplicate, lag_hours=[1])
