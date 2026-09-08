"""Config-driven chronological training window selection without leakage."""

from datetime import date
import logging
from pathlib import Path

import pandas as pd
import pytest

from energy_trading_pipeline.config.loader import load_config
from energy_trading_pipeline.models.trainer import (
    TARGET_COLUMN,
    TrainingWindow,
    select_training_window,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_CONFIG = PROJECT_ROOT / "tests/fixtures/sample_config.yaml"
# Eight whole days of hourly rows, matching the shape of the feature dataset
# artifact: timestamp, target, then the feature columns.
HOURS = 24 * 8
FEATURE_COLUMNS = ["spread_lag_1", "spread_rolling_mean_24", "hour"]
WINDOW_CONFIG = {
    "start_date": "2023-01-01",
    "end_date": "2023-01-08",
    "train_start_date": "2023-01-01",
    "train_end_date": "2023-01-06",
    "validation_start_date": "2023-01-07",
    "validation_end_date": "2023-01-08",
}


@pytest.fixture
def feature_dataset():
    """Hourly feature dataset covering 2023-01-01 through 2023-01-08 in UTC."""
    timestamps = pd.date_range("2023-01-01", periods=HOURS, freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            TARGET_COLUMN: [10.0 + 0.5 * index for index in range(HOURS)],
            "spread_lag_1": [9.5 + 0.5 * index for index in range(HOURS)],
            "spread_rolling_mean_24": [9.0 + 0.5 * index for index in range(HOURS)],
            "hour": timestamps.hour,
        }
    )


@pytest.fixture
def window():
    """The valid chronological window declared by the fixture config."""
    return TrainingWindow.from_config(WINDOW_CONFIG)


def test_valid_chronological_split_puts_training_rows_before_validation(
    feature_dataset, window
):
    split = select_training_window(feature_dataset, window)

    assert split.train_timestamps.max() < split.validation_timestamps.min()
    assert split.train_timestamps.min() == pd.Timestamp("2023-01-01", tz="UTC")
    # Both ranges are end-inclusive, so the last training row is the final hour
    # of the training end date, not its midnight.
    assert split.train_timestamps.max() == pd.Timestamp("2023-01-06 23:00", tz="UTC")
    assert split.validation_timestamps.min() == pd.Timestamp("2023-01-07", tz="UTC")
    assert split.validation_timestamps.max() == pd.Timestamp(
        "2023-01-08 23:00", tz="UTC"
    )
    assert len(split.train_features) == 24 * 6
    assert len(split.validation_features) == 24 * 2


def test_invalid_overlapping_split_fails_clearly():
    overlapping = {**WINDOW_CONFIG, "validation_start_date": "2023-01-05"}

    with pytest.raises(ValueError, match="Training and validation ranges overlap"):
        TrainingWindow.from_config(overlapping)


def test_shared_boundary_date_is_rejected_as_an_overlap():
    # Both ranges are end-inclusive, so a shared date would train and validate
    # on the same 24 rows.
    shared_boundary = {**WINDOW_CONFIG, "validation_start_date": "2023-01-06"}

    with pytest.raises(ValueError, match="strictly before"):
        TrainingWindow.from_config(shared_boundary)


def test_inverted_ranges_fail_clearly():
    with pytest.raises(ValueError, match="train_end_date"):
        TrainingWindow.from_config({**WINDOW_CONFIG, "train_end_date": "2022-12-01"})

    with pytest.raises(ValueError, match="validation_end_date"):
        TrainingWindow.from_config(
            {**WINDOW_CONFIG, "validation_end_date": "2023-01-06"}
        )


def test_window_is_read_from_the_dates_config_section():
    window = TrainingWindow.from_config(WINDOW_CONFIG)

    assert window.train_start_date == date(2023, 1, 1)
    assert window.train_end_date == date(2023, 1, 6)
    assert window.validation_start_date == date(2023, 1, 7)
    assert window.validation_end_date == date(2023, 1, 8)
    assert window.as_metadata() == {
        "train_start_date": "2023-01-01",
        "train_end_date": "2023-01-06",
        "validation_start_date": "2023-01-07",
        "validation_end_date": "2023-01-08",
    }


def test_project_config_declares_a_usable_training_window():
    config = load_config(FIXTURE_CONFIG)

    window = TrainingWindow.from_config(config["dates"])

    assert window.train_end_date < window.validation_start_date


def test_missing_window_keys_fail_rather_than_defaulting_to_the_data_range():
    with pytest.raises(ValueError, match="Missing required training window key"):
        TrainingWindow.from_config({"start_date": "2023-01-01", "end_date": "2023-01-08"})


def test_invalid_window_date_fails_clearly():
    with pytest.raises(ValueError, match="not a valid YYYY-MM-DD date"):
        TrainingWindow.from_config({**WINDOW_CONFIG, "train_start_date": "01/01/2023"})


def test_window_outside_the_configured_data_range_warns(caplog):
    reaching = {**WINDOW_CONFIG, "train_start_date": "2022-12-25"}

    with caplog.at_level(logging.WARNING):
        TrainingWindow.from_config(reaching)

    assert "precedes dates.start_date" in caplog.text


def test_feature_and_target_arrays_are_returned_consistently(feature_dataset, window):
    split = select_training_window(feature_dataset, window)

    assert split.feature_columns == FEATURE_COLUMNS
    assert split.target_column == TARGET_COLUMN
    for features, target, timestamps in (
        (split.train_features, split.train_target, split.train_timestamps),
        (
            split.validation_features,
            split.validation_target,
            split.validation_timestamps,
        ),
    ):
        # The timestamp and the target are never predictors.
        assert features.columns.tolist() == FEATURE_COLUMNS
        assert target.name == TARGET_COLUMN
        assert len(features) == len(target) == len(timestamps)
        assert features.index.tolist() == list(range(len(features)))
        assert target.index.tolist() == list(range(len(target)))

    # Rows keep their original alignment across features, target, and timestamps.
    expected = feature_dataset.loc[
        feature_dataset["timestamp"] < pd.Timestamp("2023-01-07", tz="UTC")
    ]
    assert split.train_target.tolist() == expected[TARGET_COLUMN].tolist()
    assert split.train_features["spread_lag_1"].tolist() == (
        expected["spread_lag_1"].tolist()
    )


def test_explicit_feature_columns_pin_the_feature_contract(feature_dataset, window):
    split = select_training_window(
        feature_dataset, window, feature_columns=["hour", "spread_lag_1"]
    )

    assert split.feature_columns == ["hour", "spread_lag_1"]
    assert split.train_features.columns.tolist() == ["hour", "spread_lag_1"]
    assert split.validation_features.columns.tolist() == ["hour", "spread_lag_1"]


def test_reserved_and_missing_feature_columns_are_rejected(feature_dataset, window):
    with pytest.raises(ValueError, match="predictors only"):
        select_training_window(
            feature_dataset, window, feature_columns=["hour", TARGET_COLUMN]
        )

    with pytest.raises(ValueError, match="missing feature column"):
        select_training_window(feature_dataset, window, feature_columns=["nope"])


def test_out_of_order_rows_are_selected_chronologically(feature_dataset, window):
    shuffled = feature_dataset.sample(frac=1.0, random_state=42)

    split = select_training_window(shuffled, window)

    assert split.train_timestamps.is_monotonic_increasing
    assert split.validation_timestamps.is_monotonic_increasing
    assert split.train_timestamps.max() < split.validation_timestamps.min()


def test_range_selecting_no_rows_fails_clearly(feature_dataset):
    empty_validation = TrainingWindow.from_config(
        {
            **WINDOW_CONFIG,
            "validation_start_date": "2024-01-01",
            "validation_end_date": "2024-01-02",
        }
    )

    with pytest.raises(ValueError, match="validation range .* selects no rows"):
        select_training_window(feature_dataset, empty_validation)


def test_missing_required_columns_fail_clearly(feature_dataset, window):
    with pytest.raises(ValueError, match="missing required column"):
        select_training_window(feature_dataset.drop(columns=[TARGET_COLUMN]), window)

    with pytest.raises(ValueError, match="missing required column"):
        select_training_window(feature_dataset.drop(columns=["timestamp"]), window)


def test_naive_timestamps_are_selected_by_the_same_window(feature_dataset, window):
    naive = feature_dataset.assign(
        timestamp=feature_dataset["timestamp"].dt.tz_localize(None)
    )

    split = select_training_window(naive, window)

    assert len(split.train_features) == 24 * 6
    assert split.train_timestamps.max() == pd.Timestamp("2023-01-06 23:00")


def test_selection_does_not_mutate_the_input_dataset(feature_dataset, window):
    before = feature_dataset.copy()

    select_training_window(feature_dataset, window)

    pd.testing.assert_frame_equal(feature_dataset, before)


def test_window_must_be_a_training_window(feature_dataset):
    with pytest.raises(ValueError, match="must be a TrainingWindow"):
        select_training_window(feature_dataset, WINDOW_CONFIG)


def test_metadata_records_the_window_and_selected_rows(feature_dataset, window):
    split = select_training_window(feature_dataset, window)

    assert split.metadata["window"] == window.as_metadata()
    assert split.metadata["train_rows"] == 24 * 6
    assert split.metadata["validation_rows"] == 24 * 2
    assert split.metadata["feature_columns"] == FEATURE_COLUMNS
    assert split.metadata["target_column"] == TARGET_COLUMN
    assert split.metadata["train_range"]["start"].startswith("2023-01-01T00:00:00")
    assert split.metadata["validation_range"]["end"].startswith("2023-01-08T23:00:00")
