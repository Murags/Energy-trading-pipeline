"""Deterministic calendar feature extraction from normalized UTC timestamps."""

from datetime import date
import logging

import pandas as pd
import pytest

from energy_trading_pipeline.features.calendar_features import (
    CALENDAR_FEATURE_COLUMNS,
    CALENDAR_INTEGER_DTYPE,
    DEFAULT_CALENDAR_FEATURES,
    UNCONFIGURED_HOLIDAY_POLICY,
    WEEKEND_DAYS_OF_WEEK,
    build_calendar_features,
)

# 2023-01-06 is a Friday, so the fixture spans a Friday/Saturday/Sunday run and
# covers the weekend transition in both directions.
FIRST_HOUR = "2023-01-06"
HOURS = 72
EXPECTED_DAYS_OF_WEEK = (4, 5, 6)


@pytest.fixture
def processed_hourly():
    """Three contiguous UTC days of processed prices and spread."""
    timestamps = pd.date_range(FIRST_HOUR, periods=HOURS, freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "price_de": [50.0 + index for index in range(HOURS)],
            "price_fr": [40.0 + index for index in range(HOURS)],
            "spread": [10.0] * HOURS,
        }
    )


def test_hour_repeats_the_utc_hour_of_day(processed_hourly):
    result, _ = build_calendar_features(processed_hourly)

    assert result["hour"].tolist() == list(range(24)) * 3


def test_day_of_week_follows_monday_zero_numbering(processed_hourly):
    result, _ = build_calendar_features(processed_hourly)

    expected = [day for day in EXPECTED_DAYS_OF_WEEK for _ in range(24)]
    assert result["day_of_week"].tolist() == expected


def test_month_is_the_utc_calendar_month(processed_hourly):
    result, _ = build_calendar_features(processed_hourly)

    assert result["month"].tolist() == [1] * HOURS


def test_weekend_flag_marks_saturday_and_sunday_only(processed_hourly):
    result, _ = build_calendar_features(processed_hourly)

    expected = [day in WEEKEND_DAYS_OF_WEEK for day in result["day_of_week"]]
    assert result["is_weekend"].tolist() == expected
    assert result.loc[:23, "is_weekend"].tolist() == [False] * 24
    assert result.loc[24:, "is_weekend"].tolist() == [True] * 48


def test_weekend_days_are_saturday_and_sunday():
    assert WEEKEND_DAYS_OF_WEEK == (5, 6)


def test_repeated_calls_produce_identical_features(processed_hourly):
    first, first_metadata = build_calendar_features(processed_hourly)
    second, second_metadata = build_calendar_features(processed_hourly)

    pd.testing.assert_frame_equal(first, second)
    assert first_metadata == second_metadata


def test_each_row_depends_only_on_its_own_timestamp(processed_hourly):
    result, _ = build_calendar_features(processed_hourly)

    single_row = processed_hourly.iloc[[40]].reset_index(drop=True)
    isolated, _ = build_calendar_features(single_row)

    for feature in DEFAULT_CALENDAR_FEATURES:
        assert isolated.loc[0, feature] == result.loc[40, feature]


def test_default_features_exclude_the_optional_holiday_flag(processed_hourly):
    result, metadata = build_calendar_features(processed_hourly)

    assert metadata["generated_columns"] == list(DEFAULT_CALENDAR_FEATURES)
    assert "is_holiday" not in result.columns


def test_feature_selection_is_config_driven(processed_hourly):
    result, metadata = build_calendar_features(
        processed_hourly, features=["hour", "is_weekend"]
    )

    assert metadata["generated_columns"] == ["hour", "is_weekend"]
    assert "day_of_week" not in result.columns
    assert "month" not in result.columns


def test_columns_are_emitted_in_canonical_order_and_de_duplicated(processed_hourly):
    result, metadata = build_calendar_features(
        processed_hourly, features=["month", "hour", "month", "is_weekend"]
    )

    assert metadata["requested_features"] == ["hour", "month", "is_weekend"]
    assert result.columns.tolist() == [
        "timestamp",
        "price_de",
        "price_fr",
        "spread",
        "hour",
        "month",
        "is_weekend",
    ]


def test_generated_columns_use_snake_case_names(processed_hourly):
    result, _ = build_calendar_features(
        processed_hourly, features=CALENDAR_FEATURE_COLUMNS, holiday_dates=["2023-01-06"]
    )

    for column in CALENDAR_FEATURE_COLUMNS:
        assert column in result.columns
        assert column == column.lower()
        assert " " not in column and "-" not in column


def test_calendar_columns_use_stable_dtypes(processed_hourly):
    result, _ = build_calendar_features(
        processed_hourly, features=CALENDAR_FEATURE_COLUMNS, holiday_dates=["2023-01-06"]
    )

    for column in ("hour", "day_of_week", "month"):
        assert result[column].dtype == CALENDAR_INTEGER_DTYPE
    for column in ("is_weekend", "is_holiday"):
        assert result[column].dtype == bool


def test_holiday_flag_marks_configured_utc_dates_only(processed_hourly):
    result, metadata = build_calendar_features(
        processed_hourly,
        features=["is_holiday"],
        holiday_dates=["2023-01-07", "2022-12-25"],
    )

    expected = [
        timestamp.date() == date(2023, 1, 7) for timestamp in result["timestamp"]
    ]
    assert result["is_holiday"].tolist() == expected
    assert result["is_holiday"].sum() == 24
    assert metadata["holiday_dates"] == ["2022-12-25", "2023-01-07"]


def test_holiday_dates_accept_calendar_date_objects(processed_hourly):
    result, _ = build_calendar_features(
        processed_hourly, features=["is_holiday"], holiday_dates=[date(2023, 1, 7)]
    )

    assert result["is_holiday"].sum() == 24


def test_holiday_flag_is_skipped_with_a_warning_when_unconfigured(
    processed_hourly, caplog
):
    caplog.set_level(logging.WARNING)

    result, metadata = build_calendar_features(
        processed_hourly, features=["hour", "is_holiday"]
    )

    assert "is_holiday" not in result.columns
    assert metadata["skipped_features"] == ["is_holiday"]
    assert metadata["generated_columns"] == ["hour"]
    assert metadata["unconfigured_holiday_policy"] == UNCONFIGURED_HOLIDAY_POLICY
    assert "is_holiday" in caplog.text


def test_unrequested_holiday_dates_warn_without_adding_a_column(
    processed_hourly, caplog
):
    caplog.set_level(logging.WARNING)

    result, metadata = build_calendar_features(
        processed_hourly, features=["hour"], holiday_dates=["2023-01-07"]
    )

    assert "is_holiday" not in result.columns
    assert metadata["skipped_features"] == []
    assert "holiday" in caplog.text


def test_metadata_describes_the_generated_calendar_features(processed_hourly):
    result, metadata = build_calendar_features(
        processed_hourly,
        features=CALENDAR_FEATURE_COLUMNS,
        holiday_dates=["2023-01-07"],
    )

    assert metadata == {
        "stage": "features.calendar",
        "requested_features": list(CALENDAR_FEATURE_COLUMNS),
        "generated_columns": list(CALENDAR_FEATURE_COLUMNS),
        "skipped_features": [],
        "unconfigured_holiday_policy": UNCONFIGURED_HOLIDAY_POLICY,
        "weekend_days_of_week": list(WEEKEND_DAYS_OF_WEEK),
        "holiday_dates": ["2023-01-07"],
        "holiday_date_basis": "utc_calendar_date",
        "timezone": "UTC",
        "output_rows": len(result),
    }


def test_no_target_derived_columns_are_added(processed_hourly):
    result, _ = build_calendar_features(
        processed_hourly,
        features=CALENDAR_FEATURE_COLUMNS,
        holiday_dates=["2023-01-07"],
    )

    added = [
        column
        for column in result.columns
        if column not in processed_hourly.columns
    ]
    assert added == list(CALENDAR_FEATURE_COLUMNS)


def test_input_dataframe_is_not_mutated(processed_hourly):
    original = processed_hourly.copy(deep=True)

    build_calendar_features(processed_hourly)

    pd.testing.assert_frame_equal(processed_hourly, original)


def test_unsorted_input_is_ordered_chronologically(processed_hourly):
    shuffled = processed_hourly.iloc[::-1].reset_index(drop=True)

    result, _ = build_calendar_features(shuffled)
    expected, _ = build_calendar_features(processed_hourly)

    pd.testing.assert_frame_equal(result, expected)


def test_timestamps_are_normalised_to_utc(processed_hourly):
    local = processed_hourly.copy()
    local["timestamp"] = local["timestamp"].dt.tz_convert("Europe/Berlin")

    result, _ = build_calendar_features(local)
    expected, _ = build_calendar_features(processed_hourly)

    pd.testing.assert_frame_equal(result, expected)


def test_existing_calendar_columns_are_recomputed_not_duplicated(processed_hourly):
    stale = processed_hourly.assign(hour=-1)

    result, metadata = build_calendar_features(stale, features=["hour"])

    assert result.columns.tolist().count("hour") == 1
    assert result["hour"].tolist() == list(range(24)) * 3
    assert metadata["generated_columns"] == ["hour"]


def test_hourly_gaps_are_tolerated(processed_hourly):
    gapped = processed_hourly.drop(index=[5, 6, 7]).reset_index(drop=True)

    result, metadata = build_calendar_features(gapped)

    assert metadata["output_rows"] == HOURS - 3
    assert result["hour"].tolist() == [0, 1, 2, 3, 4, 8, 9] + list(range(10, 24)) + list(
        range(24)
    ) * 2


@pytest.mark.parametrize("features", [["holiday"], ["hour", "year"], ["Hour"]])
def test_unsupported_features_are_rejected(processed_hourly, features):
    with pytest.raises(ValueError, match="Unsupported calendar features"):
        build_calendar_features(processed_hourly, features=features)


@pytest.mark.parametrize("features", [[], "hour", None, 4])
def test_invalid_feature_specifications_are_rejected(processed_hourly, features):
    with pytest.raises(ValueError, match="nonempty sequence"):
        build_calendar_features(processed_hourly, features=features)


@pytest.mark.parametrize("features", [[1], [None], [["hour"]]])
def test_non_string_feature_names_are_rejected(processed_hourly, features):
    with pytest.raises(ValueError, match="must be strings"):
        build_calendar_features(processed_hourly, features=features)


@pytest.mark.parametrize(
    "holiday_dates",
    [
        ["01/01/2023"],
        ["not-a-date"],
        [20230101],
        [pd.Timestamp("2023-01-01")],
    ],
)
def test_invalid_holiday_dates_are_rejected(processed_hourly, holiday_dates):
    with pytest.raises(ValueError, match="Invalid holiday date"):
        build_calendar_features(
            processed_hourly, features=["is_holiday"], holiday_dates=holiday_dates
        )


@pytest.mark.parametrize("holiday_dates", ["2023-01-01", None, 2023])
def test_invalid_holiday_date_specifications_are_rejected(
    processed_hourly, holiday_dates
):
    with pytest.raises(ValueError, match="holiday_dates must be a sequence"):
        build_calendar_features(
            processed_hourly, features=["is_holiday"], holiday_dates=holiday_dates
        )


def test_duplicate_timestamps_are_rejected(processed_hourly):
    duplicated = pd.concat(
        [processed_hourly, processed_hourly.iloc[[0]]], ignore_index=True
    )

    with pytest.raises(ValueError, match="Duplicate timestamps"):
        build_calendar_features(duplicated)


def test_naive_timestamps_are_rejected(processed_hourly):
    naive = processed_hourly.copy()
    naive["timestamp"] = naive["timestamp"].dt.tz_localize(None)

    with pytest.raises(ValueError, match="timezone-aware"):
        build_calendar_features(naive)


def test_missing_timestamp_column_is_rejected(processed_hourly):
    with pytest.raises(ValueError, match="timestamp"):
        build_calendar_features(processed_hourly.drop(columns=["timestamp"]))


def test_empty_dataset_is_rejected(processed_hourly):
    with pytest.raises(ValueError):
        build_calendar_features(processed_hourly.iloc[0:0])


def test_duplicate_column_names_are_rejected(processed_hourly):
    duplicated = processed_hourly.copy()
    duplicated.columns = ["timestamp", "price_de", "price_de", "spread"]

    with pytest.raises(ValueError, match="Duplicate column names"):
        build_calendar_features(duplicated)
