"""In-memory core metric aggregation from canonical experiment logs."""

import pandas as pd

from energy_trading_pipeline.backtesting.forecast_log import build_forecast_log
from energy_trading_pipeline.monitoring.metrics import calculate_mae, calculate_rmse
from energy_trading_pipeline.retraining.events import build_retraining_events


STRATEGY_METRIC_COLUMNS = (
	"strategy",
	"rmse",
	"mae",
	"retraining_count",
	"retraining_frequency",
)


def _evaluation_timestamp(value: pd.Timestamp, column: str) -> pd.Timestamp:
	message = f"{column} must be a valid timezone-aware pandas timestamp"
	if not isinstance(value, pd.Timestamp) or pd.isna(value) or value.tzinfo is None:
		raise ValueError(message)
	try:
		return value.tz_convert("UTC").as_unit("ns")
	except (ValueError, OverflowError) as exc:
		raise ValueError(message) from exc


def calculate_strategy_metrics(
	forecasts: pd.DataFrame,
	retraining_events: pd.DataFrame,
	*,
	evaluation_start: pd.Timestamp,
	evaluation_end: pd.Timestamp,
) -> pd.DataFrame:
	"""Return core metrics per input strategy for [start, end), without mutation.

	Require canonical forecast inputs and the full retraining event schema.
	Normalize aware timestamps to UTC and recompute errors from actual/prediction.
	Strategies must share target timestamps and actuals, including missingness.
	Duplicate strategy/target pairs and strategy/event-time pairs fail clearly.
	Missing actuals are excluded from both error metrics; no observations yield
	NaN, not zero. Strategies are returned in deterministic alphabetical order.

	Count only events in the same half-open window. The caller must supply
	completed retrains, excluding initial training and unexecuted policy requests.
	Frequency is event count divided by elapsed UTC days, not by scored rows;
	missing actuals never shorten the denominator. Events without a represented
	forecast strategy fail. No events means zero count/frequency. Empty input
	logs return an empty result with stable columns and dtypes. No files are written.
	"""
	start = _evaluation_timestamp(evaluation_start, "evaluation_start")
	end = _evaluation_timestamp(evaluation_end, "evaluation_end")
	if start >= end:
		raise ValueError("evaluation_start must precede evaluation_end")
	duration_days = (end - start) / pd.Timedelta(days=1)
	if not isinstance(forecasts, pd.DataFrame):
		raise ValueError("forecasts must be a pandas DataFrame")
	forecasts = build_forecast_log(forecasts)
	events = build_retraining_events(retraining_events)
	strategies = sorted(forecasts["strategy"].unique())
	forecasts = forecasts.loc[
		(forecasts["timestamp"] >= start) & (forecasts["timestamp"] < end)
	]
	events = events.loc[(events["timestamp"] >= start) & (events["timestamp"] < end)]
	if forecasts.duplicated(["strategy", "timestamp"]).any():
		raise ValueError("forecasts contain duplicate target timestamps per strategy")
	if events.duplicated(["strategy", "timestamp"]).any():
		raise ValueError("events contain duplicate retraining events per strategy")
	if not events["strategy"].isin(strategies).all():
		raise ValueError("retraining events contain a strategy without forecasts")

	rows = []
	reference: pd.DataFrame | None = None
	for strategy in strategies:
		history = forecasts.loc[forecasts["strategy"] == strategy].reset_index(
			drop=True
		)
		if reference is not None:
			if not history["timestamp"].equals(reference["timestamp"]):
				raise ValueError("strategies must share the same evaluation timeline")
			if not history["actual"].equals(reference["actual"]):
				raise ValueError("strategies must share the same actuals")
		else:
			reference = history
		retraining_count = int((events["strategy"] == strategy).sum())
		rows.append(
			{
				"strategy": strategy,
				"rmse": calculate_rmse(history["actual"], history["prediction"]),
				"mae": calculate_mae(history["actual"], history["prediction"]),
				"retraining_count": retraining_count,
				"retraining_frequency": retraining_count / duration_days,
			}
		)
	return pd.DataFrame(rows, columns=list(STRATEGY_METRIC_COLUMNS)).astype(
		{
			"strategy": "string",
			"rmse": "float64",
			"mae": "float64",
			"retraining_count": "int64",
			"retraining_frequency": "float64",
		}
	)
