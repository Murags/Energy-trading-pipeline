"""AWS Lambda entry point for the scheduled day-ahead forecast.

Configuration arrives through environment variables so the image stays generic
and holds no credentials: the function runs under an IAM role. The handler is a
thin wrapper around ``run_daily_forecast`` and contains no forecasting logic of
its own, so local and deployed runs execute the same code.
"""

from pathlib import Path
from typing import Any
import json
import logging
import os

from energy_trading_pipeline.backtesting.forecast_log import STRATEGIES
from energy_trading_pipeline.config.loader import load_config
from energy_trading_pipeline.forecasting.daily import run_daily_forecast
from energy_trading_pipeline.forecasting.store import build_store

LOGGER = logging.getLogger()
LOGGER.setLevel(os.environ.get("ETP_LOG_LEVEL", "INFO"))

ENV_STORE = "ETP_STORE"
ENV_CONFIG = "ETP_CONFIG"
ENV_MODEL_PARAMS = "ETP_MODEL_PARAMS"
ENV_STRATEGIES = "ETP_STRATEGIES"
DEFAULT_CONFIG = "configs/experiment_day_ahead_pvwind.yaml"
DEFAULT_MODEL_PARAMS = "configs/model_params.yaml"


def _strategies(event: dict[str, Any] | None) -> tuple[str, ...]:
    """Resolve strategies from the event, then the environment, then all three."""
    raw = (event or {}).get("strategies") or os.environ.get(ENV_STRATEGIES)
    if not raw:
        return tuple(sorted(STRATEGIES))
    names = raw.split(",") if isinstance(raw, str) else list(raw)
    names = tuple(name.strip() for name in names if name.strip())
    unknown = sorted(set(names) - set(STRATEGIES))
    if unknown:
        raise ValueError(f"Unknown strategies requested: {unknown}")
    return names


def handler(event: dict[str, Any] | None = None, context: Any = None) -> dict[str, Any]:
    """Issue the next delivery day for each configured strategy.

    The event may override ``store``, ``config`` and ``strategies``; otherwise
    the environment supplies them. Failures propagate so Lambda records the
    invocation as failed rather than reporting a success that did not happen.
    """
    event = event or {}
    destination = event.get("store") or os.environ.get(ENV_STORE)
    if not destination:
        raise ValueError(f"{ENV_STORE} or event['store'] is required")
    config_path = Path(event.get("config") or os.environ.get(ENV_CONFIG, DEFAULT_CONFIG))
    params_path = Path(
        event.get("model_params")
        or os.environ.get(ENV_MODEL_PARAMS, DEFAULT_MODEL_PARAMS)
    )
    config = load_config(config_path, model_params_config_path=params_path)
    strategies = _strategies(event)

    LOGGER.info(
        "Starting day-ahead forecast: store=%s config=%s strategies=%s",
        destination,
        config_path,
        ",".join(strategies),
    )
    summary = run_daily_forecast(
        build_store(destination), config, strategies=strategies
    )
    for row in summary["strategies"]:
        LOGGER.info(
            "%s: %d hours for %s using %s (%s)",
            row["strategy"],
            row["hours"],
            row["delivery_date"],
            row["model_version"],
            "refit" if row["retrained"] else "reused",
        )
    LOGGER.info("Completed: %s", json.dumps(summary, default=str))
    return summary
