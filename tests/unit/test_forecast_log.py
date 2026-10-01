"""Forecast log arithmetic, validation, and local artifact round-trips."""

import numpy as np
import pandas as pd
import pytest

from energy_trading_pipeline.backtesting.forecast_log import (
    build_forecast_log,
    read_forecast_log,
    write_forecast_log,
)


INPUT_COLUMNS = [
    "timestamp",
    "forecast_timestamp",
    "prediction",
    "actual",
    "strategy",
    "model_version",
]
LOG_COLUMNS = [
    "timestamp",
    "forecast_timestamp",
    "prediction",
    "actual",
    "error",
    "squared_error",
    "absolute_error",
    "strategy",
    "model_version",
]


@pytest.fixture
def records() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-02", periods=3, freq="h", tz="UTC"),
            "forecast_timestamp": [pd.Timestamp("2024-01-01T12:00:00Z")] * 3,
            "prediction": [3.0, -2.0, 4.0],
            "actual": [1.0, 3.0, 4.0],
            "strategy": ["no_retraining", "fixed_schedule", "performance_triggered"],
            "model_version": ["model_20240101_110000"] * 3,
        }
    )


def test_build_computes_errors_and_preserves_input(records):
    original = records.copy(deep=True)
    result = build_forecast_log(records)
    assert result.columns.tolist() == LOG_COLUMNS
    assert result["error"].tolist() == [-2.0, 5.0, 0.0]
    assert result["squared_error"].tolist() == [4.0, 25.0, 0.0]
    assert result["absolute_error"].tolist() == [2.0, 5.0, 0.0]
    pd.testing.assert_frame_equal(records, original)


def test_build_sorts_and_normalizes_aware_timestamps(records):
    records["timestamp"] = records["timestamp"].dt.tz_convert("Europe/Berlin")
    records["forecast_timestamp"] = records["forecast_timestamp"].map(str)
    result = build_forecast_log(records.iloc[::-1])
    assert result["timestamp"].is_monotonic_increasing
    assert str(result["timestamp"].dtype) == "datetime64[ns, UTC]"
    assert str(result["forecast_timestamp"].dtype) == "datetime64[ns, UTC]"
    assert result["error"].tolist() == [-2.0, 5.0, 0.0]


def test_unsigned_values_and_stale_errors_are_recomputed(records):
    records["prediction"] = pd.Series([3, 2, 4], dtype="uint64")
    records["actual"] = pd.Series([1, 3, 4], dtype="uint64")
    records["error"] = 999
    result = build_forecast_log(records)
    assert result["error"].tolist() == [-2.0, 1.0, 0.0]


@pytest.mark.parametrize("column", INPUT_COLUMNS)
def test_build_requires_input_columns(records, column):
    with pytest.raises(ValueError, match=column):
        build_forecast_log(records.drop(columns=column))


@pytest.mark.parametrize("column", ["strategy", "model_version"])
@pytest.mark.parametrize("value", [None, "", "  ", 123])
def test_build_requires_nonempty_string_identifiers(records, column, value):
    records[column] = pd.Series([value] * 3, dtype=object)
    with pytest.raises(ValueError, match=column):
        build_forecast_log(records)


def test_build_rejects_unknown_strategy(records):
    records.loc[0, "strategy"] = "weekly"
    with pytest.raises(ValueError, match="strategy"):
        build_forecast_log(records)


@pytest.mark.parametrize("column", ["timestamp", "forecast_timestamp"])
@pytest.mark.parametrize("value", [None, "invalid", "2024-01-01", 123])
def test_build_rejects_missing_invalid_or_naive_timestamps(records, column, value):
    records[column] = pd.Series([value] * 3, dtype=object)
    with pytest.raises(ValueError, match=column):
        build_forecast_log(records)


def test_build_rejects_issuance_after_target(records):
    records.loc[0, "forecast_timestamp"] = (
        records.loc[0, "timestamp"] + pd.Timedelta("1h")
    )
    with pytest.raises(ValueError, match="forecast_timestamp"):
        build_forecast_log(records)


@pytest.mark.parametrize("column", ["prediction", "actual"])
@pytest.mark.parametrize("value", [np.inf, -np.inf, "bad", True, 1 + 2j])
def test_build_rejects_non_real_or_nonfinite_values(records, column, value):
    records[column] = [value] * 3
    with pytest.raises(ValueError, match=column):
        build_forecast_log(records)


def test_build_rejects_missing_predictions(records):
    records.loc[0, "prediction"] = np.nan
    with pytest.raises(ValueError, match="prediction"):
        build_forecast_log(records)


def test_build_rejects_error_overflow(records):
    records["actual"] = 1e200
    with pytest.raises(ValueError, match="non-finite"):
        build_forecast_log(records)


def test_build_rejects_duplicate_column_names(records):
    duplicated = pd.concat([records, records[["actual"]]], axis=1)
    with pytest.raises(ValueError, match="Duplicate column"):
        build_forecast_log(duplicated)


@pytest.mark.parametrize("suffix", [".parquet", ".csv"])
@pytest.mark.parametrize("missing_actual", [False, True])
def test_round_trip(records, tmp_path, suffix, missing_actual):
    if missing_actual:
        records["actual"] = pd.Series([pd.NA, 3.0, pd.NA], dtype="Float64")
    path = tmp_path / "logs" / "runs" / "run_20240102_120000" / f"forecasts{suffix}"
    assert write_forecast_log(records, path) == path
    result = read_forecast_log(path)
    pd.testing.assert_frame_equal(result, build_forecast_log(records))
    if missing_actual:
        columns = ["actual", "error", "squared_error", "absolute_error"]
        assert result.loc[[0, 2], columns].isna().all().all()


@pytest.mark.parametrize("suffix", [".parquet", ".csv"])
def test_shared_targets_and_string_model_versions_round_trip(records, tmp_path, suffix):
    records["timestamp"] = records.loc[0, "timestamp"]
    records["forecast_timestamp"] = records["timestamp"]
    records["model_version"] = ["001", "NA", "null"]
    path = tmp_path / f"shared_targets{suffix}"
    write_forecast_log(records, path)
    result = read_forecast_log(path)
    assert result["model_version"].tolist() == ["001", "NA", "null"]
    assert result["strategy"].tolist() == records["strategy"].tolist()


@pytest.mark.parametrize("suffix", [".parquet", ".csv"])
def test_all_actuals_unavailable_round_trip(records, tmp_path, suffix):
    records["actual"] = None
    path = tmp_path / f"pending{suffix}"
    write_forecast_log(records, path)
    result = read_forecast_log(path)
    columns = ["actual", "error", "squared_error", "absolute_error"]
    assert result[columns].isna().all().all()


@pytest.mark.parametrize("suffix", [".parquet", ".csv"])
def test_empty_log_round_trip(tmp_path, suffix):
    records = pd.DataFrame(columns=INPUT_COLUMNS)
    path = tmp_path / f"empty{suffix}"
    write_forecast_log(records, path)
    result = read_forecast_log(path)
    assert result.empty
    pd.testing.assert_frame_equal(result, build_forecast_log(records))


@pytest.mark.parametrize("column", LOG_COLUMNS)
def test_read_requires_complete_persisted_schema(records, tmp_path, column):
    path = tmp_path / "incomplete.csv"
    build_forecast_log(records).drop(columns=column).to_csv(path, index=False)
    with pytest.raises(ValueError, match=column):
        read_forecast_log(path)


@pytest.mark.parametrize("column", ["error", "squared_error", "absolute_error"])
@pytest.mark.parametrize("value", [999.0, np.nan])
def test_read_rejects_inconsistent_saved_errors(records, tmp_path, column, value):
    saved = build_forecast_log(records)
    saved.loc[0, column] = value
    path = tmp_path / "inconsistent.parquet"
    saved.to_parquet(path, index=False)
    with pytest.raises(ValueError, match=column):
        read_forecast_log(path)


def test_invalid_records_do_not_create_output(records, tmp_path):
    path = tmp_path / "new" / "forecasts.parquet"
    with pytest.raises(ValueError, match="strategy"):
        write_forecast_log(records.drop(columns="strategy"), path)
    assert not path.parent.exists()


def test_unsupported_formats_and_missing_file(records, tmp_path):
    path = tmp_path / "forecasts.json"
    with pytest.raises(ValueError, match="format"):
        write_forecast_log(records, path)
    with pytest.raises(ValueError, match="format"):
        read_forecast_log(path)
    with pytest.raises(FileNotFoundError):
        read_forecast_log(tmp_path / "missing.parquet")
