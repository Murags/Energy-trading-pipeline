"""Chronological single-strategy orchestration with a static baseline hook."""

from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
import json
import hashlib
import os
import tempfile
import yaml
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
from energy_trading_pipeline.retraining.events import (
    RETRAINING_EVENT_COLUMNS,
    write_retraining_events,
)
from energy_trading_pipeline.retraining.fixed_schedule import FixedSchedulePolicy
from energy_trading_pipeline.retraining.no_retraining import NoRetrainingPolicy
from energy_trading_pipeline.retraining.performance_triggered import (
    PerformanceTriggeredPolicy,
)
from energy_trading_pipeline.retraining.policies import RetrainingPolicy
from energy_trading_pipeline.backtesting.splitter import (
    TimeWindow,
    generate_backtest_windows_from_config,
)
from energy_trading_pipeline.config.paths import (
    get_default_base_dir,
    resolve_paths_config,
)
from energy_trading_pipeline.models.xgboost_model import XGBoostSpreadModel
from energy_trading_pipeline.features.availability import (
    availability_contract,
    validate_availability_frame,
)
from energy_trading_pipeline.utils.io import write_run_metadata
from energy_trading_pipeline.utils.time import generate_run_id

PolicyHook = Callable[[pd.Timestamp, pd.DataFrame], bool]


def build_policy(config: Mapping[str, Any]) -> RetrainingPolicy:
    """Construct the configured strategy's policy from experiment config.

    Each strategy reads only its own settings, so an unrelated missing key never
    blocks a run. Returns a fresh instance; policies carry per-run decision state.
    """
    strategy = config["retraining"]["strategy"]
    if strategy == "no_retraining":
        return NoRetrainingPolicy()
    if strategy == "fixed_schedule":
        return FixedSchedulePolicy.from_config(config)
    return PerformanceTriggeredPolicy.from_config(config)


def _trigger_details(policy: RetrainingPolicy) -> dict[str, Any]:
    """Describe why this policy last fired, for the canonical event record.

    Scheduled retraining has no threshold or metric, which the event builder
    records as missing rather than inventing a number.
    """
    if isinstance(policy, PerformanceTriggeredPolicy):
        return {
            "trigger_reason": "rolling_rmse_exceeds_threshold",
            "threshold": policy.threshold,
            "rolling_rmse": policy.rolling_rmse,
        }
    return {
        "trigger_reason": "fixed_schedule_interval_elapsed",
        "threshold": float("nan"),
        "rolling_rmse": float("nan"),
    }


def run_configured_backtest(
    config: Mapping[str, Any], *, config_file_path: Path
) -> dict[str, Any]:
    """Run a local static baseline and persist run provenance and JSONL events.

    Requires explicit paths, model parameters, ``backtest.feature_columns``, and
    ``retraining.strategy: no_retraining``. Availability columns must already be
    present in the Parquet input; they are never inferred by the CLI. Uses only
    the first training window and leaves validation held out, as in run_backtest.
    Aggregate metrics are deferred and recorded as an empty mapping.

    Run/model directories are exclusively reserved to prevent overwrites. Failed
    execution leaves its diagnostic log and any partial artifacts for inspection;
    only successful execution writes run metadata. Returns that metadata.
    """
    paths_config = config.get("paths")
    required_paths = ("feature_data_parquet_path", "models_dir", "logs_dir")
    if not isinstance(paths_config, Mapping) or any(
        not paths_config.get(key) for key in required_paths
    ):
        raise ValueError(
            f"Backtesting requires paths {list(required_paths)}; use --paths-config"
        )
    paths = resolve_paths_config(dict(paths_config), get_default_base_dir())
    feature_path = paths["feature_data_parquet_path"]
    if not feature_path.is_file():
        raise FileNotFoundError(f"Feature dataset not found: {feature_path}")
    model_config = config.get("model")
    if not isinstance(model_config, Mapping) or not isinstance(
        model_config.get("params"), Mapping
    ):
        raise ValueError(
            "Backtesting requires model.params; use --model-params-config or inline params"
        )
    model = XGBoostSpreadModel.from_config(model_config)
    retraining = config.get("retraining")
    if not isinstance(retraining, Mapping) or retraining.get("strategy") not in (
        STRATEGIES
    ):
        raise ValueError(
            f"retraining.strategy must be one of {sorted(STRATEGIES)}"
        )
    policy = build_policy(config)
    windows = generate_backtest_windows_from_config(config)
    columns = config["backtest"].get("feature_columns")
    if not isinstance(columns, list) or not columns:
        raise ValueError(
            "Backtesting requires a nonempty backtest.feature_columns list"
        )
    frame = pd.read_parquet(feature_path)
    day_ahead = config["backtest"].get("mode") == "day_ahead"
    feature_metadata = None
    if day_ahead:
        sidecar = feature_path.with_suffix(".metadata.yaml")
        feature_metadata = yaml.safe_load(sidecar.read_text(encoding="utf-8"))
        if not isinstance(feature_metadata, Mapping) or (
            feature_metadata.get("availability_contract")
            != availability_contract(config)
            or feature_metadata.get("feature_columns") != columns
            or feature_metadata.get("feature_sha256")
            != hashlib.sha256(feature_path.read_bytes()).hexdigest()
        ):
            raise ValueError("Day-ahead feature artifact/config/metadata mismatch")
        validate_availability_frame(frame, config, columns)

    run_id = generate_run_id()
    model_version = run_id.replace("run_", "model_", 1)
    run_dir = paths["logs_dir"] / "runs" / run_id
    model_dir = paths["models_dir"] / "artifacts" / model_version
    artifact_paths = {
        "feature_dataset": str(feature_path),
        "model": str(model_dir / "model.json"),
        "forecasts": str(run_dir / "forecasts.parquet"),
        "backtest_log": str(run_dir / "backtest_log.jsonl"),
        "retraining_events": str(run_dir / "retraining_events.parquet"),
        "run_metadata": str(run_dir / "run_metadata.yaml"),
    }
    context = {
        "stage": "backtesting",
        "run_id": run_id,
        "strategy": retraining["strategy"],
        "model_version": model_version,
        "evaluation_window": {
            "start": windows[0].forecast.start.isoformat(),
            "end": windows[-1].forecast.end.isoformat(),
        },
    }
    run_dir.mkdir(parents=True, exist_ok=False)
    log_path = Path(artifact_paths["backtest_log"])
    _write_backtest_event(log_path, context, "backtest_started")
    try:
        model_dir.mkdir(parents=True, exist_ok=False)
        events: list[dict[str, Any]] = []
        forecasts = run_backtest(
            frame,
            config,
            feature_columns=columns,
            model_version=model_version,
            model_output_path=Path(artifact_paths["model"]),
            forecast_path=Path(artifact_paths["forecasts"]),
            strategy=retraining["strategy"],
            policy_hook=policy.as_policy_hook(),
            refit_logger=lambda record: events.append(
                {**record, **_trigger_details(policy)}
            ),
        )
        write_retraining_events(
            pd.DataFrame(events, columns=list(RETRAINING_EVENT_COLUMNS)),
            Path(artifact_paths["retraining_events"]),
        )
        timestamps = pd.to_datetime(frame["timestamp"], utc=True)
        metadata = {
            **context,
            "config_file_path": str(Path(config_file_path).resolve()),
            "config": {
                **config,
                "paths": {key: str(value) for key, value in paths.items()},
            },
            "data_date_range": {
                "start": timestamps.min().isoformat(),
                "end": timestamps.max().isoformat(),
            },
            "feature_columns": columns,
            "target_column": model.target_column,
            "model_parameters": model.params,
            "training_windows": [
                _window_metadata(windows[0].train),
                *(
                    {
                        "start": record["training_window_start"],
                        "end": record["training_window_end"],
                        "model_version": record["model_version"],
                    }
                    for record in events
                ),
            ],
            "model_versions": [
                model_version,
                *(record["model_version"] for record in events),
            ],
            "retraining_event_count": len(events),
            "validation_window": _window_metadata(windows[0].validation),
            "window_convention": "[start, end)",
            "metrics": {},
            "artifact_paths": artifact_paths,
        }
        if day_ahead:
            metadata["availability_contract"] = availability_contract(config)
            metadata["feature_metadata"] = feature_metadata
            metadata["issuance_times"] = [
                window.issuance.isoformat() for window in windows
            ]
            metadata["evaluation_purpose"] = "engineering_smoke_not_final_evaluation"
        write_run_metadata(run_dir, metadata)
        _write_backtest_event(
            log_path, context, "backtest_completed", forecast_rows=len(forecasts)
        )
    except Exception as exc:
        _write_backtest_event(log_path, context, "backtest_failed", error=str(exc))
        raise
    return metadata


def _window_metadata(window: TimeWindow) -> dict[str, str]:
    """Serialize a half-open UTC interval."""
    return {"start": window.start.isoformat(), "end": window.end.isoformat()}


def _write_backtest_event(
    path: Path, context: Mapping[str, Any], event: str, **details: Any
) -> None:
    """Append a run-local event without configuring process-global logging."""
    record = {
        **context,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **details,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


def _timestamp(value: Any, name: str) -> pd.Timestamp:
    """Require explicit timezone information rather than assuming UTC."""
    try:
        result = pd.Timestamp(value)
        if pd.isna(result) or result.tzinfo is None:
            raise ValueError(name)
        return result.tz_convert("UTC")
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError(f"{name} must be a valid timezone-aware timestamp") from exc


def _validate_training_block(
    train: pd.DataFrame, issuance: pd.Timestamp, target: str
) -> None:
    """Reject a fit whose predictors or labels are not yet usable at issuance."""
    if (train["feature_available_at"] > issuance).any():
        raise ValueError("Training features are unavailable at issuance")
    if (train["actual_available_at"] > issuance).any():
        raise ValueError("training actuals are unavailable at issuance")
    if (
        not pd.api.types.is_numeric_dtype(train[target])
        or not np.isfinite(train[target].to_numpy(dtype=float)).all()
    ):
        raise ValueError("Training actuals must be finite numeric values")


def _save_model(model: XGBoostSpreadModel, path: Path, *, exclusive: bool) -> None:
    """Persist a model, optionally refusing to replace an existing artifact."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not exclusive:
        model.save(path)
        return
    with tempfile.TemporaryDirectory(dir=path.parent) as temporary:
        staged = Path(temporary) / "model.json"
        model.save(staged)
        os.link(staged, path)  # Atomic, fails if destination exists.


def _select_hours(frame: pd.DataFrame, window: TimeWindow) -> pd.DataFrame:
    """Fail on missing delivery hours instead of silently shortening evaluation."""
    rows = frame.loc[
        (frame["timestamp"] >= window.start) & (frame["timestamp"] < window.end)
    ]
    expected = pd.date_range(window.start, window.end, freq="h", inclusive="left")
    if rows["timestamp"].tolist() != expected.tolist():
        raise ValueError(
            f"Incomplete hourly coverage for {window.start} to {window.end}"
        )
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
    refit_model_dir: Path | None = None,
    refit_logger: Callable[[dict[str, Any]], None] | None = None,
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
    A True decision refits a fresh model on that window's training interval,
    using the same configuration, predictors, and availability rules as the
    initial fit, so every strategy differs only in when it refits. Supplying a
    hook preflights every candidate training window, so an unusable refit fails
    before any artifact is written.

    Each refit is saved as ``<model_version>_refit_NNN.json`` under
    ``refit_model_dir``, defaulting to the directory of ``model_output_path``,
    and subsequent blocks are logged under that version, so the forecast log
    carries model lineage. ``refit_logger`` receives one record per *completed*
    refit: issuance, strategy, training window, and the new version. Trigger
    provenance such as threshold and rolling RMSE belongs to the policy owner,
    which is the caller, not this runner.

    The returned/persisted log includes retrospective actuals, while hooks see
    only time-filtered history. CLI run metadata and registry coordination
    belong to the caller.
    """
    windows = generate_backtest_windows_from_config(config)
    if strategy not in STRATEGIES:
        raise ValueError(f"strategy must be one of {sorted(STRATEGIES)}")
    if strategy != "no_retraining" and policy_hook is None:
        raise ValueError("A non-baseline strategy requires a policy_hook")
    if policy_hook is not None and not callable(policy_hook):
        raise ValueError("policy_hook must be callable")
    if refit_logger is not None and not callable(refit_logger):
        raise ValueError("refit_logger must be callable")
    if not isinstance(model_version, str) or not model_version.strip():
        raise ValueError("model_version must be a nonempty string")
    forecast_path = Path(forecast_path)
    if forecast_path.suffix.lower() not in {".parquet", ".csv"}:
        raise ValueError("forecast_path must use .parquet or .csv")
    if (initial_model_path is None) == (model_output_path is None):
        raise ValueError(
            "Supply exactly one of model_output_path or initial_model_path"
        )
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
        "forecast_timestamp",
    }
    if (
        not columns
        or any(not isinstance(column, str) for column in columns)
        or len(set(columns)) != len(columns)
        or reserved.intersection(columns)
    ):
        raise ValueError(
            "feature_columns must be unique predictors without target leakage"
        )
    required = [
        "timestamp",
        target,
        "feature_available_at",
        "actual_available_at",
        *columns,
    ]
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

    day_ahead = config["backtest"].get("mode") == "day_ahead"
    if day_ahead:
        validate_availability_frame(
            feature_data.reset_index(drop=True), config, columns
        )
        for path in (forecast_path, model_output_path):
            if path is not None and Path(path).exists():
                raise FileExistsError(f"Refusing to overwrite artifact: {path}")
    first_issuance = windows[0].issuance
    # Preflight the entire evaluation before training or writing any artifacts.
    blocks = [_select_hours(frame, window.forecast) for window in windows]
    for window, block in zip(windows, blocks, strict=True):
        if (block["feature_available_at"] > window.issuance).any():
            raise ValueError("Forecast features are unavailable at issuance")
    # A policy may refit at any issuance, so every candidate window is checked
    # up front rather than failing part-way through a run.
    refit_blocks: list[pd.DataFrame] | None = None
    if policy_hook is not None:
        refit_blocks = [_select_hours(frame, window.train) for window in windows]
        for window, train_block in zip(windows, refit_blocks, strict=True):
            _validate_training_block(train_block, window.issuance, target)
    refit_dir = refit_model_dir
    if refit_dir is None and model_output_path is not None:
        refit_dir = Path(model_output_path).parent
    if initial_model_path is None:
        train = _select_hours(frame, windows[0].train)
        _validate_training_block(train, first_issuance, target)
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
            raise ValueError(
                "Loaded model does not match configured features/target/params"
            )
        model = loaded

    log = build_forecast_log(pd.DataFrame(columns=INPUT_COLUMNS))
    availability = frame.set_index("timestamp")["actual_available_at"]
    # Refits rebind `model`, so keep the initial fit for `model_output_path`:
    # that artifact identifies `model_version`, not whichever model fit last.
    initial_model = model
    active_version = model_version
    refit_count = 0
    for index, (window, block) in enumerate(zip(windows, blocks, strict=True)):
        issuance = window.issuance
        if policy_hook is not None:
            known = log["timestamp"].map(availability) <= issuance
            history = log.loc[known & log["actual"].notna()].copy(deep=True)
            decision = policy_hook(issuance, history)
            if not isinstance(decision, bool):
                raise ValueError("policy_hook must return a bool retraining decision")
            if decision:
                if refit_dir is None:
                    raise ValueError(
                        "Retraining requires refit_model_dir or model_output_path"
                    )
                refit_count += 1
                active_version = f"{model_version}_refit_{refit_count:03d}"
                train_block = refit_blocks[index]
                model = XGBoostSpreadModel.from_config(config["model"])
                model.fit(train_block[columns], train_block[target])
                _save_model(
                    model,
                    Path(refit_dir) / f"{active_version}.json",
                    exclusive=day_ahead,
                )
                if refit_logger is not None:
                    refit_logger(
                        {
                            "timestamp": issuance.isoformat(),
                            "strategy": strategy,
                            "training_window_start": window.train.start.isoformat(),
                            "training_window_end": window.train.end.isoformat(),
                            "model_version": active_version,
                        }
                    )
        records = pd.DataFrame(
            {
                "timestamp": block["timestamp"].to_numpy(),
                "forecast_timestamp": issuance,
                "prediction": model.predict(block[columns]),
                "actual": block[target].to_numpy(),
                "strategy": strategy,
                "model_version": active_version,
            }
        )
        current = build_forecast_log(records)
        log = current if log.empty else pd.concat([log, current], ignore_index=True)

    if day_ahead:
        if model_output_path is not None:
            _save_model(initial_model, Path(model_output_path), exclusive=True)
        forecast_path.parent.mkdir(parents=True, exist_ok=True)
        with forecast_path.open("xb") as handle:
            if forecast_path.suffix.lower() == ".parquet":
                log.to_parquet(handle, index=False)
            else:
                handle.write(log.to_csv(index=False).encode("utf-8"))
    else:
        if model_output_path is not None:
            _save_model(initial_model, Path(model_output_path), exclusive=False)
        write_forecast_log(log, forecast_path)
    return log
