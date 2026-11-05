"""Issue one day-ahead forecast per strategy, resuming from stored artifacts.

A run performs the same steps the backtest performs for a single delivery day,
against live data: refresh market data, record actuals that have since become
usable, ask the strategy whether to refit, issue the next delivery day, and
persist the result. Everything needed to continue lives in the store, so the
job is stateless and safe to re-run.
"""

from collections.abc import Mapping, Sequence
from datetime import date, datetime, timedelta, timezone
from typing import Any
import logging

import numpy as np
import pandas as pd

from energy_trading_pipeline.backtesting.backtest_runner import build_policy
from energy_trading_pipeline.backtesting.splitter import day_ahead_issuance
from energy_trading_pipeline.data_ingestion.smard_client import (
    SMARD_SERIES,
    SmardClient,
    missing_hours,
)
from energy_trading_pipeline.features.availability import (
    availability_contract,
    build_availability_dataset,
)
from energy_trading_pipeline.forecasting.store import (
    MARKET_DATA_KEY,
    ArtifactStore,
    model_key,
    sorted_unique,
    strategy_keys,
)
from energy_trading_pipeline.models.xgboost_model import XGBoostSpreadModel
from energy_trading_pipeline.retraining.events import RETRAINING_EVENT_COLUMNS

LOGGER = logging.getLogger(__name__)

LIVE_FORECAST_COLUMNS = (
    "timestamp",
    "forecast_timestamp",
    "delivery_date",
    "prediction",
    "actual",
    "strategy",
    "model_version",
)
# Enough history to build 168-hour lags and fit the configured training window.
MARKET_HISTORY_MARGIN_DAYS = 30


def required_market_columns(config: Mapping[str, Any]) -> list[str]:
    """Return the SMARD series this configuration actually needs.

    Prices form the target and the price history; the configured day-ahead
    forecast columns are the published predictors. Fetching anything else would
    let an unused series block an otherwise usable hour.
    """
    forecasts = list(config["features"].get("day_ahead_forecast_columns") or [])
    unknown = sorted(set(forecasts) - set(SMARD_SERIES))
    if unknown:
        raise ValueError(f"Unknown SMARD forecast series in config: {unknown}")
    return ["price_de", "price_fr", *forecasts]


def latest_issuance(
    config: Mapping[str, Any], now: pd.Timestamp
) -> tuple[pd.Timestamp, date]:
    """Return the most recent issuance that has already passed, and its day.

    Forecasts are issued once per day at the configured local hour. Running at
    any later moment reissues that same delivery day rather than reaching for a
    publication that does not exist yet.
    """
    settings = config["backtest"]
    zone = settings["issue_timezone"]
    local = now.tz_convert(zone)
    delivery = local.date() + timedelta(days=1)
    issuance = day_ahead_issuance(delivery, settings)
    if issuance > now:
        delivery = local.date()
        issuance = day_ahead_issuance(delivery, settings)
    return issuance, delivery


def refresh_market_data(
    store: ArtifactStore,
    config: Mapping[str, Any],
    *,
    through: pd.Timestamp,
    client: SmardClient | None = None,
    history_days: int | None = None,
) -> pd.DataFrame:
    """Extend stored SMARD data up to ``through``, returning the full series.

    Only hours after the stored maximum are fetched, so a daily run downloads a
    day rather than a history. Rows whose values are still unpublished are
    dropped, which lets a later run pick them up once SMARD publishes them.
    """
    columns = required_market_columns(config)
    existing = (
        store.read_frame(MARKET_DATA_KEY)
        if store.exists(MARKET_DATA_KEY)
        else pd.DataFrame(columns=["timestamp", *columns])
    )
    # Only the configured series are required; an unused one must not be able to
    # withhold an otherwise complete hour.
    existing = existing.loc[:, ["timestamp", *columns]]
    if history_days is None:
        history_days = (
            int(config["backtest"]["train_window_days"])
            + int(config["backtest"]["validation_window_days"])
            + MARKET_HISTORY_MARGIN_DAYS
        )
    if existing.empty:
        start = (through - pd.Timedelta(days=history_days)).floor("h")
    else:
        start = pd.Timestamp(existing["timestamp"].max()).ceil("h") + pd.Timedelta(
            hours=1
        )
    fetched = pd.DataFrame(columns=["timestamp", *columns])
    if start < through:
        fetched = (client or SmardClient()).fetch_frame(columns, start, through)
        unpublished = fetched[columns].isna().any(axis=1)
        if unpublished.any():
            LOGGER.info(
                "Dropping %d hour(s) not yet published: %s",
                int(unpublished.sum()),
                missing_hours(fetched.loc[unpublished], columns),
            )
        fetched = fetched.loc[~unpublished]
    frames = [frame for frame in (existing, fetched) if not frame.empty]
    combined = (
        pd.concat(frames, ignore_index=True)
        if frames
        else pd.DataFrame(columns=["timestamp", *columns])
    )
    # Concatenating an empty frame would otherwise leave object-dtype columns.
    combined["timestamp"] = pd.to_datetime(combined["timestamp"], utc=True).dt.as_unit(
        "ns"
    )
    for column in columns:
        combined[column] = pd.to_numeric(combined[column], errors="coerce").astype(
            "float64"
        )
    combined = sorted_unique(combined, ["timestamp"])
    store.write_frame(MARKET_DATA_KEY, combined)
    return combined


def build_features(
    market: pd.DataFrame, config: Mapping[str, Any]
) -> pd.DataFrame:
    """Build the configured day-ahead predictors from raw market data."""
    forecast_columns = list(config["features"].get("day_ahead_forecast_columns") or [])
    prices = market.loc[:, ["timestamp", "price_de", "price_fr"]]
    forecasts = (
        market.loc[:, ["timestamp", *forecast_columns]] if forecast_columns else None
    )
    frame, _ = build_availability_dataset(
        prices,
        config,
        source_dataset="live_smard",
        day_ahead_forecasts=forecasts,
    )
    return frame


def _empty_forecasts() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.Series(dtype="datetime64[ns, UTC]"),
            "forecast_timestamp": pd.Series(dtype="datetime64[ns, UTC]"),
            "delivery_date": pd.Series(dtype="string"),
            "prediction": pd.Series(dtype="float64"),
            "actual": pd.Series(dtype="float64"),
            "strategy": pd.Series(dtype="string"),
            "model_version": pd.Series(dtype="string"),
        }
    )


def backfill_actuals(
    forecasts: pd.DataFrame, observed: pd.DataFrame, *, now: pd.Timestamp
) -> pd.DataFrame:
    """Fill actual spreads that have become usable since the forecast was made.

    ``observed`` supplies ``timestamp`` and the realised ``spread``. Under the
    availability contract a delivered hour is usable one hour after it ends, so
    only hours satisfying that bound are recorded; the rest stay missing until
    a later run.
    """
    if forecasts.empty:
        return forecasts
    spread = (
        observed["spread"]
        if "spread" in observed
        else observed["price_de"] - observed["price_fr"]
    )
    usable = pd.DataFrame(
        {"timestamp": observed["timestamp"], "observed_spread": spread}
    )
    usable = usable.loc[usable["timestamp"] + pd.Timedelta(hours=1) <= now]
    merged = forecasts.merge(usable, on="timestamp", how="left")
    merged["actual"] = merged["actual"].where(
        merged["actual"].notna(), merged["observed_spread"]
    )
    return merged.drop(columns="observed_spread")


def _policy_history(forecasts: pd.DataFrame, issuance: pd.Timestamp) -> pd.DataFrame:
    """Return observed forecast errors the policy may see at this issuance."""
    from energy_trading_pipeline.backtesting.forecast_log import (
        INPUT_COLUMNS,
        build_forecast_log,
    )

    if forecasts.empty:
        return build_forecast_log(pd.DataFrame(columns=INPUT_COLUMNS))
    known = (
        (forecasts["timestamp"] + pd.Timedelta(hours=1) <= issuance)
        & forecasts["actual"].notna()
        & (forecasts["forecast_timestamp"] <= issuance)
    )
    history = forecasts.loc[known, list(INPUT_COLUMNS)].copy()
    return build_forecast_log(history)


def run_strategy_issuance(
    store: ArtifactStore,
    config: Mapping[str, Any],
    strategy: str,
    features: pd.DataFrame,
    *,
    issuance: pd.Timestamp,
    delivery: date,
    now: pd.Timestamp,
) -> dict[str, Any]:
    """Issue one delivery day for one strategy and persist the outcome."""
    keys = strategy_keys(strategy)
    columns = list(config["backtest"]["feature_columns"])
    target = config["model"]["target_column"]

    block = features.loc[features["forecast_timestamp"] == issuance]
    expected = {23, 24, 25}
    if len(block) not in expected:
        raise ValueError(
            f"Delivery day {delivery} has {len(block)} hours; "
            "predictors are not fully published yet"
        )
    if (block["feature_available_at"] > issuance).any():
        raise ValueError("Forecast predictors are unavailable at issuance")

    forecasts = (
        store.read_frame(keys["forecasts"])
        if store.exists(keys["forecasts"])
        else _empty_forecasts()
    )
    forecasts = backfill_actuals(forecasts, features, now=now)
    events = (
        store.read_frame(keys["events"])
        if store.exists(keys["events"])
        else pd.DataFrame(columns=list(RETRAINING_EVENT_COLUMNS))
    )
    state = store.read_yaml(keys["state"]) if store.exists(keys["state"]) else {}

    policy = build_policy({**config, "retraining": {**config["retraining"], "strategy": strategy}})
    if state.get("policy"):
        policy.restore(state["policy"])

    already_issued = (
        not forecasts.empty
        and (forecasts["delivery_date"] == str(delivery)).any()
    )
    model_version = state.get("model_version")
    retrained = False

    if already_issued:
        # Re-running a day must not retrain again or move the schedule on.
        LOGGER.info("Delivery %s already issued for %s; reusing model", delivery, strategy)
    else:
        decision = bool(policy.should_retrain(issuance, _policy_history(forecasts, issuance)))
        retrained = decision or model_version is None
        if retrained:
            train = _training_block(features, config, issuance, columns, target)
            model = XGBoostSpreadModel.from_config(config["model"])
            model.fit(train[columns], train[target])
            model_version = _version_for(issuance)
            _save_model(store, strategy, model_version, model)
            if decision:
                events = pd.concat(
                    [
                        events,
                        pd.DataFrame([_event(policy, strategy, issuance, train, model_version)]),
                    ],
                    ignore_index=True,
                )

    model = _load_model(store, strategy, model_version, config, columns, target)
    predictions = model.predict(block[columns])
    issued = pd.DataFrame(
        {
            "timestamp": block["timestamp"].to_numpy(),
            "forecast_timestamp": issuance,
            "delivery_date": str(delivery),
            "prediction": predictions,
            "actual": np.nan,
            "strategy": strategy,
            "model_version": model_version,
        }
    )
    combined = pd.concat([forecasts, issued], ignore_index=True)
    combined = sorted_unique(combined, ["strategy", "timestamp"])
    combined = backfill_actuals(combined, features, now=now)

    store.write_frame(keys["forecasts"], combined.loc[:, list(LIVE_FORECAST_COLUMNS)])
    store.write_frame(keys["events"], events)
    store.write_yaml(
        keys["state"],
        {
            "strategy": strategy,
            "model_version": model_version,
            "last_issuance": issuance.isoformat(),
            "last_delivery_date": str(delivery),
            "retraining_count": int(len(events)),
            "feature_columns": columns,
            "model_parameters": dict(config["model"]["params"]),
            "availability_contract": availability_contract(config),
            "policy": policy.state(),
            "updated_at": now.isoformat(),
        },
    )
    return {
        "strategy": strategy,
        "delivery_date": str(delivery),
        "issuance": issuance.isoformat(),
        "hours": int(len(issued)),
        "model_version": model_version,
        "retrained": bool(retrained),
        "reissued": bool(already_issued),
        "retraining_count": int(len(events)),
    }


def _training_block(
    features: pd.DataFrame,
    config: Mapping[str, Any],
    issuance: pd.Timestamp,
    columns: Sequence[str],
    target: str,
) -> pd.DataFrame:
    """Select the configured training window ending before this issuance."""
    settings = config["backtest"]
    end = issuance - pd.Timedelta(days=int(settings["validation_window_days"]))
    start = end - pd.Timedelta(days=int(settings["train_window_days"]))
    train = features.loc[
        (features["timestamp"] >= start) & (features["timestamp"] < end)
    ]
    if train.empty:
        raise ValueError(f"No training rows between {start} and {end}")
    if (train["feature_available_at"] > issuance).any():
        raise ValueError("Training predictors are unavailable at issuance")
    if (train["actual_available_at"] > issuance).any():
        raise ValueError("Training actuals are unavailable at issuance")
    values = train[target].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Training actuals must be finite numeric values")
    return train


def _version_for(issuance: pd.Timestamp) -> str:
    """Name a model after the issuance that created it, as the registry does."""
    return issuance.tz_convert("UTC").strftime("model_%Y%m%d_%H%M%S")


def _save_model(
    store: ArtifactStore, strategy: str, version: str, model: XGBoostSpreadModel
) -> None:
    """Persist a fitted model under its version key."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "model.json"
        model.save(path)
        store.write_bytes(model_key(strategy, version), path.read_bytes())


def _load_model(
    store: ArtifactStore,
    strategy: str,
    version: str,
    config: Mapping[str, Any],
    columns: Sequence[str],
    target: str,
) -> XGBoostSpreadModel:
    """Load a saved model and verify it matches the configured contract."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "model.json"
        path.write_bytes(store.read_bytes(model_key(strategy, version)))
        model = XGBoostSpreadModel.load(path)
    if (
        model.feature_columns != list(columns)
        or model.target_column != target
        or model.params != config["model"]["params"]
    ):
        raise ValueError(
            f"Saved model {version} does not match configured features/target/params"
        )
    return model


def _event(
    policy: Any,
    strategy: str,
    issuance: pd.Timestamp,
    train: pd.DataFrame,
    version: str,
) -> dict[str, Any]:
    """Build the canonical record of a completed refit."""
    rolling = getattr(policy, "rolling_rmse", float("nan"))
    threshold = getattr(policy, "threshold", float("nan"))
    return {
        "timestamp": issuance.isoformat(),
        "strategy": strategy,
        "trigger_reason": (
            "rolling_rmse_exceeds_threshold"
            if strategy == "performance_triggered"
            else "fixed_schedule_interval_elapsed"
        ),
        "threshold": float(threshold),
        "rolling_rmse": float(rolling),
        "training_window_start": train["timestamp"].min().isoformat(),
        "training_window_end": (
            train["timestamp"].max() + pd.Timedelta(hours=1)
        ).isoformat(),
        "model_version": version,
    }


def run_daily_forecast(
    store: ArtifactStore,
    config: Mapping[str, Any],
    *,
    strategies: Sequence[str] = ("no_retraining", "fixed_schedule", "performance_triggered"),
    now: pd.Timestamp | None = None,
    client: SmardClient | None = None,
) -> dict[str, Any]:
    """Refresh data and issue the next delivery day for every strategy."""
    now = (now or pd.Timestamp.now(tz="UTC")).tz_convert("UTC")
    issuance, delivery = latest_issuance(config, now)
    # Reach to the end of the delivery day: its predictors are published by
    # issuance, and its hours are what this run forecasts.
    delivery_end = pd.Timestamp(
        delivery + timedelta(days=1), tz=config["backtest"]["issue_timezone"]
    ).tz_convert("UTC")
    market = refresh_market_data(store, config, through=delivery_end, client=client)
    features = build_features(market, config)
    results = [
        run_strategy_issuance(
            store, config, strategy, features,
            issuance=issuance, delivery=delivery, now=now,
        )
        for strategy in strategies
    ]
    summary = {
        "ran_at": now.isoformat(),
        "issuance": issuance.isoformat(),
        "delivery_date": str(delivery),
        "market_rows": int(len(market)),
        "market_through": market["timestamp"].max().isoformat(),
        "strategies": results,
    }
    store.write_yaml(
        f"live/runs/{now.strftime('%Y%m%dT%H%M%SZ')}.yaml", summary
    )
    store.write_yaml("live/latest_run.yaml", summary)
    return summary
