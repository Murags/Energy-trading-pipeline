"""Shared selection of optional exogenous predictor columns."""

from collections.abc import Sequence
import logging
from typing import Any

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_complex_dtype, is_numeric_dtype

from energy_trading_pipeline.preprocessing.validation import summarize_records


logger = logging.getLogger(__name__)

# Market and target columns are contemporaneous with the target, so they can
# never be passed through as exogenous predictors.
RESERVED_COLUMNS: frozenset[str] = frozenset(
    {"timestamp", "price_de", "price_fr", "spread"}
)
UNAVAILABLE_COLUMN_POLICY = "warn_and_continue_with_reduced_feature_set"
OPTIONAL_FEATURE_DTYPE = "float64"


def select_optional_features(
    df: pd.DataFrame,
    columns: Sequence[str],
    *,
    group: str,
    stage: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Return a sorted UTC copy plus metadata naming the usable predictors.

    Optional exogenous predictors are passed through from the aligned processed
    dataset rather than derived from the target, so the only decision here is
    which configured columns can actually be used. A column is usable when it is
    present, real numeric, and free of missing or non-finite values; usable
    columns are cast to ``float64`` so the artifact dtype is stable. Requested
    columns that are absent or unusable warn and are left out of
    ``selected_columns`` rather than failing, which leaves a documented reduced
    feature set. An empty ``columns`` sequence is valid and requests no optional
    features.

    Nothing is removed from the returned frame; the dataset builder selects the
    feature columns from ``selected_columns``. Require ``timestamp`` to hold
    parsed, timezone-aware instants; the input is not mutated.
    """
    requested = _validate_requested_columns(columns, group=group)
    summarize_records(df)

    result = df.copy()
    result["timestamp"] = result["timestamp"].dt.tz_convert("UTC")
    result = result.sort_values("timestamp").reset_index(drop=True)

    selected: list[str] = []
    missing: list[str] = []
    unusable: dict[str, str] = {}
    for column in requested:
        if column not in result.columns:
            missing.append(column)
            continue
        reason = _unusable_reason(result[column])
        if reason is not None:
            unusable[column] = reason
            continue
        result[column] = result[column].astype(OPTIONAL_FEATURE_DTYPE)
        selected.append(column)

    if missing:
        logger.warning(
            "Optional %s columns unavailable: %s; continuing with a reduced "
            "feature set (%s)",
            group,
            missing,
            stage,
        )
    for column, reason in unusable.items():
        logger.warning(
            "Optional %s column excluded: %s (%s, %s)", group, column, reason, stage
        )

    metadata = {
        "stage": stage,
        "group": group,
        "requested_columns": requested,
        "selected_columns": selected,
        "missing_columns": missing,
        "unusable_columns": unusable,
        "unavailable_column_policy": UNAVAILABLE_COLUMN_POLICY,
        "dtype": OPTIONAL_FEATURE_DTYPE,
        "output_rows": len(result),
    }
    return result, metadata


def _unusable_reason(values: pd.Series) -> str | None:
    """Return why an optional column cannot be a predictor, or None if it can."""
    dtype = values.dtype
    if not is_numeric_dtype(dtype) or is_bool_dtype(dtype) or is_complex_dtype(dtype):
        return f"dtype {dtype} is not real numeric"
    missing_count = int(values.isna().sum())
    if missing_count:
        return f"{missing_count} missing hourly values"
    if not np.isfinite(values.to_numpy(dtype=OPTIONAL_FEATURE_DTYPE)).all():
        return "non-finite values"
    return None


def _validate_requested_columns(columns: Any, *, group: str) -> list[str]:
    """Return the requested column names de-duplicated in configured order."""
    if isinstance(columns, (str, bytes)) or not isinstance(columns, Sequence):
        raise ValueError(
            f"{group} columns must be a sequence of column names; an empty "
            "sequence requests no optional features"
        )
    for column in columns:
        if not isinstance(column, str) or not column.strip():
            raise ValueError(f"Invalid {group} column name: {column!r}")
    requested = list(dict.fromkeys(columns))
    reserved = sorted(RESERVED_COLUMNS.intersection(requested))
    if reserved:
        raise ValueError(
            f"Optional {group} columns cannot include market or target columns: "
            f"{reserved}"
        )
    return requested
