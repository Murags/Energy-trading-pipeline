"""Leakage-safe rolling feature generation for spread and price columns."""

from statistics import fmean, stdev

import numpy as np
import pandas as pd
import pytest

from energy_trading_pipeline.features.rolling_features import (
    DEFAULT_ROLLING_SOURCE_COLUMNS,
    INSUFFICIENT_WINDOW_POLICY,
    MIN_ROLLING_WINDOW_HOURS,
    ROLLING_SHIFT_HOURS,
    ROLLING_STATISTICS,
    build_rolling_features,
    rolling_column_name,
)

PRICE_DE = [10.0, 11.0, 13.0, 16.0, 20.0, 25.0, 31.0, 38.0]
PRICE_FR = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
SPREAD = [de - fr for de, fr in zip(PRICE_DE, PRICE_FR)]


@pytest.fixture
def processed_hourly():
    """Eight contiguous UTC hours with strictly increasing, traceable values."""
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2023-01-01", periods=8, freq="h", tz="UTC"),
            "price_de": PRICE_DE,
            "price_fr": PRICE_FR,
            "spread": SPREAD,
            "load_de": [100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0, 170.0],
        }
    )


def expected_trailing(values, window, statistic):
    """Reference values from the ``window`` hours strictly before each row.

    Deliberately independent of pandas: each row aggregates the plain Python
    slice ``values[i - window : i]``, which excludes the row's own value.
    """
    aggregate = fmean if statistic == "mean" else stdev
    return [
        np.nan if index < window else aggregate(values[index - window : index])
        for index in range(len(values))
    ]


def test_rolling_means_aggregate_only_the_hours_before_each_row(processed_hourly):
    result, _ = build_rolling_features(processed_hourly, window_hours=[2, 3])

    for window in (2, 3):
        assert result[f"price_de_rolling_mean_{window}"].tolist() == pytest.approx(
            expected_trailing(PRICE_DE, window, "mean"), nan_ok=True
        )
        assert result[f"price_fr_rolling_mean_{window}"].tolist() == pytest.approx(
            expected_trailing(PRICE_FR, window, "mean"), nan_ok=True
        )
        assert result[f"spread_rolling_mean_{window}"].tolist() == pytest.approx(
            expected_trailing(SPREAD, window, "mean"), nan_ok=True
        )


def test_rolling_standard_deviations_aggregate_only_the_hours_before_each_row(
    processed_hourly,
):
    result, _ = build_rolling_features(processed_hourly, window_hours=[2, 3])

    for window in (2, 3):
        assert result[f"price_de_rolling_std_{window}"].tolist() == pytest.approx(
            expected_trailing(PRICE_DE, window, "std"), nan_ok=True
        )
        assert result[f"spread_rolling_std_{window}"].tolist() == pytest.approx(
            expected_trailing(SPREAD, window, "std"), nan_ok=True
        )


def test_first_valid_window_uses_the_earliest_rows_and_not_the_current_row(
    processed_hourly,
):
    result, _ = build_rolling_features(processed_hourly, window_hours=[3])

    # Row 3 must summarise rows 0-2 only (10, 11, 13), never its own 16.
    assert result.loc[2, "price_de_rolling_mean_3"] is not None
    assert np.isnan(result.loc[2, "price_de_rolling_mean_3"])
    assert result.loc[3, "price_de_rolling_mean_3"] == pytest.approx(
        fmean([10.0, 11.0, 13.0])
    )
    assert result.loc[3, "price_de_rolling_std_3"] == pytest.approx(
        stdev([10.0, 11.0, 13.0])
    )


def test_window_is_shifted_so_the_current_value_is_excluded(processed_hourly):
    """A shifted window differs from an unshifted one; assert we use the shift."""
    result, metadata = build_rolling_features(processed_hourly, window_hours=[3])

    unshifted_row_3 = fmean([11.0, 13.0, 16.0])
    assert result.loc[3, "price_de_rolling_mean_3"] != pytest.approx(unshifted_row_3)
    assert metadata["shift_hours"] == ROLLING_SHIFT_HOURS == 1


def test_generated_column_names_include_the_window_size(processed_hourly):
    _, metadata = build_rolling_features(processed_hourly, window_hours=[2, 24])

    for name in metadata["generated_columns"]:
        assert name.endswith(("_2", "_24"))
        assert "_rolling_mean_" in name or "_rolling_std_" in name


def test_generated_columns_follow_snake_case_and_are_appended_in_order(
    processed_hourly,
):
    result, metadata = build_rolling_features(processed_hourly, window_hours=[24, 2])

    expected = [
        "spread_rolling_mean_2",
        "spread_rolling_std_2",
        "spread_rolling_mean_24",
        "spread_rolling_std_24",
        "price_de_rolling_mean_2",
        "price_de_rolling_std_2",
        "price_de_rolling_mean_24",
        "price_de_rolling_std_24",
        "price_fr_rolling_mean_2",
        "price_fr_rolling_std_2",
        "price_fr_rolling_mean_24",
        "price_fr_rolling_std_24",
    ]
    assert metadata["generated_columns"] == expected
    assert result.columns.tolist() == processed_hourly.columns.tolist() + expected
    assert all(column == column.lower() and " " not in column for column in expected)


def test_rolling_column_name_builds_the_canonical_identifier():
    assert rolling_column_name("spread", "mean", 24) == "spread_rolling_mean_24"
    assert rolling_column_name("price_de", "std", 3) == "price_de_rolling_std_3"


def test_current_timestamp_value_never_feeds_its_own_rolling_features(
    processed_hourly,
):
    baseline, _ = build_rolling_features(processed_hourly, window_hours=[2, 3])
    perturbed_input = processed_hourly.copy()
    perturbed_input.loc[4, ["price_de", "price_fr", "spread"]] = [999.0, -999.0, 1998.0]
    perturbed, _ = build_rolling_features(perturbed_input, window_hours=[2, 3])

    rolling_columns = [c for c in baseline.columns if "_rolling_" in c]
    pd.testing.assert_frame_equal(
        baseline.loc[[4], rolling_columns], perturbed.loc[[4], rolling_columns]
    )
    # The perturbed value may only surface at strictly later timestamps: row 5
    # summarises rows 3 and 4, so it picks up the perturbation, row 4 does not.
    assert perturbed.loc[5, "price_de_rolling_mean_2"] == pytest.approx(
        fmean([PRICE_DE[3], 999.0])
    )


def test_future_values_never_feed_earlier_rolling_features(processed_hourly):
    baseline, _ = build_rolling_features(processed_hourly, window_hours=[2, 3])
    perturbed_input = processed_hourly.copy()
    perturbed_input.loc[6:, ["price_de", "price_fr", "spread"]] = 1234.0
    perturbed, _ = build_rolling_features(perturbed_input, window_hours=[2, 3])

    rolling_columns = [c for c in baseline.columns if "_rolling_" in c]
    # Rows 0-6 are computed from hours strictly before row 6, so nothing changes.
    pd.testing.assert_frame_equal(
        baseline.loc[:6, rolling_columns], perturbed.loc[:6, rolling_columns]
    )
    assert perturbed.loc[7, "price_de_rolling_mean_2"] != pytest.approx(
        baseline.loc[7, "price_de_rolling_mean_2"]
    )


def test_rows_without_a_full_window_are_retained_with_null_features(processed_hourly):
    result, metadata = build_rolling_features(processed_hourly, window_hours=[3])

    assert len(result) == len(processed_hourly)
    rolling_columns = [c for c in result.columns if "_rolling_" in c]
    assert result.loc[:2, rolling_columns].isna().all().all()
    assert result.loc[3:, rolling_columns].notna().all().all()
    assert metadata["insufficient_window_policy"] == INSUFFICIENT_WINDOW_POLICY
    assert metadata["min_history_hours"] == 3
    assert metadata["incomplete_window_rows"] == 3


def test_partial_windows_are_never_aggregated(processed_hourly):
    """Consistency: a partial window yields null, not a shorter-window value."""
    result, _ = build_rolling_features(processed_hourly, window_hours=[4])

    assert result.loc[3, "price_de_rolling_mean_4"] != pytest.approx(
        fmean([10.0, 11.0, 13.0])
    ) or np.isnan(result.loc[3, "price_de_rolling_mean_4"])
    assert np.isnan(result.loc[3, "price_de_rolling_mean_4"])


def test_incomplete_window_rows_never_exceed_the_row_count():
    short = pd.DataFrame(
        {
            "timestamp": pd.date_range("2023-01-01", periods=2, freq="h", tz="UTC"),
            "price_de": [10.0, 11.0],
            "price_fr": [1.0, 2.0],
            "spread": [9.0, 9.0],
        }
    )

    result, metadata = build_rolling_features(short, window_hours=[24])

    assert metadata["incomplete_window_rows"] == 2
    assert metadata["output_rows"] == 2
    assert result.filter(like="_rolling_").isna().all().all()


def test_metadata_describes_the_generated_rolling_features(processed_hourly):
    _, metadata = build_rolling_features(processed_hourly, window_hours=[3, 2])

    assert metadata["stage"] == "features.rolling"
    assert metadata["source_columns"] == list(DEFAULT_ROLLING_SOURCE_COLUMNS)
    assert metadata["window_hours"] == [2, 3]
    assert metadata["statistics"] == list(ROLLING_STATISTICS) == ["mean", "std"]
    assert metadata["shift_hours"] == 1
    assert metadata["std_ddof"] == 1
    assert metadata["min_history_hours"] == 3
    assert metadata["incomplete_window_rows"] == 3
    assert metadata["output_rows"] == 8
    assert len(metadata["generated_columns"]) == 12


def test_windows_are_sorted_and_de_duplicated(processed_hourly):
    _, metadata = build_rolling_features(processed_hourly, window_hours=[3, 2, 3])

    assert metadata["window_hours"] == [2, 3]
    assert len(metadata["generated_columns"]) == 12


def test_source_columns_can_be_overridden(processed_hourly):
    result, metadata = build_rolling_features(
        processed_hourly, window_hours=[2], columns=["load_de"]
    )

    assert metadata["source_columns"] == ["load_de"]
    assert metadata["generated_columns"] == [
        "load_de_rolling_mean_2",
        "load_de_rolling_std_2",
    ]
    assert "spread_rolling_mean_2" not in result.columns


def test_input_dataframe_is_not_mutated(processed_hourly):
    before = processed_hourly.copy(deep=True)

    build_rolling_features(processed_hourly, window_hours=[2])

    pd.testing.assert_frame_equal(processed_hourly, before)


def test_unsorted_input_is_ordered_chronologically_before_aggregation(
    processed_hourly,
):
    shuffled = processed_hourly.iloc[[4, 0, 7, 2, 5, 1, 6, 3]].reset_index(drop=True)

    result, _ = build_rolling_features(shuffled, window_hours=[3])
    expected, _ = build_rolling_features(processed_hourly, window_hours=[3])

    assert result["timestamp"].is_monotonic_increasing
    pd.testing.assert_frame_equal(result, expected)


def test_timestamps_are_normalised_to_utc(processed_hourly):
    localised = processed_hourly.copy()
    localised["timestamp"] = localised["timestamp"].dt.tz_convert("Europe/Berlin")

    result, _ = build_rolling_features(localised, window_hours=[3])
    expected, _ = build_rolling_features(processed_hourly, window_hours=[3])

    assert str(result["timestamp"].dt.tz) == "UTC"
    pd.testing.assert_frame_equal(result, expected)


def test_existing_rolling_columns_are_recomputed_not_duplicated(processed_hourly):
    stale = processed_hourly.copy()
    stale["spread_rolling_mean_3"] = -1.0

    result, metadata = build_rolling_features(stale, window_hours=[3])

    assert result.columns.tolist().count("spread_rolling_mean_3") == 1
    assert result["spread_rolling_mean_3"].tolist() == pytest.approx(
        expected_trailing(SPREAD, 3, "mean"), nan_ok=True
    )
    assert result.columns.tolist()[-len(metadata["generated_columns"]) :] == (
        metadata["generated_columns"]
    )


def test_null_source_values_propagate_instead_of_shrinking_the_window(
    processed_hourly,
):
    gapped = processed_hourly.copy()
    gapped.loc[1, "price_de"] = np.nan

    result, _ = build_rolling_features(gapped, window_hours=[2])

    # Windows covering the null hour cannot be completed.
    assert np.isnan(result.loc[2, "price_de_rolling_mean_2"])
    assert np.isnan(result.loc[3, "price_de_rolling_mean_2"])
    assert result.loc[4, "price_de_rolling_mean_2"] == pytest.approx(
        fmean([13.0, 16.0])
    )


@pytest.mark.parametrize("window_hours", [[0], [1], [-3], [2, 0]])
def test_windows_below_the_minimum_are_rejected(processed_hourly, window_hours):
    with pytest.raises(ValueError, match="window_hours"):
        build_rolling_features(processed_hourly, window_hours=window_hours)


@pytest.mark.parametrize("window_hours", [[], "24", 24, [2.5], [True], None])
def test_invalid_window_specifications_are_rejected(processed_hourly, window_hours):
    with pytest.raises(ValueError, match="window_hours"):
        build_rolling_features(processed_hourly, window_hours=window_hours)


def test_minimum_window_constant_is_two_hours():
    assert MIN_ROLLING_WINDOW_HOURS == 2


def test_missing_source_columns_are_reported(processed_hourly):
    with pytest.raises(ValueError, match="Missing required columns"):
        build_rolling_features(
            processed_hourly.drop(columns=["price_fr"]), window_hours=[2]
        )


def test_missing_timestamp_column_is_reported(processed_hourly):
    with pytest.raises(ValueError, match="Missing required columns"):
        build_rolling_features(
            processed_hourly.drop(columns=["timestamp"]), window_hours=[2]
        )


def test_timestamp_cannot_be_a_rolling_source(processed_hourly):
    with pytest.raises(ValueError, match="timestamp"):
        build_rolling_features(
            processed_hourly, window_hours=[2], columns=["timestamp"]
        )


@pytest.mark.parametrize("columns", [[], "spread"])
def test_invalid_column_specifications_are_rejected(processed_hourly, columns):
    with pytest.raises(ValueError, match="columns"):
        build_rolling_features(processed_hourly, window_hours=[2], columns=columns)


@pytest.mark.parametrize(
    "values",
    [
        ["a", "b", "c", "d", "e", "f", "g", "h"],
        [True, False, True, False, True, False, True, False],
        [1 + 1j] * 8,
    ],
)
def test_non_real_numeric_sources_are_rejected(processed_hourly, values):
    frame = processed_hourly.copy()
    frame["spread"] = values

    with pytest.raises(ValueError, match="real numeric"):
        build_rolling_features(frame, window_hours=[2])


def test_duplicate_column_names_are_rejected(processed_hourly):
    duplicated = pd.concat([processed_hourly, processed_hourly[["spread"]]], axis=1)

    with pytest.raises(ValueError, match="Duplicate column"):
        build_rolling_features(duplicated, window_hours=[2])


def test_empty_dataset_is_rejected(processed_hourly):
    with pytest.raises(ValueError, match="empty"):
        build_rolling_features(processed_hourly.iloc[0:0], window_hours=[2])


def test_naive_timestamps_are_rejected(processed_hourly):
    naive = processed_hourly.copy()
    naive["timestamp"] = naive["timestamp"].dt.tz_localize(None)

    with pytest.raises(ValueError, match="timezone-aware"):
        build_rolling_features(naive, window_hours=[2])


def test_gapped_timestamps_are_rejected(processed_hourly):
    gapped = processed_hourly.drop(index=3).reset_index(drop=True)

    with pytest.raises(ValueError, match="hourly"):
        build_rolling_features(gapped, window_hours=[2])


def test_duplicate_timestamps_are_rejected(processed_hourly):
    duplicated = pd.concat(
        [processed_hourly, processed_hourly.iloc[[3]]], ignore_index=True
    )

    with pytest.raises(ValueError, match="hourly"):
        build_rolling_features(duplicated, window_hours=[2])


def test_off_hour_timestamps_are_rejected(processed_hourly):
    off_hour = processed_hourly.copy()
    off_hour["timestamp"] = off_hour["timestamp"] + pd.Timedelta(minutes=30)

    with pytest.raises(ValueError, match="hourly"):
        build_rolling_features(off_hour, window_hours=[2])


def test_rolling_mean_matches_the_mean_of_the_equivalent_lag_columns(processed_hourly):
    """Cross-check against Story 4.1: a 3-hour window equals lags 1, 2, and 3."""
    from energy_trading_pipeline.features.lag_features import build_lag_features

    rolling, _ = build_rolling_features(processed_hourly, window_hours=[3])
    lagged, _ = build_lag_features(processed_hourly, lag_hours=[1, 2, 3])

    lag_mean = lagged[
        ["price_de_lag_1", "price_de_lag_2", "price_de_lag_3"]
    ].mean(axis=1, skipna=False)

    pd.testing.assert_series_equal(
        rolling["price_de_rolling_mean_3"], lag_mean, check_names=False
    )
