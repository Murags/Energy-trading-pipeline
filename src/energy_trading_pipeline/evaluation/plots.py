"""Headless report figures from stored evaluation data, without metric calculation."""

import re
from datetime import timezone
from pathlib import Path

import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from pandas.api.types import is_bool_dtype, is_complex_dtype


STRATEGY_COLORS = {
	"no_retraining": "#0072b2",
	"fixed_schedule": "#d55e00",
	"performance_triggered": "#009e73",
}


def _plot_data(
	data: pd.DataFrame, columns: set[str], run_id: str
) -> pd.DataFrame:
	if not isinstance(run_id, str) or not re.fullmatch(
		r"[A-Za-z0-9][A-Za-z0-9_-]*", run_id
	):
		raise ValueError("run_id must be a nonempty safe directory name")
	if not isinstance(data, pd.DataFrame):
		raise ValueError("plot data must be a pandas DataFrame")
	if not data.columns.is_unique:
		raise ValueError("plot data has duplicate column names")
	missing = sorted(columns - set(data.columns))
	if missing:
		raise ValueError(f"Missing required plot columns: {missing}")
	if not data["strategy"].isin(STRATEGY_COLORS).all():
		raise ValueError("strategy must use a canonical retraining identifier")
	if "run_id" in data and not data["run_id"].eq(run_id).all():
		raise ValueError("plot data must belong to the supplied run_id")
	return data.copy(deep=True).reset_index(drop=True)


def _numeric_values(data: pd.DataFrame, column: str, *, missing: bool) -> None:
	message = f"{column} must contain finite real numeric values"
	values = data[column]
	if is_bool_dtype(values.dtype) or is_complex_dtype(values.dtype):
		raise ValueError(message)
	try:
		values = pd.to_numeric(values, errors="raise").astype("float64")
	except (ValueError, TypeError, OverflowError) as exc:
		raise ValueError(message) from exc
	if np.isinf(values).any() or (not missing and values.isna().any()):
		raise ValueError(message)
	data[column] = values


def _utc_values(values: pd.Series, column: str) -> pd.Series:
	timestamps = []
	message = f"{column} must contain valid timezone-aware timestamps"
	for value in values:
		try:
			timestamp = pd.Timestamp(value)
			if pd.isna(timestamp) or timestamp.tzinfo is None:
				raise ValueError(message)
			timestamps.append(timestamp.tz_convert("UTC").as_unit("ns"))
		except (ValueError, TypeError, OverflowError) as exc:
			raise ValueError(message) from exc
	return pd.Series(timestamps, index=values.index, dtype="datetime64[ns, UTC]")


def _time_data(
	data: pd.DataFrame, columns: set[str], run_id: str
) -> pd.DataFrame:
	result = _plot_data(data, columns | {"timestamp", "strategy"}, run_id)
	result["timestamp"] = _utc_values(result["timestamp"], "timestamp")
	if result.duplicated(["strategy", "timestamp"]).any():
		raise ValueError("plot data contains duplicate timestamps per strategy")
	return result.sort_values("timestamp", kind="stable").reset_index(drop=True)


def _time_axes(title: str, ylabel: str) -> tuple[Figure, Axes]:
	figure = Figure(figsize=(10, 4), layout="constrained")
	FigureCanvasAgg(figure)
	axes = figure.subplots()
	axes.set_title(title)
	axes.set_xlabel("Target timestamp (UTC)")
	axes.set_ylabel(ylabel)
	locator = mdates.AutoDateLocator(tz=timezone.utc)
	axes.xaxis.set_major_locator(locator)
	axes.xaxis.set_major_formatter(
		mdates.ConciseDateFormatter(locator, tz=timezone.utc)
	)
	axes.grid(axis="y", alpha=0.25)
	return figure, axes


def _empty_message(axes: Axes, message: str) -> None:
	axes.text(0.5, 0.5, message, ha="center", va="center", transform=axes.transAxes)


def _save_figure(
	figure: Figure, figures_dir: Path, plot_type: str, run_id: str
) -> Path:
	output = Path(figures_dir) / plot_type / f"{run_id}.png"
	output.parent.mkdir(parents=True, exist_ok=True)
	figure.savefig(output, format="png", dpi=180)
	return output


def plot_forecasts_vs_actuals(
	forecasts: pd.DataFrame, *, run_id: str, figures_dir: Path
) -> Path:
	"""Plot shared actual spreads and each strategy's predictions as a PNG.

	Require timestamp, strategy, prediction, and actual. Normalize aware timestamps
	to UTC and sort without mutation. Strategies must share a timeline and actuals.
	Missing actuals remain gaps. Pass the configured reports directory / figures;
	write forecasts_vs_actuals/<run_id>.png without training or metric calculation.
	"""
	data = _time_data(forecasts, {"prediction", "actual"}, run_id)
	_numeric_values(data, "prediction", missing=False)
	_numeric_values(data, "actual", missing=True)
	histories = [
		(strategy, data.loc[data["strategy"] == strategy].reset_index(drop=True))
		for strategy in STRATEGY_COLORS
		if data["strategy"].eq(strategy).any()
	]
	if histories:
		reference = histories[0][1]
		for strategy, history in histories[1:]:
			if not history["timestamp"].equals(reference["timestamp"]):
				raise ValueError("strategies must share the same evaluation timeline")
			if not history["actual"].equals(reference["actual"]):
				raise ValueError("strategies must share the same actuals")
	figure, axes = _time_axes(f"Forecasts vs actuals: {run_id}", "Spread (EUR/MWh)")
	if histories:
		axes.plot(
			reference["timestamp"], reference["actual"],
			label="Actual", color="#222222", linewidth=2,
		)
		for strategy, history in histories:
			axes.plot(
				history["timestamp"], history["prediction"],
				label=strategy, color=STRATEGY_COLORS[strategy], linewidth=1.2,
			)
		axes.legend(fontsize=8)
	else:
		_empty_message(axes, "No forecasts available")
	return _save_figure(figure, figures_dir, "forecasts_vs_actuals", run_id)


def plot_rolling_rmse(
	monitoring: pd.DataFrame, *, run_id: str, figures_dir: Path
) -> Path:
	"""Plot stored decision-time rolling_rmse values; never compute a window.

	Require timestamp, strategy, and rolling_rmse, with aware decision timestamps.
	Missing values denote insufficient history and remain gaps, not zeros.
	Write rolling_rmse/<run_id>.png under the caller's configured figures directory.
	"""
	data = _time_data(monitoring, {"rolling_rmse"}, run_id)
	_numeric_values(data, "rolling_rmse", missing=True)
	if data["rolling_rmse"].lt(0).any():
		raise ValueError("rolling_rmse must be nonnegative")
	figure, axes = _time_axes(f"Rolling RMSE: {run_id}", "Rolling RMSE (EUR/MWh)")
	axes.set_xlabel("Decision timestamp (UTC)")
	for strategy, color in STRATEGY_COLORS.items():
		history = data.loc[data["strategy"] == strategy]
		if not history.empty:
			axes.plot(
				history["timestamp"], history["rolling_rmse"],
				label=strategy, color=color, linewidth=1.5,
			)
	if axes.lines:
		axes.legend(fontsize=8)
	if data.empty:
		_empty_message(axes, "No rolling RMSE records available")
	elif data["rolling_rmse"].isna().all():
		_empty_message(axes, "Insufficient history for rolling RMSE")
	return _save_figure(figure, figures_dir, "rolling_rmse", run_id)


def plot_retraining_events(
	retraining_events: pd.DataFrame, *, run_id: str, figures_dir: Path
) -> Path:
	"""Render timestamp/strategy event markers, including lanes without events.

	Supply completed retrains only, excluding initial training and policy requests.
	No events are inferred from model changes, thresholds, or missing records.
	Write retraining_events/<run_id>.png; an empty log has an explicit message.
	"""
	data = _time_data(retraining_events, set(), run_id)
	figure, axes = _time_axes(f"Completed retraining events: {run_id}", "Strategy")
	axes.set_xlabel("Retraining timestamp (UTC)")
	for position, (strategy, color) in enumerate(STRATEGY_COLORS.items()):
		history = data.loc[data["strategy"] == strategy]
		if not history.empty:
			axes.scatter(
				history["timestamp"], np.full(len(history), position),
				marker="|", s=180, linewidths=2, color=color,
			)
	axes.set_yticks(range(len(STRATEGY_COLORS)), list(STRATEGY_COLORS), fontsize=8)
	axes.set_ylim(-0.5, len(STRATEGY_COLORS) - 0.5)
	if data.empty:
		_empty_message(axes, "No retraining events recorded")
	elif data["timestamp"].nunique() == 1:
		timestamp = data["timestamp"].iloc[0]
		padding = pd.Timedelta(hours=1)
		axes.set_xlim(timestamp - padding, timestamp + padding)
	return _save_figure(figure, figures_dir, "retraining_events", run_id)


def plot_strategy_comparison(
	comparison: pd.DataFrame, *, run_id: str, figures_dir: Path
) -> Path:
	"""Plot Story 8.2's exported metrics in four separately labelled panels.

	Require run_id, UTC-aware evaluation_start/end, strategy, rmse, mae,
	retraining_count, and retraining_frequency. Require one row per strategy for
	the same run and half-open period. Frequency is completed retrains per day.
	Missing scores remain unavailable, not zero. No metrics are recalculated.
	Write strategy_comparison/<run_id>.png without mutating the input table.
	"""
	panels = (
		("rmse", "RMSE", "EUR/MWh"),
		("mae", "MAE", "EUR/MWh"),
		("retraining_count", "Retraining count", "Completed retrains"),
		("retraining_frequency", "Retraining frequency", "Completed retrains/day"),
	)
	columns = {"run_id", "evaluation_start", "evaluation_end", "strategy"}
	data = _plot_data(comparison, columns | {panel[0] for panel in panels}, run_id)
	if data["strategy"].duplicated().any():
		raise ValueError("comparison contains duplicate strategies")
	for column in ("evaluation_start", "evaluation_end"):
		data[column] = _utc_values(data[column], column)
		if data[column].nunique() > 1:
			raise ValueError("comparison must share the same evaluation window")
	if data["evaluation_start"].ge(data["evaluation_end"]).any():
		raise ValueError("evaluation_start must precede evaluation_end")
	for column, title, unit in panels:
		_numeric_values(data, column, missing=column in {"rmse", "mae"})
		if data[column].lt(0).any():
			raise ValueError(f"{column} must be nonnegative")
	if data["retraining_count"].mod(1).ne(0).any():
		raise ValueError("retraining_count must contain integer counts")
	strategies = [
		strategy for strategy in STRATEGY_COLORS if strategy in set(data["strategy"])
	]
	data = data.set_index("strategy").reindex(strategies).reset_index()
	figure = Figure(figsize=(12, 6), layout="constrained")
	FigureCanvasAgg(figure)
	title = f"Strategy comparison: {run_id}"
	if not data.empty:
		start = data["evaluation_start"].iloc[0].strftime("%Y-%m-%d %H:%M")
		end = data["evaluation_end"].iloc[0].strftime("%Y-%m-%d %H:%M")
		title += f"\n{start} to {end} (UTC, end exclusive)"
	figure.suptitle(title, fontsize=12)
	for axes, (column, title, unit) in zip(figure.subplots(2, 2).flat, panels):
		axes.set_title(title, fontsize=11)
		axes.set_xlabel(unit)
		axes.grid(axis="x", alpha=0.25)
		if data.empty:
			_empty_message(axes, "No comparison records available")
			continue
		positions = np.arange(len(data))
		axes.barh(
			positions, data[column],
			color=[STRATEGY_COLORS[strategy] for strategy in strategies],
		)
		axes.set_yticks(positions, strategies, fontsize=8)
		axes.invert_yaxis()
		axes.set_xlim(left=0)
		for position, value in enumerate(data[column]):
			if pd.isna(value):
				axes.text(
					0.02, position, "Not available", va="center", fontsize=8,
					transform=axes.get_yaxis_transform(),
				)
	return _save_figure(figure, figures_dir, "strategy_comparison", run_id)
