"""Chronological single-strategy orchestration with a static baseline hook."""

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from energy_trading_pipeline.backtesting.forecast_log import (
    INPUT_COLUMNS,
    STRATEGIES,
    build_forecast_log,
    write_forecast_log,
)
from energy_trading_pipeline.backtesting.splitter import (
    TimeWindow,
    generate_backtest_windows_from_config,
)
from energy_trading_pipeline.models.xgboost_model import XGBoostSpreadModel


PolicyHook = Callable[[pd.Timestamp, pd.DataFrame], bool]


def _timestamp(value: Any, name: str) -> pd.Timestamp:
    """Require explicit timezone information rather than assuming UTC."""
    try:
        result = pd.Timestamp(value)
        if pd.isna(result) or result.tzinfo is None:
            raise ValueError(name)
        return result.tz_convert("UTC")
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError(f"{name} must be a valid timezone-aware timestamp") from exc


def _select_hours(frame: pd.DataFrame, window: TimeWindow) -> pd.DataFrame:
    """Fail on missing delivery hours instead of silently shortening evaluation."""
    rows = frame.loc[
        (frame["timestamp"] >= window.start) & (frame["timestamp"] < window.end)
    ]
    expected = pd.date_range(window.start, window.end, freq="h", inclusive="left")
    if rows["timestamp"].tolist() != expected.tolist():
        raise ValueError(f"Incomplete hourly coverage for {window.start} to {window.end}")
    return rows


def run_backtest(
    feature_data: pd.DataFrame,
    config: Mapping[str, Any],
    *,
    feature_columns: Sequence[str],
    model_version: str,
    forecast_path: Path,
    model_output_path: Path | None = None,
    initial_model_path: Path | None = None,
    initial_model_history_end: pd.Timestamp | None = None,
    strategy: str = "no_retraining",
    policy_hook: PolicyHook | None = None,
) -> pd.DataFrame:
    """Train once or load a static XGBoost model and persist canonical forecasts.

    Uses the half-open windows from ``config['backtest']``. A fresh model fits
    only the first training window; the validation interval remains held out.
    Supply ``model_output_path`` for a new model, or ``initial_model_path`` plus
    an inclusive ``initial_model_history_end`` for a saved model. The latter is
    a caller-verified upper bound on all fitting/tuning data timestamps AND their
    availability times; it must precede first issuance. The model version and
    artifact paths are caller-owned (normally from a run/registry).

    Data must include aware ``feature_available_at`` (latest availability of
    any selected predictor in that row) and ``actual_available_at`` columns.
    These are explicit caller attestations, not inferred from delivery time.
    Every predictor in a forecast block must be available at its start, so
    within-block lags cannot silently leak later observations. Training labels
    must also be available at first issuance. Complete hourly training and
    evaluation coverage is required; input data is never mutated.

    The optional hook receives issuance and an isolated canonical log of prior
    forecasts whose actuals are available then. None is the static placeholder.
    A True decision raises NotImplementedError pending Epic 7 retraining; it is
    never silently ignored. The returned/persisted log includes retrospective
    actuals, while hooks see only time-filtered history. CLI run metadata and
    registry coordination belong to the caller.
    """
    windows = generate_backtest_windows_from_config(config)
    if strategy not in STRATEGIES:
        raise ValueError(f"strategy must be one of {sorted(STRATEGIES)}")
    if strategy != "no_retraining" and policy_hook is None:
        raise ValueError("A non-baseline strategy requires a policy_hook")
    if policy_hook is not None and not callable(policy_hook):
        raise ValueError("policy_hook must be callable")
    if not isinstance(model_version, str) or not model_version.strip():
        raise ValueError("model_version must be a nonempty string")
    forecast_path = Path(forecast_path)
    if forecast_path.suffix.lower() not in {".parquet", ".csv"}:
        raise ValueError("forecast_path must use .parquet or .csv")
    if (initial_model_path is None) == (model_output_path is None):
        raise ValueError("Supply exactly one of model_output_path or initial_model_path")
    if model_output_path is not None and Path(model_output_path).suffix != ".json":
        raise ValueError("model_output_path must use .json")

    model = XGBoostSpreadModel.from_config(config["model"])
    target = model.target_column
    if isinstance(feature_columns, str) or not isinstance(feature_columns, Sequence):
        raise ValueError("feature_columns must be a sequence of predictor names")
    columns = list(feature_columns)
    reserved = {
        "timestamp",
        target,
        "spread",
        "price_de",
        "price_fr",
        "feature_available_at",
        "actual_available_at",
    }
    if (
        not columns
        or any(not isinstance(column, str) for column in columns)
        or len(set(columns)) != len(columns)
        or reserved.intersection(columns)
    ):
        raise ValueError("feature_columns must be unique predictors without target leakage")
    required = ["timestamp", target, "feature_available_at", "actual_available_at", *columns]
    if not feature_data.columns.is_unique:
        raise ValueError("Feature data has duplicate column names")
    missing = sorted(set(required) - set(feature_data.columns))
    if missing:
        raise ValueError(f"Missing required feature data columns: {missing}")
    frame = feature_data.loc[:, required].copy()
    for name in ("timestamp", "feature_available_at", "actual_available_at"):
        frame[name] = pd.to_datetime(
            [_timestamp(value, name) for value in frame[name]], utc=True
        )
    frame = frame.sort_values("timestamp", kind="stable").reset_index(drop=True)
    if frame["timestamp"].duplicated().any():
        raise ValueError("Feature data has duplicate timestamps")
    if (frame["timestamp"] != frame["timestamp"].dt.floor("h")).any():
        raise ValueError("Feature data timestamps must be hourly aligned")

    first_issuance = windows[0].forecast.start
    # Preflight the entire evaluation before training or writing any artifacts.
    blocks = [_select_hours(frame, window.forecast) for window in windows]
    for window, block in zip(windows, blocks, strict=True):
        if (block["feature_available_at"] > window.forecast.start).any():
            raise ValueError("Forecast features are unavailable at issuance")
    if initial_model_path is None:
        train = _select_hours(frame, windows[0].train)
        if (train["feature_available_at"] > first_issuance).any():
            raise ValueError("Training features are unavailable at issuance")
        if (train["actual_available_at"] > first_issuance).any():
            raise ValueError("training actuals are unavailable at issuance")
        if not pd.api.types.is_numeric_dtype(train[target]) or not np.isfinite(
            train[target].to_numpy(dtype=float)
        ).all():
            raise ValueError("Training actuals must be finite numeric values")
        model.fit(train[columns], train[target])
    else:
        history_end = _timestamp(initial_model_history_end, "initial_model_history_end")
        if history_end >= first_issuance:
            raise ValueError("initial_model_history_end must precede first issuance")
        loaded = XGBoostSpreadModel.load(Path(initial_model_path))
        if (
            loaded.feature_columns != columns
            or loaded.target_column != target
            or loaded.params != model.params
        ):
            raise ValueError("Loaded model does not match configured features/target/params")
        model = loaded

    log = build_forecast_log(pd.DataFrame(columns=INPUT_COLUMNS))
    availability = frame.set_index("timestamp")["actual_available_at"]
    for window, block in zip(windows, blocks, strict=True):
        issuance = window.forecast.start
        if policy_hook is not None:
            known = log["timestamp"].map(availability) <= issuance
            history = log.loc[known & log["actual"].notna()].copy(deep=True)
            decision = policy_hook(issuance, history)
            if not isinstance(decision, bool):
                raise ValueError("policy_hook must return a bool retraining decision")
            if decision:
                raise NotImplementedError("Retraining execution is deferred to Epic 7")
        records = pd.DataFrame(
            {
                "timestamp": block["timestamp"].to_numpy(),
                "forecast_timestamp": issuance,
                "prediction": model.predict(block[columns]),
                "actual": block[target].to_numpy(),
                "strategy": strategy,
                "model_version": model_version,
            }
        )
        current = build_forecast_log(records)
        log = current if log.empty else pd.concat([log, current], ignore_index=True)

    if model_output_path is not None:
        model.save(Path(model_output_path))
    write_forecast_log(log, forecast_path)
    return log
