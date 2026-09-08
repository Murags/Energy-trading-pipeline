"""Canonical feature dataset assembly and artifact persistence."""

from collections.abc import Mapping
import logging
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from energy_trading_pipeline.features.calendar_features import (
    DEFAULT_CALENDAR_FEATURES,
    build_calendar_features,
)
from energy_trading_pipeline.features.grid_features import build_grid_features
from energy_trading_pipeline.features.lag_features import build_lag_features
from energy_trading_pipeline.features.rolling_features import build_rolling_features
from energy_trading_pipeline.features.weather_features import build_weather_features


logger = logging.getLogger(__name__)

TARGET_COLUMN = "spread"
# Fixed stage order so the artifact is reproducible from processed data and
# config alone. Target-derived features come first, then exogenous predictors.
FEATURE_STAGE_ORDER: tuple[str, ...] = (
    "lag",
    "rolling",
    "calendar",
    "weather",
    "grid",
)
REQUIRED_FEATURE_CONFIG_KEYS: tuple[str, ...] = ("lag_hours", "rolling_window_hours")
OPTIONAL_FEATURE_CONFIG_KEYS: tuple[str, ...] = (
    "calendar_features",
    "holiday_dates",
    "weather_columns",
    "grid_columns",
)
# At the target timestamp these are the target: spread is price_de - price_fr,
# so neither price nor the spread itself may be a feature. The spread is kept in
# the artifact as the target column, not as a predictor.
NON_FEATURE_COLUMNS: tuple[str, ...] = (
    "timestamp",
    "price_de",
    "price_fr",
    TARGET_COLUMN,
)
INCOMPLETE_ROW_POLICY = "drop_rows_without_a_complete_feature_vector"
PARQUET_SUFFIX = ".parquet"
METADATA_SUFFIX = ".metadata.yaml"


def build_feature_dataset(
    df: pd.DataFrame,
    feature_config: Mapping[str, Any],
    *,
    source_dataset: str | Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Assemble the canonical feature dataset and its metadata.

    Run the lag, rolling, calendar, weather, and grid builders in a fixed order
    over a processed hourly dataset, then keep only ``timestamp``, the
    ``spread`` target, and the generated feature columns. Contemporaneous
    ``price_de`` and ``price_fr`` are dropped rather than passed through: at the
    target timestamp they are the target. The input is not mutated.

    ``feature_config`` is the ``features`` section of the experiment config.
    ``lag_hours`` and ``rolling_window_hours`` are required; the calendar,
    holiday, weather, and grid keys are optional, and an absent exogenous key
    requests no predictors from that group rather than guessing one. Unknown
    keys warn so a typo does not silently fall back to a default.

    Rows without a complete feature vector, which are the leading hours that lack
    enough history for the configured lags and windows, are dropped so every
    retained row is usable by modelling and every strategy compares on identical
    rows. The count is reported as ``incomplete_rows_dropped``. Pass the path of
    the processed dataset as ``source_dataset``; provenance is caller supplied and
    the file is not reopened.
    """
    resolved = _resolve_feature_config(feature_config)
    source = str(source_dataset).strip()
    if not source:
        raise ValueError("source_dataset must be a nonempty processed dataset path")
    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Missing required target column: {TARGET_COLUMN}")

    stages: dict[str, dict[str, Any]] = {}
    result, stages["lag"] = build_lag_features(df, resolved["lag_hours"])
    result, stages["rolling"] = build_rolling_features(
        result, resolved["rolling_window_hours"]
    )
    result, stages["calendar"] = build_calendar_features(
        result,
        features=resolved["calendar_features"],
        holiday_dates=resolved["holiday_dates"],
    )
    result, stages["weather"] = build_weather_features(
        result, columns=resolved["weather_columns"]
    )
    result, stages["grid"] = build_grid_features(
        result, columns=resolved["grid_columns"]
    )

    feature_columns = _collect_feature_columns(stages)
    source_rows = len(result)
    source_range = _date_range(result["timestamp"])
    result = result[["timestamp", TARGET_COLUMN, *feature_columns]]
    result = result.dropna(subset=[TARGET_COLUMN, *feature_columns]).reset_index(
        drop=True
    )
    if result.empty:
        raise ValueError(
            f"No row of the {source_rows} processed rows has a complete feature "
            "vector; extend the processed date range or reduce "
            "features.lag_hours and features.rolling_window_hours"
        )

    metadata = {
        "stage": "features.dataset",
        "target_column": TARGET_COLUMN,
        "feature_columns": feature_columns,
        "source_processed_dataset": source,
        "source_date_range": source_range,
        "source_rows": source_rows,
        "date_range": _date_range(result["timestamp"]),
        "timezone": "UTC",
        "feature_config": _applied_feature_config(stages),
        "excluded_columns": [
            column for column in NON_FEATURE_COLUMNS if column != TARGET_COLUMN
        ],
        "incomplete_row_policy": INCOMPLETE_ROW_POLICY,
        "incomplete_rows_dropped": source_rows - len(result),
        "output_rows": len(result),
        "feature_stages": {name: stages[name] for name in FEATURE_STAGE_ORDER},
    }
    logger.info(
        "Feature dataset built: rows=%d, features=%d, dropped_incomplete=%d, "
        "start=%s, end=%s",
        len(result),
        len(feature_columns),
        metadata["incomplete_rows_dropped"],
        metadata["date_range"]["start"],
        metadata["date_range"]["end"],
    )
    return result, metadata


def save_feature_dataset(
    df: pd.DataFrame,
    output_path: Path,
    *,
    feature_config: Mapping[str, Any],
    source_dataset: str | Path,
) -> tuple[Path, Path]:
    """Build the feature dataset and write Parquet plus a metadata sidecar.

    Pass the configured feature dataset path, normally
    ``paths.feature_data_parquet_path`` (``data/features/feature_dataset.parquet``).
    The metadata is written next to it as ``<name>.metadata.yaml`` and records the
    target column, feature columns, source processed dataset, date range, and the
    resolved feature config. Existing artifacts at these paths are replaced.
    Return the Parquet and metadata paths.
    """
    output_path = Path(output_path)
    if output_path.suffix.lower() != PARQUET_SUFFIX:
        raise ValueError(
            f"Feature dataset output_path must have a {PARQUET_SUFFIX} suffix"
        )
    result, metadata = build_feature_dataset(
        df, feature_config, source_dataset=source_dataset
    )
    metadata_path = output_path.with_suffix(METADATA_SUFFIX)
    metadata["artifact_paths"] = {
        "feature_dataset": str(output_path),
        "metadata": str(metadata_path),
    }
    metadata_text = yaml.safe_dump(metadata, sort_keys=False)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(output_path, index=False)
    metadata_path.write_text(metadata_text, encoding="utf-8")
    return output_path, metadata_path


def _applied_feature_config(
    stages: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Return the normalized feature settings each stage actually applied."""
    return {
        "lag_hours": stages["lag"]["lag_hours"],
        "lag_columns": stages["lag"]["source_columns"],
        "rolling_window_hours": stages["rolling"]["window_hours"],
        "rolling_columns": stages["rolling"]["source_columns"],
        "calendar_features": stages["calendar"]["requested_features"],
        "holiday_dates": stages["calendar"]["holiday_dates"],
        "weather_columns": stages["weather"]["requested_columns"],
        "grid_columns": stages["grid"]["requested_columns"],
    }


def _collect_feature_columns(stages: Mapping[str, Mapping[str, Any]]) -> list[str]:
    """Return the generated feature columns in fixed stage order."""
    feature_columns: list[str] = []
    for name in FEATURE_STAGE_ORDER:
        metadata = stages[name]
        # Optional groups report the columns they could actually use.
        columns = metadata.get("generated_columns", metadata.get("selected_columns"))
        feature_columns.extend(columns)
    duplicates = sorted(
        {column for column in feature_columns if feature_columns.count(column) > 1}
    )
    if duplicates:
        raise ValueError(f"Feature columns collide across stages: {duplicates}")
    reserved = [column for column in feature_columns if column in NON_FEATURE_COLUMNS]
    if reserved:
        raise ValueError(f"Feature columns cannot include: {sorted(set(reserved))}")
    return feature_columns


def _date_range(timestamps: pd.Series) -> dict[str, str]:
    """Return the inclusive UTC bounds of a chronologically ordered series."""
    return {
        "start": timestamps.iloc[0].isoformat(),
        "end": timestamps.iloc[-1].isoformat(),
    }


def _resolve_feature_config(feature_config: Any) -> dict[str, Any]:
    """Return the feature settings actually applied, so a run is reproducible."""
    if not isinstance(feature_config, Mapping):
        raise ValueError(
            "feature_config must be the 'features' mapping of the experiment config"
        )
    missing = [
        key for key in REQUIRED_FEATURE_CONFIG_KEYS if key not in feature_config
    ]
    if missing:
        raise ValueError(f"Missing required feature config key(s): {missing}")
    known = set(REQUIRED_FEATURE_CONFIG_KEYS) | set(OPTIONAL_FEATURE_CONFIG_KEYS)
    unknown = sorted(set(feature_config) - known)
    if unknown:
        logger.warning(
            "Ignoring unrecognized feature config key(s): %s; supported: %s",
            unknown,
            sorted(known),
        )
    return {
        "lag_hours": feature_config["lag_hours"],
        "rolling_window_hours": feature_config["rolling_window_hours"],
        "calendar_features": feature_config.get(
            "calendar_features", list(DEFAULT_CALENDAR_FEATURES)
        ),
        "holiday_dates": feature_config.get("holiday_dates", []),
        # An absent exogenous key requests nothing rather than guessing which
        # optional variables a processed dataset happens to carry.
        "weather_columns": feature_config.get("weather_columns", []),
        "grid_columns": feature_config.get("grid_columns", []),
    }
