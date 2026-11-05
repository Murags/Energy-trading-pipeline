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
from energy_trading_pipeline.features.rolling_features import STD_DDOF
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
PERFECT_FORESIGHT_LIMITATION = (
    "PERFECT FORESIGHT BOUNDING EXPERIMENT, NOT AN OPERATIONAL FORECAST. Weather "
    "predictors are ERA5 reanalysis for the delivery hour itself, which no forecaster "
    "holds at issuance. Results bound what weather could contribute if forecasts were "
    "exact, and overstate achievable accuracy by the cost of weather forecast error. "
    "They must never be reported as day-ahead forecast accuracy."
)
PERFECT_FORESIGHT_KEY = "perfect_foresight_weather"
# Regulation (EU) 543/2013 Art. 14(1)(c)/(d): transmission system operators
# transmit day-ahead generation forecasts for the following day to the ENTSO-E
# Transparency Platform by 18:00 local time on the preceding day.
PUBLISHED_FORECAST_DEADLINE_HOUR = 18
PUBLISHED_FORECAST_BASIS = (
    "Day-ahead TSO generation forecast for the following day under Regulation "
    "(EU) 543/2013 Art. 14(1)(c)/(d), published by 18:00 local time on the "
    "preceding day and not retrospectively updated, so the stored value is the "
    "original day-ahead vintage available at issuance."
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
        "issuance_window_hours",
        "calendar_timezone",
        "calendar_features",
        "weather_columns",
        "grid_columns",
        "holiday_dates",
        "day_ahead_forecast_columns",
        PERFECT_FORESIGHT_KEY,
    }
    if set(features) - allowed:
        raise ValueError("Unsupported availability feature configuration")
    published = features.get("day_ahead_forecast_columns") or []
    if published and (
        not isinstance(published, list)
        or any(not isinstance(name, str) or not name.strip() for name in published)
        or len(set(published)) != len(published)
    ):
        raise ValueError("day_ahead_forecast_columns must be unique nonempty names")
    if published and settings["issue_hour"] < PUBLISHED_FORECAST_DEADLINE_HOUR:
        # Art. 14(1)(c)/(d) of Regulation (EU) 543/2013 only guarantees these
        # forecasts by 18:00 on the preceding day; issuing earlier would use a
        # publication that is not yet certain to exist.
        raise ValueError(
            "day_ahead_forecast_columns require backtest.issue_hour of at least "
            f"{PUBLISHED_FORECAST_DEADLINE_HOUR}, the regulated publication "
            "deadline on the preceding day"
        )
    perfect_foresight = features.get(PERFECT_FORESIGHT_KEY, False)
    if not isinstance(perfect_foresight, bool):
        raise ValueError(f"features.{PERFECT_FORESIGHT_KEY} must be true or false")
    weather = features.get("weather_columns") or []
    if any(features.get(key) for key in ("grid_columns", "holiday_dates")):
        raise ValueError(
            "Day-ahead preparation supports price and calendar predictors only"
        )
    if weather and not perfect_foresight:
        # Operational day-ahead has no usable weather source yet: reanalysis for
        # the delivery hour is unknown at issuance, and lagging it only restates
        # stale price history. Weather is therefore opt-in and clearly labelled.
        raise ValueError(
            "Day-ahead weather predictors require "
            f"features.{PERFECT_FORESIGHT_KEY}: true, which marks the run as a "
            "bounding experiment rather than an operational forecast"
        )
    if perfect_foresight and not weather:
        raise ValueError(
            f"features.{PERFECT_FORESIGHT_KEY} requires weather_columns to bound"
        )
    if weather and (
        any(not isinstance(name, str) or not name.strip() for name in weather)
        or len(set(weather)) != len(weather)
    ):
        raise ValueError("weather_columns must be unique nonempty names")
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
    issuance_windows = features.get("issuance_window_hours")
    if issuance_windows is not None and (
        not isinstance(issuance_windows, list)
        or not issuance_windows
        or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 2
            for value in issuance_windows
        )
        or len(set(issuance_windows)) != len(issuance_windows)
    ):
        raise ValueError(
            "issuance_window_hours must be unique integers of at least 2"
        )
    contract = {
        "mode": "day_ahead",
        "issue_hour": settings["issue_hour"],
        "issue_timezone": settings["issue_timezone"],
        "price_usable_after": "delivery_end_timestamp_plus_1_hour",
        "features": dict(features),
        "limitations": LIMITATIONS,
    }
    if published:
        contract["day_ahead_forecast_basis"] = PUBLISHED_FORECAST_BASIS
        contract["day_ahead_forecast_deadline_hour"] = PUBLISHED_FORECAST_DEADLINE_HOUR
    if perfect_foresight:
        contract["evaluation_purpose"] = "perfect_foresight_bound_not_operational"
        contract["weather_usable_after"] = "delivery_hour_itself_UNAVAILABLE_AT_ISSUANCE"
        contract["limitations"] = f"{LIMITATIONS} {PERFECT_FORESIGHT_LIMITATION}"
    return contract


ISSUANCE_SOURCE_COLUMNS = ("spread", "price_de", "price_fr")


def issuance_feature_columns(windows: list[int]) -> list[str]:
    """Name the issuance-relative predictors in a stable, configuration-driven order.

    No configured window means the feature is disabled and contributes no
    columns at all, including the last-usable-hour values.
    """
    if not windows:
        return []
    names = [
        f"{column}_issuance_{statistic}_{window}"
        for column in ISSUANCE_SOURCE_COLUMNS
        for window in sorted(set(windows))
        for statistic in ("mean", "std")
    ]
    return names + [f"{column}_issuance_last" for column in ISSUANCE_SOURCE_COLUMNS]


def build_issuance_features(
    prices: pd.DataFrame, config: Mapping[str, Any], issuances: pd.Series
) -> pd.DataFrame:
    """Summarize the price history usable at each issuance, indexed by issuance.

    A day-ahead block is issued once, so its market-state predictors are defined
    relative to that instant rather than to each delivery hour. Per-hour lags
    must be long enough for the *last* hour of the block, which throws away
    information the forecaster genuinely holds for the earlier hours.

    The window ends at the newest hour whose actual is usable at issuance, which
    under this protocol is ``issuance - 1 hour``. Windows must be complete;
    issuances without full history are returned as missing and dropped upstream
    rather than aggregated over a shorter span.
    """
    windows = sorted(set(config["features"]["issuance_window_hours"]))
    series = prices.set_index("timestamp").sort_index()
    if series.index.has_duplicates:
        raise ValueError("Prices must have unique hourly timestamps")
    rows = {}
    for issuance in sorted(pd.unique(issuances)):
        issued = pd.Timestamp(issuance)
        newest = issued - pd.Timedelta(hours=1)
        row: dict[str, float] = {}
        for window in windows:
            start = newest - pd.Timedelta(hours=window - 1)
            block = series.loc[(series.index >= start) & (series.index <= newest)]
            # A short window would silently become a different statistic.
            complete = len(block) == window
            for column in ISSUANCE_SOURCE_COLUMNS:
                values = block[column]
                row[f"{column}_issuance_mean_{window}"] = (
                    float(values.mean()) if complete else float("nan")
                )
                row[f"{column}_issuance_std_{window}"] = (
                    float(values.std(ddof=STD_DDOF)) if complete else float("nan")
                )
        for column in ISSUANCE_SOURCE_COLUMNS:
            row[f"{column}_issuance_last"] = (
                float(series.at[newest, column])
                if newest in series.index
                else float("nan")
            )
        rows[issued] = row
    frame = pd.DataFrame.from_dict(rows, orient="index")
    frame.index.name = "forecast_timestamp"
    return frame.loc[:, issuance_feature_columns(windows)]


def build_availability_dataset(
    df: pd.DataFrame,
    config: Mapping[str, Any],
    *,
    source_dataset: str | Path,
    weather: pd.DataFrame | None = None,
    day_ahead_forecasts: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build predictors and enforce their dependencies at each original issuance.

    Under ``features.perfect_foresight_weather`` the supplied weather frame is
    joined at the delivery hour itself. ``feature_available_at`` then records
    that delivery hour truthfully, so the artifact states plainly that these
    predictors are not held at issuance; only a run that declares the bound may
    accept them.
    """
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
    issuance_windows = features.get("issuance_window_hours")
    if issuance_windows:
        issuance_features = build_issuance_features(
            prices, config, result["forecast_timestamp"]
        )
        result = result.merge(
            issuance_features, left_on="forecast_timestamp", right_index=True, how="left"
        )
        names = issuance_feature_columns(issuance_windows)
        incomplete = result[names].isna().any(axis=1)
        # Whole blocks warm up together, so only leading issuances may drop.
        if incomplete.any() and not incomplete.to_numpy()[: int(incomplete.sum())].all():
            raise ValueError(
                "Issuance feature warmup must be a leading block of rows"
            )
        metadata["issuance_warmup_rows_dropped"] = int(incomplete.sum())
        # The sidecar contract must name every predictor the backtest will use.
        metadata["feature_columns"] = list(metadata["feature_columns"]) + names
        result = result.loc[~incomplete].reset_index(drop=True)
        # These summarize history up to issuance, so they are usable exactly then.
        result["feature_available_at"] = result[
            ["feature_available_at", "forecast_timestamp"]
        ].max(axis=1)
    published = list(features.get("day_ahead_forecast_columns") or [])
    if published:
        if day_ahead_forecasts is None:
            raise ValueError(
                "day_ahead_forecast_columns require a day_ahead_forecasts frame"
            )
        missing = sorted(
            set(["timestamp", *published]) - set(day_ahead_forecasts.columns)
        )
        if missing:
            raise ValueError(f"Missing day-ahead forecast columns: {missing}")
        joined = day_ahead_forecasts.loc[:, ["timestamp", *published]]
        if joined["timestamp"].duplicated().any():
            raise ValueError("Day-ahead forecasts must have unique hourly timestamps")
        before = len(result)
        result = result.merge(joined, on="timestamp", how="inner", validate="one_to_one")
        if len(result) != before:
            raise ValueError(
                "Day-ahead forecasts must cover every prepared delivery hour"
            )
        if result[published].isna().any().any():
            raise ValueError("Day-ahead forecast predictors must not be missing")
        # Published by the regulated deadline on the preceding day, so these are
        # held exactly at issuance, never before it.
        result["feature_available_at"] = result[
            ["feature_available_at", "forecast_timestamp"]
        ].max(axis=1)
        metadata["feature_columns"] = list(metadata["feature_columns"]) + published
        metadata["day_ahead_forecast_basis"] = PUBLISHED_FORECAST_BASIS

    perfect_foresight = features.get(PERFECT_FORESIGHT_KEY, False)
    if perfect_foresight:
        names = list(features["weather_columns"])
        if weather is None:
            raise ValueError("Perfect-foresight preparation requires a weather frame")
        missing = sorted(set(["timestamp", *names]) - set(weather.columns))
        if missing:
            raise ValueError(f"Missing weather columns: {missing}")
        joined = weather.loc[:, ["timestamp", *names]]
        if joined["timestamp"].duplicated().any():
            raise ValueError("Weather must have unique hourly timestamps")
        before = len(result)
        result = result.merge(joined, on="timestamp", how="inner", validate="one_to_one")
        if len(result) != before:
            raise ValueError("Weather must cover every prepared delivery hour")
        if result[names].isna().any().any():
            raise ValueError("Weather predictors must not contain missing values")
        # Truthful provenance: the delivery hour's own weather is known only then.
        result["feature_available_at"] = result[
            ["feature_available_at", "timestamp"]
        ].max(axis=1)
        metadata["feature_columns"] = list(metadata["feature_columns"]) + names
        metadata[PERFECT_FORESIGHT_KEY] = True
        metadata["evaluation_purpose"] = "perfect_foresight_bound_not_operational"
    elif (result["feature_available_at"] > result["forecast_timestamp"]).any():
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
        + issuance_feature_columns(
            config["features"].get("issuance_window_hours") or []
        )
        + list(config["features"].get("day_ahead_forecast_columns") or [])
        + list(config["features"].get("weather_columns") or [])
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
    if features.get("issuance_window_hours"):
        # Issuance-relative predictors are usable exactly at issuance, so they
        # set the availability of every row in their block.
        expected["feature_available_at"] = pd.concat(
            [expected["feature_available_at"], expected["forecast_timestamp"]], axis=1
        ).max(axis=1)
    if features.get("day_ahead_forecast_columns"):
        expected["feature_available_at"] = pd.concat(
            [expected["feature_available_at"], expected["forecast_timestamp"]], axis=1
        ).max(axis=1)
    if features.get(PERFECT_FORESIGHT_KEY):
        expected["feature_available_at"] = pd.concat(
            [expected["feature_available_at"], times], axis=1
        ).max(axis=1)
    for name, values in expected.items():
        if not pd.to_datetime(frame[name], utc=True).equals(values):
            raise ValueError(f"Invalid day-ahead {name} provenance")
    if (
        not features.get(PERFECT_FORESIGHT_KEY)
        and (expected["feature_available_at"] > expected["forecast_timestamp"]).any()
    ):
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
    weather = None
    if config["features"].get(PERFECT_FORESIGHT_KEY):
        weather_path = paths.get("processed_weather_parquet_path")
        if weather_path is None:
            raise ValueError(
                "Perfect-foresight preparation requires "
                "paths.processed_weather_parquet_path"
            )
        weather = load_local_data(weather_path)
        if not isinstance(weather["timestamp"].dtype, pd.DatetimeTZDtype):
            raise ValueError("Cached weather timestamps must be timezone-aware")
        metadata_weather_source = str(weather_path)
    forecasts = None
    if config["features"].get("day_ahead_forecast_columns"):
        forecast_path = paths.get("processed_day_ahead_forecast_parquet_path")
        if forecast_path is None:
            raise ValueError(
                "day_ahead_forecast_columns require "
                "paths.processed_day_ahead_forecast_parquet_path"
            )
        forecasts = load_local_data(forecast_path)
        if not isinstance(forecasts["timestamp"].dtype, pd.DatetimeTZDtype):
            raise ValueError("Forecast timestamps must be timezone-aware")
    result, metadata = build_availability_dataset(
        frame, config, source_dataset=source, weather=weather,
        day_ahead_forecasts=forecasts,
    )
    if forecasts is not None:
        metadata["day_ahead_forecast_source_dataset"] = str(forecast_path)
        metadata["day_ahead_forecast_source_sha256"] = hashlib.sha256(
            forecast_path.read_bytes()
        ).hexdigest()
    if weather is not None:
        metadata["weather_source_dataset"] = metadata_weather_source
        metadata["weather_source_sha256"] = hashlib.sha256(
            weather_path.read_bytes()
        ).hexdigest()
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
