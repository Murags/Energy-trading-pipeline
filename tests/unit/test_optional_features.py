"""Optional exogenous predictor selection shared by weather and grid builders."""

import logging

import numpy as np
import pandas as pd
import pytest

from energy_trading_pipeline.features.optional_features import (
    OPTIONAL_FEATURE_DTYPE,
    UNAVAILABLE_COLUMN_POLICY,
    select_optional_features,
)

HOURS = 8


@pytest.fixture
def aligned_hourly():
    """Eight contiguous UTC hours with two usable optional predictors."""
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2023-01-01", periods=HOURS, freq="h", tz="UTC"),
            "price_de": [50.0 + index for index in range(HOURS)],
            "price_fr": [40.0 + index for index in range(HOURS)],
            "spread": [10.0] * HOURS,
            "temperature_2m_c": [1.5 + index for index in range(HOURS)],
            "wind_speed_10m_m_s": list(range(HOURS)),
        }
    )


def select(df, columns):
    """Select optional columns under a fixed group and stage."""
    return select_optional_features(df, columns, group="weather", stage="features.test")


def test_available_columns_are_selected(aligned_hourly):
    result, metadata = select(
        aligned_hourly, ["temperature_2m_c", "wind_speed_10m_m_s"]
    )

    assert metadata["selected_columns"] == ["temperature_2m_c", "wind_speed_10m_m_s"]
    assert metadata["missing_columns"] == []
    assert metadata["unusable_columns"] == {}
    for column in metadata["selected_columns"]:
        assert result[column].tolist() == aligned_hourly[column].astype(float).tolist()


def test_selected_columns_are_cast_to_a_stable_float_dtype(aligned_hourly):
    result, metadata = select(aligned_hourly, ["wind_speed_10m_m_s"])

    assert aligned_hourly["wind_speed_10m_m_s"].dtype != OPTIONAL_FEATURE_DTYPE
    assert result["wind_speed_10m_m_s"].dtype == OPTIONAL_FEATURE_DTYPE
    assert metadata["dtype"] == OPTIONAL_FEATURE_DTYPE


def test_missing_columns_warn_and_continue(aligned_hourly, caplog):
    caplog.set_level(logging.WARNING)

    result, metadata = select(
        aligned_hourly, ["temperature_2m_c", "shortwave_radiation_w_m2"]
    )

    assert metadata["selected_columns"] == ["temperature_2m_c"]
    assert metadata["missing_columns"] == ["shortwave_radiation_w_m2"]
    assert metadata["unavailable_column_policy"] == UNAVAILABLE_COLUMN_POLICY
    assert "shortwave_radiation_w_m2" in caplog.text
    assert len(result) == HOURS


def test_every_requested_column_can_be_unavailable(aligned_hourly, caplog):
    caplog.set_level(logging.WARNING)

    result, metadata = select(aligned_hourly, ["load_de", "load_fr"])

    assert metadata["selected_columns"] == []
    assert metadata["missing_columns"] == ["load_de", "load_fr"]
    assert "load_de" in caplog.text
    pd.testing.assert_frame_equal(result, aligned_hourly)


def test_no_requested_columns_is_valid(aligned_hourly, caplog):
    caplog.set_level(logging.WARNING)

    result, metadata = select(aligned_hourly, [])

    assert metadata["requested_columns"] == []
    assert metadata["selected_columns"] == []
    assert caplog.text == ""
    pd.testing.assert_frame_equal(result, aligned_hourly)


@pytest.mark.parametrize(
    ("values", "reason"),
    [
        ([None] * HOURS, "not real numeric"),
        ([1.0] * (HOURS - 1) + [None], "missing"),
        ([np.nan] * HOURS, "missing"),
        ([np.inf] + [1.0] * (HOURS - 1), "non-finite"),
        (list("abcdefgh"), "not real numeric"),
        ([True] * HOURS, "not real numeric"),
    ],
)
def test_unusable_columns_warn_and_are_excluded(
    aligned_hourly, caplog, values, reason
):
    caplog.set_level(logging.WARNING)
    frame = aligned_hourly.assign(temperature_2m_c=values)

    result, metadata = select(frame, ["temperature_2m_c", "wind_speed_10m_m_s"])

    assert metadata["selected_columns"] == ["wind_speed_10m_m_s"]
    assert reason in metadata["unusable_columns"]["temperature_2m_c"]
    assert "temperature_2m_c" in caplog.text
    assert len(result) == HOURS


def test_unusable_columns_are_not_silently_dropped_from_the_frame(aligned_hourly):
    frame = aligned_hourly.assign(temperature_2m_c=[None] * HOURS)

    result, metadata = select(frame, ["temperature_2m_c"])

    assert "temperature_2m_c" in result.columns
    assert metadata["unusable_columns"]


def test_metadata_describes_the_selection(aligned_hourly):
    result, metadata = select(
        aligned_hourly, ["wind_speed_10m_m_s", "shortwave_radiation_w_m2"]
    )

    assert metadata == {
        "stage": "features.test",
        "group": "weather",
        "requested_columns": ["wind_speed_10m_m_s", "shortwave_radiation_w_m2"],
        "selected_columns": ["wind_speed_10m_m_s"],
        "missing_columns": ["shortwave_radiation_w_m2"],
        "unusable_columns": {},
        "unavailable_column_policy": UNAVAILABLE_COLUMN_POLICY,
        "dtype": OPTIONAL_FEATURE_DTYPE,
        "output_rows": len(result),
    }


def test_requested_columns_keep_configured_order_and_are_de_duplicated(
    aligned_hourly,
):
    _, metadata = select(
        aligned_hourly,
        ["wind_speed_10m_m_s", "temperature_2m_c", "wind_speed_10m_m_s"],
    )

    assert metadata["requested_columns"] == [
        "wind_speed_10m_m_s",
        "temperature_2m_c",
    ]
    assert metadata["selected_columns"] == [
        "wind_speed_10m_m_s",
        "temperature_2m_c",
    ]


def test_input_dataframe_is_not_mutated(aligned_hourly):
    original = aligned_hourly.copy(deep=True)

    select(aligned_hourly, ["wind_speed_10m_m_s"])

    pd.testing.assert_frame_equal(aligned_hourly, original)


def test_unsorted_input_is_ordered_chronologically(aligned_hourly):
    shuffled = aligned_hourly.iloc[::-1].reset_index(drop=True)

    result, _ = select(shuffled, ["temperature_2m_c"])
    expected, _ = select(aligned_hourly, ["temperature_2m_c"])

    pd.testing.assert_frame_equal(result, expected)


def test_timestamps_are_normalised_to_utc(aligned_hourly):
    local = aligned_hourly.copy()
    local["timestamp"] = local["timestamp"].dt.tz_convert("Europe/Berlin")

    result, _ = select(local, ["temperature_2m_c"])
    expected, _ = select(aligned_hourly, ["temperature_2m_c"])

    pd.testing.assert_frame_equal(result, expected)


@pytest.mark.parametrize(
    "column", ["timestamp", "spread", "price_de", "price_fr"]
)
def test_market_and_target_columns_cannot_be_optional_predictors(
    aligned_hourly, column
):
    with pytest.raises(ValueError, match="market or target columns"):
        select(aligned_hourly, [column])


@pytest.mark.parametrize("columns", ["temperature_2m_c", None, 7])
def test_invalid_column_specifications_are_rejected(aligned_hourly, columns):
    with pytest.raises(ValueError, match="must be a sequence"):
        select(aligned_hourly, columns)


@pytest.mark.parametrize("columns", [[1], [None], [""], ["  "]])
def test_invalid_column_names_are_rejected(aligned_hourly, columns):
    with pytest.raises(ValueError, match="Invalid weather column name"):
        select(aligned_hourly, columns)


def test_missing_timestamp_column_is_rejected(aligned_hourly):
    with pytest.raises(ValueError, match="timestamp"):
        select(aligned_hourly.drop(columns=["timestamp"]), ["temperature_2m_c"])


def test_naive_timestamps_are_rejected(aligned_hourly):
    naive = aligned_hourly.copy()
    naive["timestamp"] = naive["timestamp"].dt.tz_localize(None)

    with pytest.raises(ValueError, match="timezone-aware"):
        select(naive, ["temperature_2m_c"])


def test_empty_dataset_is_rejected(aligned_hourly):
    with pytest.raises(ValueError):
        select(aligned_hourly.iloc[0:0], ["temperature_2m_c"])


def test_duplicate_column_names_are_rejected(aligned_hourly):
    duplicated = aligned_hourly.copy()
    duplicated.columns = [
        "timestamp",
        "price_de",
        "price_fr",
        "spread",
        "temperature_2m_c",
        "temperature_2m_c",
    ]

    with pytest.raises(ValueError, match="Duplicate column names"):
        select(duplicated, ["temperature_2m_c"])
