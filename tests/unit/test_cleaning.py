"""Deterministic cleaning rules and persisted preprocessing audit records."""

import json
import logging
from pathlib import Path

import pandas as pd
import pytest

from energy_trading_pipeline.config.loader import load_config
from energy_trading_pipeline.data_ingestion.local_loader import load_local_data
from energy_trading_pipeline.preprocessing.cleaning import clean_records
from energy_trading_pipeline.preprocessing.timestamps import normalize_timestamps
from energy_trading_pipeline.preprocessing.validation import summarize_records


@pytest.fixture
def prices():
    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=3, freq="h", tz="UTC"),
            "price_de": [10.0, 20.0, 30.0],
            "temperature": [1.0, 2.0, 3.0],
        }
    )


@pytest.fixture
def options(tmp_path):
    return {
        "required_columns": ["price_de"],
        "optional_columns": ["temperature"],
        "duplicate_policy": "raise",
        "required_missing_policy": "raise",
        "run_dir": tmp_path / "logs" / "runs" / "run_20240101_000000",
        "dataset": "prices_de",
    }


def read_audit(options):
    path = options["run_dir"] / "preprocessing_log.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_clean_records_preserves_values_and_appends_audit(prices, options):
    original = prices.copy(deep=True)
    for _ in range(2):
        result, report = clean_records(prices, **options)
        pd.testing.assert_frame_equal(result, original)
        assert report["status"] == "completed"
        assert report["input_rows"] == report["output_rows"] == 3
        assert report["missing_counts"] == dict.fromkeys(prices.columns, 0)
        assert report["duplicate_count"] == 0
        assert report["stage"] == "preprocessing"
        assert report["run_id"] == options["run_dir"].name
        assert report["dataset"] == "prices_de"
        assert report["date_range"] == {
            "start": prices.timestamp.min().isoformat(),
            "end": prices.timestamp.max().isoformat(),
        }
        assert read_audit(options)[-1] == report
    pd.testing.assert_frame_equal(prices, original)
    assert len(read_audit(options)) == 2


def test_summary_counts_surplus_duplicates_and_all_column_nulls(prices):
    prices.loc[1, "temperature"] = None
    prices = pd.concat([prices, prices.iloc[[0]], prices.iloc[[0]]])
    original = prices.copy(deep=True)
    report = summarize_records(prices)
    assert report["duplicate_count"] == 2
    assert report["duplicate_timestamps"] == ["2024-01-01T00:00:00+00:00"]
    assert report["missing_counts"] == {
        "timestamp": 0,
        "price_de": 0,
        "temperature": 1,
    }
    pd.testing.assert_frame_equal(prices, original)


def test_duplicates_fail_and_log_before_required_missing_handling(prices, options):
    prices.loc[0, "price_de"] = None
    prices = pd.concat([prices, prices.iloc[[0]]])
    with pytest.raises(ValueError, match="Duplicate timestamps"):
        clean_records(prices, **options)
    report = read_audit(options)[0]
    assert report["status"] == "failed"
    assert report["duplicate_count"] == 1
    assert report["missing_counts"]["price_de"] == 2
    assert "Duplicate timestamps" in report["error"]


def test_keep_first_is_stable_sorted_and_does_not_mutate(prices, options):
    duplicate = prices.iloc[[0]].copy()
    duplicate["price_de"] = 999.0
    prices = pd.concat([prices.iloc[[2, 0]], duplicate, prices.iloc[[1]]])
    original = prices.copy(deep=True)
    result, report = clean_records(
        prices, **{**options, "duplicate_policy": "keep_first"}
    )
    assert result.price_de.tolist() == [10.0, 20.0, 30.0]
    assert result.index.tolist() == [0, 1, 2]
    assert report["duplicate_rows_removed"] == 1
    assert read_audit(options)[0] == report
    pd.testing.assert_frame_equal(prices, original)


def test_required_nulls_fail_with_counts_and_audit(prices, options):
    prices.loc[1, "price_de"] = None
    with pytest.raises(ValueError, match="Missing required values.*price_de"):
        clean_records(prices, **options)
    assert read_audit(options)[0]["missing_counts"]["price_de"] == 1


def test_drop_rows_handles_required_nulls_without_imputation(prices, options):
    prices.loc[1, "price_de"] = None
    original = prices.copy(deep=True)
    result, report = clean_records(
        prices, **{**options, "required_missing_policy": "drop_rows"}
    )
    assert result.price_de.tolist() == [10.0, 30.0]
    assert report["required_rows_removed"] == 1
    assert report["required_missing_timestamps"] == ["2024-01-01T01:00:00+00:00"]
    assert report["output_rows"] == 2
    pd.testing.assert_frame_equal(prices, original)


def test_duplicate_resolution_precedes_drop_rows(prices, options):
    duplicate = prices.iloc[[0]].copy()
    prices.loc[0, "price_de"] = None
    prices = pd.concat([prices, duplicate])
    result, report = clean_records(
        prices,
        **{
            **options,
            "duplicate_policy": "keep_first",
            "required_missing_policy": "drop_rows",
        },
    )
    assert result.price_de.tolist() == [20.0, 30.0]
    assert report["duplicate_rows_removed"] == report["required_rows_removed"] == 1


@pytest.mark.parametrize("policy", ["raise", "drop_rows"])
def test_absent_required_column_always_fails(prices, options, policy):
    with pytest.raises(ValueError, match="Missing required columns.*price_de"):
        clean_records(
            prices.drop(columns="price_de"),
            **{**options, "required_missing_policy": policy},
        )
    assert read_audit(options)[0]["status"] == "failed"


@pytest.mark.parametrize("missing", ["partial", "all", "absent"])
def test_optional_missingness_warns_and_documents_reduced_columns(
    prices, options, caplog, missing
):
    if missing == "absent":
        prices = prices.drop(columns="temperature")
    else:
        prices.loc[[0] if missing == "partial" else prices.index, "temperature"] = None
    with caplog.at_level(logging.WARNING):
        result, report = clean_records(prices, **options)
    assert "Optional columns excluded" in caplog.text
    assert "temperature" in caplog.text
    assert result.columns.tolist() == ["timestamp", "price_de"]
    assert len(result) == 3
    assert report["excluded_optional_columns"] == ["temperature"]
    assert report["retained_columns"] == ["timestamp", "price_de"]
    assert report["missing_optional_columns"] == (
        ["temperature"] if missing == "absent" else []
    )
    assert read_audit(options)[0] == report


def test_undeclared_extra_column_is_optional(prices, options, caplog):
    prices["load"] = None
    result, report = clean_records(prices, **options)
    assert "load" not in result
    assert report["excluded_optional_columns"] == ["load"]
    assert "load" in caplog.text


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("duplicate_policy", "keep_last", "duplicate_policy"),
        ("required_missing_policy", "interpolate", "required_missing_policy"),
        ("optional_columns", ["price_de"], "both required and optional"),
        ("required_columns", "price_de", "list of nonempty column names"),
        ("optional_columns", [None], "list of nonempty column names"),
    ],
)
def test_invalid_rules_fail_and_are_audited(prices, options, key, value, message):
    with pytest.raises(ValueError, match=message):
        clean_records(prices, **{**options, key: value})
    assert read_audit(options)[0]["status"] == "failed"


@pytest.mark.parametrize(
    "invalid", ["empty", "absent", "null", "unparsed", "naive", "duplicate_columns"]
)
def test_invalid_input_fails_and_is_audited(prices, options, invalid):
    if invalid == "empty":
        prices = prices.iloc[:0]
    elif invalid == "absent":
        prices = prices.drop(columns="timestamp")
    elif invalid == "null":
        prices.loc[0, "timestamp"] = pd.NaT
    elif invalid == "unparsed":
        prices["timestamp"] = prices.timestamp.astype(str)
    elif invalid == "naive":
        prices["timestamp"] = prices.timestamp.dt.tz_localize(None)
    else:
        prices.columns = ["timestamp", "price_de", "price_de"]
    with pytest.raises(ValueError):
        clean_records(prices, **options)
    assert read_audit(options)[0]["status"] == "failed"


def test_dropping_all_rows_fails_with_audited_decision(prices, options):
    prices["price_de"] = None
    with pytest.raises(ValueError, match="No records remain"):
        clean_records(prices, **{**options, "required_missing_policy": "drop_rows"})
    report = read_audit(options)[0]
    assert report["required_rows_removed"] == 3
    assert report["status"] == "failed"


def test_dst_distinct_instants_are_not_duplicates(prices, options):
    prices["timestamp"] = [
        "2024-10-27T02:00:00+02:00",
        "2024-10-27T02:00:00+01:00",
        "2024-10-27T03:00:00+01:00",
    ]
    normalized, _ = normalize_timestamps(prices)
    result, report = clean_records(normalized, **options)
    assert report["duplicate_count"] == 0
    assert len(result) == 3


def test_equivalent_offsets_are_duplicate_instants(prices, options):
    prices["timestamp"] = [
        "2024-01-01T00:00:00Z",
        "2024-01-01T01:00:00+01:00",
        "2024-01-01T02:00:00Z",
    ]
    normalized, _ = normalize_timestamps(prices)
    with pytest.raises(ValueError, match="Duplicate timestamps"):
        clean_records(normalized, **options)
    assert read_audit(options)[0]["duplicate_count"] == 1


def test_multiple_required_nulls_remove_each_row_once(prices, options):
    prices["price_fr"] = [None, None, 5.0]
    prices.loc[0, "price_de"] = None
    result, report = clean_records(
        prices,
        **{
            **options,
            "required_columns": ["price_de", "price_fr"],
            "required_missing_policy": "drop_rows",
        },
    )
    assert len(result) == 1
    assert report["required_rows_removed"] == 2
    assert report["missing_counts"]["price_fr"] == 2


def test_log_write_failure_prevents_success(prices, options, monkeypatch):
    def fail_open(*args, **kwargs):
        raise OSError("Audit storage unavailable")

    monkeypatch.setattr(Path, "open", fail_open)
    with pytest.raises(OSError, match="Audit storage unavailable"):
        clean_records(prices, **options)


def test_fixture_cleaning_uses_loaded_yaml_policies(options):
    root = Path(__file__).resolve().parents[2]
    rules = load_config(root / "configs" / "experiment.yaml")["data"]["cleaning"]
    assert rules == {"duplicate_policy": "raise", "required_missing_policy": "raise"}
    df = load_local_data(root / "tests" / "fixtures" / "sample_prices_de.csv")
    normalized, _ = normalize_timestamps(df)
    with pytest.raises(ValueError, match="Duplicate timestamps"):
        clean_records(normalized, **{**options, **rules, "optional_columns": []})
    result, report = clean_records(
        normalized,
        **{**options, **rules, "optional_columns": [], "duplicate_policy": "keep_first"},
    )
    assert len(result) == 192
    assert report["duplicate_count"] == report["duplicate_rows_removed"] == 1
