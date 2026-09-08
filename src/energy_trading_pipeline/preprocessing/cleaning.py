"""Explicit missing/duplicate cleaning with append-only per-run audit records."""

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from energy_trading_pipeline.preprocessing.validation import summarize_records


logger = logging.getLogger(__name__)


def clean_records(
    df: pd.DataFrame,
    *,
    required_columns: list[str],
    optional_columns: list[str],
    duplicate_policy: str,
    required_missing_policy: str,
    run_dir: Path,
    dataset: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Return a cleaned copy and persist its audit to preprocessing_log.jsonl.

    Consume normalized timestamps. Resolve duplicates first (``raise`` or stable
    ``keep_first``), then required nulls (``raise`` or ``drop_rows``). Timestamp
    is always required and cannot be null. Absent required columns always fail.
    Optional columns with any input nulls are excluded with a warning; undeclared
    extra columns are optional too. No values are imputed or hours inserted.

    Policies must be supplied explicitly, e.g. from YAML ``data.cleaning``.
    Each call appends one JSON object, including validation failures. Filesystem
    errors propagate: a successful result must never lack its audit record.
    """
    log_path = Path(run_dir) / "preprocessing_log.jsonl"
    report: dict[str, Any] = {
        "stage": "preprocessing",
        "run_id": Path(run_dir).name,
        "dataset": dataset,
        "status": "failed",
        "input_rows": len(df),
        "required_columns": required_columns,
        "optional_columns": optional_columns,
        "duplicate_policy": duplicate_policy,
        "required_missing_policy": required_missing_policy,
        "optional_missing_policy": "drop_columns",
        "duplicate_rows_removed": 0,
        "required_rows_removed": 0,
    }
    try:
        report.update(summarize_records(df))
        if duplicate_policy not in ("raise", "keep_first"):
            raise ValueError("duplicate_policy must be 'raise' or 'keep_first'")
        if required_missing_policy not in ("raise", "drop_rows"):
            raise ValueError("required_missing_policy must be 'raise' or 'drop_rows'")
        for name, columns in (
            ("required_columns", required_columns),
            ("optional_columns", optional_columns),
        ):
            if not isinstance(columns, list) or any(
                not isinstance(column, str) or not column for column in columns
            ):
                raise ValueError(f"{name} must be a list of nonempty column names")
        required = sorted(set(required_columns) | {"timestamp"})
        report["required_columns"] = required
        overlap = sorted(set(required) & set(optional_columns))
        if overlap:
            raise ValueError(f"Columns cannot be both required and optional: {overlap}")
        absent = sorted(set(required) - set(df.columns))
        if absent:
            raise ValueError(f"Missing required columns: {absent}")

        optional = sorted((set(optional_columns) | set(df.columns)) - set(required))
        report["missing_optional_columns"] = sorted(set(optional) - set(df.columns))
        excluded = [
            column
            for column in optional
            if column not in df.columns or report["missing_counts"][column] > 0
        ]
        report["excluded_optional_columns"] = excluded
        if excluded:
            logger.warning(
                "Optional columns excluded due to missing columns/values: %s "
                "(stage=preprocessing, run_id=%s, dataset=%s)",
                excluded,
                report["run_id"],
                dataset,
            )

        if report["duplicate_count"] and duplicate_policy == "raise":
            raise ValueError(
                f"Duplicate timestamps detected: {report['duplicate_timestamps']}"
            )
        result = df.copy()
        result["timestamp"] = result["timestamp"].dt.tz_convert("UTC")
        result = result.sort_values("timestamp", kind="stable")
        if duplicate_policy == "keep_first":
            result = result.drop_duplicates(subset="timestamp", keep="first")
            report["duplicate_rows_removed"] = len(df) - len(result)

        missing_required = result[required].isna().any(axis=1)
        report["required_missing_timestamps"] = [
            value.isoformat() for value in result.loc[missing_required, "timestamp"]
        ]
        if missing_required.any():
            if required_missing_policy == "raise":
                counts = result[required].isna().sum()
                raise ValueError(
                    f"Missing required values: {counts[counts > 0].to_dict()}"
                )
            report["required_rows_removed"] = int(missing_required.sum())
            result = result.loc[~missing_required]
        if result.empty:
            raise ValueError("No records remain after required missing-value cleaning")
        result = result.drop(columns=excluded, errors="ignore").reset_index(drop=True)
        report.update(
            status="completed",
            output_rows=len(result),
            retained_columns=result.columns.tolist(),
        )
    except ValueError as exc:
        report["error"] = str(exc)
        logger.error(
            "Record cleaning failed (stage=preprocessing, run_id=%s, dataset=%s): %s",
            report["run_id"],
            dataset,
            exc,
        )
        raise
    finally:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(report, allow_nan=False) + "\n")

    return result, report
