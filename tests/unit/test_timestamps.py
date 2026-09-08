"""UTC normalization and hourly validation contracts on small local inputs."""

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from energy_trading_pipeline.data_ingestion.local_loader import load_local_data
from energy_trading_pipeline.preprocessing.timestamps import normalize_timestamps
from energy_trading_pipeline.preprocessing.validation import validate_hourly_index


def test_normalization_sorts_preserves_values_and_does_not_mutate_input():
    frame = pd.DataFrame(
        {
            "timestamp": ["2023-01-01 02:00", "2023-01-01T01:00:00"],
            "price_de": [20.0, 10.0],
        },
        index=[8, 4],
    )
    original = frame.copy(deep=True)

    result, metadata = normalize_timestamps(frame, source_timezone="Europe/Berlin")

    pd.testing.assert_frame_equal(frame, original)
    assert result["timestamp"].tolist() == list(
        pd.date_range("2023-01-01", periods=2, freq="h", tz="UTC")
    )
    assert result["price_de"].tolist() == [10.0, 20.0]
    assert result.index.tolist() == [0, 1]
    assert metadata["source_timezone"] == "Europe/Berlin"
    assert metadata["normalized_timezone"] == "UTC"
    assert metadata["naive_timestamp_count"] == 2
    assert metadata["hourly_validation"]["is_hourly"] is True
    assert metadata["dst_policy"] == {
        "ambiguous": "raise",
        "nonexistent": "raise",
        "aware": "preserve_instant",
    }
    assert json.loads(json.dumps(metadata)) == metadata
    assert yaml.safe_load(yaml.safe_dump(metadata)) == metadata


def test_default_timezone_is_utc_and_mixed_awareness_preserves_instants():
    frame = pd.DataFrame(
        {"timestamp": ["2023-01-01 00:00", "2023-01-01T02:00:00+01:00"]}
    )
    result, metadata = normalize_timestamps(frame)

    assert result["timestamp"].tolist() == list(
        pd.date_range("2023-01-01", periods=2, freq="h", tz="UTC")
    )
    assert metadata["source_timezone"] == "UTC"
    assert metadata["source_timezones"] == ["UTC+01:00"]
    assert metadata["naive_timestamp_count"] == 1


@pytest.mark.parametrize("timezone", ["Europe/Berlin", "Europe/Paris"])
@pytest.mark.parametrize("start", ["2023-03-26 00:00", "2023-10-29 00:00"])
def test_aware_dst_transitions_remain_continuous_utc_hours(timezone, start):
    timestamps = pd.date_range(start, periods=6, freq="h", tz=timezone)
    result, metadata = normalize_timestamps(pd.DataFrame({"timestamp": timestamps}))

    assert result["timestamp"].tolist() == timestamps.tz_convert("UTC").tolist()
    assert metadata["source_timezones"] == [timezone]
    assert metadata["hourly_validation"]["is_hourly"] is True


def test_explicit_fall_back_offsets_are_distinct_hours():
    frame = pd.DataFrame(
        {"timestamp": ["2023-10-29T02:00:00+02:00", "2023-10-29T02:00:00+01:00"]}
    )
    result, metadata = normalize_timestamps(frame)

    assert result["timestamp"].tolist() == list(
        pd.date_range("2023-10-29", periods=2, freq="h", tz="UTC")
    )
    assert metadata["source_timezones"] == ["UTC+01:00", "UTC+02:00"]
    assert metadata["hourly_validation"]["duplicate_count"] == 0


def test_naive_spring_forward_does_not_create_false_missing_hour():
    frame = pd.DataFrame({"timestamp": ["2023-03-26 01:00", "2023-03-26 03:00"]})
    _, metadata = normalize_timestamps(frame, source_timezone="Europe/Berlin")
    assert metadata["hourly_validation"]["is_hourly"] is True


@pytest.mark.parametrize("timestamp", ["2023-03-26 02:00", "2023-10-29 02:00"])
def test_naive_dst_ambiguity_and_nonexistence_fail_clearly(timestamp):
    with pytest.raises(ValueError, match="[Aa]mbiguous or nonexistent.*row 0"):
        normalize_timestamps(
            pd.DataFrame({"timestamp": [timestamp]}), source_timezone="Europe/Berlin"
        )


@pytest.mark.parametrize("timestamp", ["bad-date", "", None, pd.NaT, 1672531200])
def test_invalid_or_missing_timestamp_fails_with_row_context(timestamp):
    with pytest.raises(ValueError, match="[Ii]nvalid.*timestamp.*row 0"):
        normalize_timestamps(pd.DataFrame({"timestamp": [timestamp]}))


def test_missing_column_empty_input_and_invalid_timezone_fail():
    with pytest.raises(ValueError, match="timestamp"):
        normalize_timestamps(pd.DataFrame({"price_de": [1]}))
    with pytest.raises(ValueError, match="empty"):
        normalize_timestamps(pd.DataFrame({"timestamp": []}))
    with pytest.raises(ValueError, match="source_timezone"):
        normalize_timestamps(
            pd.DataFrame({"timestamp": ["2023-01-01"]}), source_timezone="Not/AZone"
        )


def test_missing_duplicate_and_off_hour_records_are_reported_not_cleaned(caplog):
    frame = pd.DataFrame(
        {
            "timestamp": [
                "2023-01-01T00:00:00Z",
                "2023-01-01T02:00:00Z",
                "2023-01-01T02:00:00Z",
                "2023-01-01T02:30:00Z",
                "2023-01-01T03:00:00Z",
            ]
        }
    )
    result, metadata = normalize_timestamps(frame)
    report = metadata["hourly_validation"]

    assert len(result) == len(frame)
    assert report["is_hourly"] is False
    assert report["missing_hours"] == ["2023-01-01T01:00:00+00:00"]
    assert report["duplicate_count"] == 1
    assert report["duplicate_timestamps"] == ["2023-01-01T02:00:00+00:00"]
    assert report["non_hourly_count"] == 1
    assert report["non_hourly_timestamps"] == ["2023-01-01T02:30:00+00:00"]
    assert "hourly" in caplog.text


@pytest.mark.parametrize("offset", ["30min", "1s", "1ns"])
def test_hourly_spacing_with_off_hour_origin_is_not_valid(offset):
    timestamps = pd.date_range("2023-01-01", periods=2, freq="h", tz="UTC")
    report = validate_hourly_index(pd.Series(timestamps + pd.Timedelta(offset)))
    assert report["non_hourly_count"] == 2
    assert report["is_hourly"] is False


def test_duplicate_detection_uses_utc_instant_not_source_text():
    _, metadata = normalize_timestamps(
        pd.DataFrame(
            {"timestamp": ["2023-01-01T00:00:00Z", "2023-01-01T01:00:00+01:00"]}
        )
    )
    assert metadata["hourly_validation"]["duplicate_count"] == 1


@pytest.mark.parametrize(
    "timestamps",
    [
        pd.Series([], dtype="datetime64[ns, UTC]"),
        pd.Series(["2023-01-01"]),
        pd.Series(pd.date_range("2023-01-01", periods=2, freq="h")),
        pd.Series([pd.NaT], dtype="datetime64[ns, UTC]"),
    ],
)
def test_validator_rejects_empty_unparsed_naive_or_missing_values(timestamps):
    with pytest.raises(ValueError):
        validate_hourly_index(timestamps)


def test_validator_reports_unsorted_input():
    timestamps = pd.Series(
        pd.date_range("2023-01-01", periods=2, freq="h", tz="UTC")[::-1]
    )
    report = validate_hourly_index(timestamps)
    assert report["is_sorted"] is False
    assert report["is_hourly"] is False


def test_single_hour_has_no_internal_gaps():
    _, metadata = normalize_timestamps(pd.DataFrame({"timestamp": ["2023-01-01"]}))
    assert metadata["hourly_validation"]["is_hourly"] is True
    assert metadata["hourly_validation"]["missing_hours"] == []


@pytest.mark.parametrize(
    ("filename", "duplicate_count"),
    [("sample_prices_de.csv", 1), ("sample_prices_fr.csv", 0), ("sample_weather.csv", 0)],
)
def test_existing_local_fixtures_normalize_without_cleaning(filename, duplicate_count):
    frame = load_local_data(Path(__file__).parents[1] / "fixtures" / filename)
    result, metadata = normalize_timestamps(frame)
    assert len(result) == len(frame)
    assert metadata["hourly_validation"]["duplicate_count"] == duplicate_count
    assert metadata["hourly_validation"]["missing_hours"] == []
    pd.testing.assert_frame_equal(
        result.drop(columns="timestamp"), frame.drop(columns="timestamp")
    )
