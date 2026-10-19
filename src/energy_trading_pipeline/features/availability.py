"""Price/calendar day-ahead preparation under an explicit conservative convention."""

from collections.abc import Mapping
import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from energy_trading_pipeline.backtesting.splitter import (
    day_ahead_issuance,
    generate_backtest_windows_from_config,
)
from energy_trading_pipeline.config.paths import (
    get_default_base_dir,
    resolve_paths_config,
)
from energy_trading_pipeline.data_ingestion.local_loader import load_local_data
from energy_trading_pipeline.features.dataset_builder import build_feature_dataset
from energy_trading_pipeline.preprocessing.spread import calculate_spread

PROVENANCE_COLUMNS = (
    "forecast_timestamp",
    "feature_available_at",
    "actual_available_at",
)
LIMITATIONS = (
    "Historical snapshot prices may include later revisions; publication vintages are "
    "not reconstructed. Usable-after is deliberately delayed until delivery end, "
    "not an observed publication time. ERA5 and grid predictors are excluded."
)


def availability_contract(config: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the supported predictor and timing settings and return provenance."""
    if not isinstance(config, Mapping):
        raise ValueError("Day-ahead config must be a mapping")
    settings = config.get("backtest")
    features = config.get("features")
    if not isinstance(settings, Mapping) or not isinstance(features, Mapping):
        raise ValueError("backtest and features must be configuration mappings")
    model = config.get("model")
    if not isinstance(model, Mapping):
        raise ValueError("model must be a configuration mapping")
    if settings.get("mode") != "day_ahead":
        raise ValueError("Availability preparation requires backtest.mode: day_ahead")
    if model.get("target_column", "spread") != "spread":
        raise ValueError("Day-ahead target_column must be spread")
    generate_backtest_windows_from_config(config)
    allowed = {
        "lag_hours",
        "rolling_window_hours",
        "rolling_shift_hours",
        "calendar_timezone",
        "calendar_features",
        "weather_columns",
        "grid_columns",
        "holiday_dates",
    }
    if set(features) - allowed:
        raise ValueError("Unsupported availability feature configuration")
    if any(
        features.get(key)
        for key in ("weather_columns", "grid_columns", "holiday_dates")
    ):
        raise ValueError(
            "Day-ahead preparation supports price and calendar predictors only"
        )
    if features.get("calendar_timezone") != settings["issue_timezone"]:
        raise ValueError("calendar_timezone must match issue_timezone")
    calendar = features.get("calendar_features")
    if (
        not isinstance(calendar, list)
        or any(not isinstance(name, str) for name in calendar)
        or len(set(calendar)) != len(calendar)
    ):
        raise ValueError("calendar_features must be unique names")
    if set(calendar) != {"hour", "day_of_week", "month", "is_weekend"}:
        raise ValueError(
            "Day-ahead calendar_features must be hour, day_of_week, month, is_weekend"
        )
    for key in ("lag_hours", "rolling_window_hours"):
        values = features.get(key)
        if (
            not isinstance(values, list)
            or not values
            or any(
                isinstance(v, bool) or not isinstance(v, int) or v < 1 for v in values
            )
        ):
            raise ValueError(f"{key} must be a nonempty positive integer list")
    shift = features.get("rolling_shift_hours")
    if isinstance(shift, bool) or not isinstance(shift, int) or shift < 1:
        raise ValueError("rolling_shift_hours must be a positive integer")
    if min(features["rolling_window_hours"]) < 2:
        raise ValueError("rolling_window_hours must be at least 2")
    return {
        "mode": "day_ahead",
        "issue_hour": settings["issue_hour"],
        "issue_timezone": settings["issue_timezone"],
        "price_usable_after": "delivery_end_timestamp_plus_1_hour",
        "features": dict(features),
        "limitations": LIMITATIONS,
    }


def build_availability_dataset(
    df: pd.DataFrame,
    config: Mapping[str, Any],
    *,
    source_dataset: str | Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build predictors and enforce their dependencies at each original issuance."""
    contract = availability_contract(config)
    prices = calculate_spread(df)
    if (prices["timestamp"] != prices["timestamp"].dt.floor("h")).any():
        raise ValueError("Prices must be aligned to whole UTC hours")
    features = config["features"]
    result, metadata = build_feature_dataset(
        prices, features, source_dataset=source_dataset
    )
    warmup = max(
        max(features["lag_hours"]),
        features["rolling_shift_hours"] + max(features["rolling_window_hours"]) - 1,
    )
    if len(prices) - len(result) != warmup:
        raise ValueError("Only leading feature warmup may be dropped")
    dependency_lag = min(min(features["lag_hours"]), features["rolling_shift_hours"])
    dates = result["timestamp"].dt.tz_convert(contract["issue_timezone"]).dt.date
    issuance_by_date = {
        day: day_ahead_issuance(day, config["backtest"]) for day in dates.unique()
    }
    result["forecast_timestamp"] = pd.to_datetime(dates.map(issuance_by_date), utc=True)
    result["actual_available_at"] = result["timestamp"] + pd.Timedelta(hours=1)
    result["feature_available_at"] = result["timestamp"] - pd.Timedelta(
        hours=dependency_lag - 1
    )
    if (result["feature_available_at"] > result["forecast_timestamp"]).any():
        raise ValueError(
            "Forecast features are unavailable at original issuance; increase lag/shift"
        )
    metadata["availability_contract"] = contract
    metadata["warmup_rows_dropped"] = warmup
    metadata["excluded_columns"] += list(PROVENANCE_COLUMNS)
    return result, metadata


def validate_availability_frame(
    frame: pd.DataFrame, config: Mapping[str, Any], columns: list[str]
) -> None:
    """Check supplied provenance against the configured dependency convention."""
    contract = availability_contract(config)
    if any(name not in frame for name in PROVENANCE_COLUMNS):
        raise ValueError("Missing day-ahead availability provenance")
    expected_columns = (
        [
            f"{column}_lag_{lag}"
            for column in ("spread", "price_de", "price_fr")
            for lag in sorted(set(config["features"]["lag_hours"]))
        ]
        + [
            f"{column}_rolling_{statistic}_{window}"
            for column in ("spread", "price_de", "price_fr")
            for window in sorted(set(config["features"]["rolling_window_hours"]))
            for statistic in ("mean", "std")
        ]
        + ["hour", "day_of_week", "month", "is_weekend"]
    )
    if columns != expected_columns:
        raise ValueError(
            "Configured feature_columns do not match prepared day-ahead predictors"
        )
    if any(name not in frame for name in ["timestamp", "spread", *columns]):
        raise ValueError("Missing day-ahead target or predictor columns")
    for name in ("timestamp", *PROVENANCE_COLUMNS):
        if (
            not isinstance(frame[name].dtype, pd.DatetimeTZDtype)
            or frame[name].isna().any()
        ):
            raise ValueError(
                f"{name} must contain timezone-aware timestamps without NaT"
            )
    for name in ["spread", *columns]:
        if (
            not pd.api.types.is_numeric_dtype(frame[name])
            or not np.isfinite(frame[name].to_numpy(dtype=float)).all()
        ):
            raise ValueError(f"{name} must contain finite numeric values")
    times = pd.to_datetime(frame["timestamp"], utc=True)
    features = config["features"]
    lag = min(min(features["lag_hours"]), features["rolling_shift_hours"])
    expected = {
        "actual_available_at": times + pd.Timedelta(hours=1),
        "feature_available_at": times - pd.Timedelta(hours=lag - 1),
    }
    dates = times.dt.tz_convert(contract["issue_timezone"]).dt.date
    lookup = {d: day_ahead_issuance(d, config["backtest"]) for d in dates.unique()}
    expected["forecast_timestamp"] = pd.to_datetime(dates.map(lookup), utc=True)
    for name, values in expected.items():
        if not pd.to_datetime(frame[name], utc=True).equals(values):
            raise ValueError(f"Invalid day-ahead {name} provenance")
    if (expected["feature_available_at"] > expected["forecast_timestamp"]).any():
        raise ValueError("Forecast features unavailable at original issuance")


def prepare_configured_day_ahead(
    config: Mapping[str, Any], *, config_file_path: Path
) -> dict[str, Any]:
    """Load cached paired prices and exclusively write features plus metadata."""
    availability_contract(config)
    paths_config = config.get("paths")
    if not isinstance(paths_config, Mapping) or any(
        not isinstance(paths_config.get(key), (str, Path))
        or not str(paths_config[key]).strip()
        for key in ("processed_data_parquet_path", "feature_data_parquet_path")
    ):
        raise ValueError("Preparation requires processed and feature dataset paths")
    if any(not isinstance(value, (str, Path)) for value in paths_config.values()):
        raise ValueError("All configured paths must be strings or Path objects")
    paths = resolve_paths_config(dict(paths_config), get_default_base_dir())
    source = paths["processed_data_parquet_path"]
    output = paths["feature_data_parquet_path"]
    sidecar = output.with_suffix(".metadata.yaml")
    if output.suffix != ".parquet":
        raise ValueError("Feature output must be Parquet")
    if output.exists() or sidecar.exists():
        raise FileExistsError(
            "Day-ahead artifacts already exist; choose new output paths"
        )
    frame = load_local_data(source)
    if not isinstance(frame["timestamp"].dtype, pd.DatetimeTZDtype):
        raise ValueError("Cached price timestamps must be timezone-aware")
    result, metadata = build_availability_dataset(frame, config, source_dataset=source)
    validate_availability_frame(result, config, config["backtest"]["feature_columns"])
    metadata["config_file_path"] = str(config_file_path.resolve())
    metadata["source_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    metadata["artifact_paths"] = {
        "feature_dataset": str(output),
        "metadata": str(sidecar),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive handles prevent a racing writer from replacing either artifact.
    with sidecar.open("x", encoding="utf-8") as metadata_handle:
        with output.open("xb") as data_handle:
            result.to_parquet(data_handle, index=False)
        metadata["feature_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
        yaml.safe_dump(metadata, metadata_handle, sort_keys=False)
    return metadata
