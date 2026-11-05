"""Streamlit review interface that reads only saved dashboard exports."""

import os

import pandas as pd

from energy_trading_pipeline.dashboard.charts import (
	forecast_vs_actual_chart,
	model_versions_chart,
	retraining_events_chart,
	rolling_rmse_chart,
	strategy_comparison_chart,
)
from energy_trading_pipeline.dashboard.data_loader import (
	DashboardArtifactError,
	load_dashboard_artifacts,
	load_live_artifacts,
)


def filter_by_dates(
	frame: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp
) -> pd.DataFrame:
	"""Return rows in the half-open UTC interval, leaving stored values untouched.

	Filtering is display-only. It never recomputes a metric, so a narrowed view
	shows the same numbers the export recorded for those hours.
	"""
	if frame.empty:
		return frame
	timestamps = frame["timestamp"]
	return frame.loc[(timestamps >= start) & (timestamps < end)].copy()


def _apply_date_filter(
	st, forecasts: pd.DataFrame, events: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, tuple[pd.Timestamp, pd.Timestamp]]:
	"""Offer a delivery-date range so hourly detail is legible on long runs."""
	first = forecasts["timestamp"].min()
	last = forecasts["timestamp"].max()
	st.sidebar.caption(
		f"{len(forecasts):,} forecast rows from {first.date()} to {last.date()}"
	)
	# A year of hourly points per strategy is unreadable at full extent, so the
	# default view is the last week rather than everything.
	default_start = max(first, last - pd.Timedelta(days=6)).date()
	chosen = st.sidebar.date_input(
		"Delivery dates (UTC)",
		value=(default_start, last.date()),
		min_value=first.date(),
		max_value=last.date(),
	)
	if not isinstance(chosen, tuple) or len(chosen) != 2:
		return forecasts, events, (first, last)
	start = pd.Timestamp(chosen[0], tz="UTC")
	end = pd.Timestamp(chosen[1], tz="UTC") + pd.Timedelta(days=1)
	if st.sidebar.checkbox("Show the whole run instead", value=False):
		start, end = first, last + pd.Timedelta(hours=1)
	return (
		filter_by_dates(forecasts, start, end),
		filter_by_dates(events, start, end),
		(start, end),
	)


def _render_backtest(st, exports_dir: str) -> None:
	"""Render the existing read-only historical comparison view."""
	try:
		if exports_dir.startswith("s3://"):
			cached_loader = st.cache_data(
				ttl=300, show_spinner="Reading backtest exports…"
			)(load_dashboard_artifacts)
			artifacts = cached_loader(exports_dir)
		else:
			artifacts = load_dashboard_artifacts(exports_dir)
	except DashboardArtifactError as error:
		st.error(str(error))
		return

	available = sorted({
		strategy
		for name in ("forecasts", "metrics", "retraining_events")
		for strategy in artifacts[name]["strategy"].dropna().unique()
	})
	if not available:
		st.info("No exported strategies available.")
		return
	selected = st.sidebar.multiselect("Strategies", available, default=available)
	if not selected:
		st.info("No strategies selected.")
		return

	forecasts, metrics, events = (
		artifacts[name].loc[artifacts[name]["strategy"].isin(selected)].copy()
		for name in ("forecasts", "metrics", "retraining_events")
	)
	forecasts, events, window = _apply_date_filter(st, forecasts, events)
	if forecasts.empty:
		st.info("No forecasts in the selected dates.")
		return
	referenced_versions = pd.concat([
		forecasts["model_version"], events["model_version"]
	]).dropna().unique()
	models = artifacts["model_versions"].loc[
		artifacts["model_versions"]["model_version"].isin(referenced_versions)
	]

	for row in metrics[
		["run_id", "evaluation_start", "evaluation_end"]
	].drop_duplicates().itertuples(index=False):
		st.caption(
			f"Run: {row.run_id} | Evaluation: {row.evaluation_start.isoformat()} "
			f"to {row.evaluation_end.isoformat()}"
		)
	st.subheader("Error Summary")
	st.caption(
		"Exported metrics cover the whole evaluation window. The date filter "
		"narrows the charts and tables below, never these numbers."
	)
	if metrics.empty:
		st.info("No metric summaries for the selected strategies.")
	st.dataframe(
		metrics[[
			"strategy", "rmse", "mae", "retraining_count", "retraining_frequency"
		]],
		hide_index=True,
		column_config={
			"strategy": "Strategy",
			"rmse": st.column_config.NumberColumn("RMSE (EUR/MWh)", format="%.3f"),
			"mae": st.column_config.NumberColumn("MAE (EUR/MWh)", format="%.3f"),
			"retraining_count": "Retraining Count",
			"retraining_frequency": "Retrainings / Day",
		},
	)

	forecast_tab, rolling_tab, events_tab, models_tab, comparison_tab = st.tabs(
		["Forecasts", "Rolling RMSE", "Retraining", "Models", "Comparison"]
	)
	with forecast_tab:
		st.subheader("Forecast vs Actual")
		days = (window[1] - window[0]) / pd.Timedelta(days=1)
		st.caption(
			f"Showing {len(forecasts):,} rows over {days:.0f} day(s). "
			"Each delivery day's 24 hours are issued together at 10:00 "
			"Europe/Berlin on the preceding day."
		)
		if forecasts.empty:
			st.info("No forecasts for the selected strategies.")
		elif forecasts["actual"].isna().all():
			st.info("Actual spreads unavailable.")
		st.plotly_chart(forecast_vs_actual_chart(forecasts))
		st.dataframe(
			forecasts.drop(columns="rolling_rmse"),
			hide_index=True,
		)
	with rolling_tab:
		st.subheader("Rolling RMSE")
		if forecasts["rolling_rmse"].isna().all():
			st.info("Rolling RMSE unavailable.")
		st.plotly_chart(rolling_rmse_chart(forecasts))
		st.dataframe(
			forecasts[["timestamp", "strategy", "rolling_rmse"]],
			hide_index=True,
		)
	with events_tab:
		st.subheader("Retraining Events")
		if events.empty:
			st.info("No retraining events for the selected strategies.")
		st.plotly_chart(retraining_events_chart(events))
		st.dataframe(events, hide_index=True)
	with models_tab:
		st.subheader("Model Version Changes")
		if forecasts.empty:
			st.info("No forecast model history for the selected strategies.")
		st.plotly_chart(model_versions_chart(forecasts))
		st.dataframe(models, hide_index=True)
	with comparison_tab:
		st.subheader("Strategy Comparison")
		st.plotly_chart(strategy_comparison_chart(metrics))
		st.dataframe(metrics, hide_index=True)


def _render_live(st, destination: str) -> None:
	"""Render persisted daily forecasts without invoking any pipeline stage."""
	st.subheader("Live Daily Forecast")
	try:
		cached_loader = st.cache_data(ttl=60, show_spinner="Reading live artifacts…")(
			load_live_artifacts
		)
		artifacts = cached_loader(destination)
	except DashboardArtifactError as error:
		st.error(str(error))
		return

	latest = artifacts["latest_run"]
	for field in ("ran_at", "issuance", "delivery_date", "market_through"):
		if field not in latest:
			st.error(f"Live artifact 'live/latest_run.yaml' is missing '{field}'.")
			return
	st.caption(
		f"Last run: {latest['ran_at']} | Issuance: {latest['issuance']} | "
		f"Delivery: {latest['delivery_date']} | Market through: "
		f"{latest['market_through']}"
	)

	available = sorted(artifacts["forecasts"]["strategy"].dropna().unique())
	selected = st.sidebar.multiselect(
		"Live strategies", available, default=available, key="live_strategies"
	)
	if not selected:
		st.info("No live strategies selected.")
		return
	forecasts = artifacts["forecasts"].loc[
		artifacts["forecasts"]["strategy"].isin(selected)
	].copy()
	events = artifacts["retraining_events"].loc[
		artifacts["retraining_events"]["strategy"].isin(selected)
	].copy()
	states = artifacts["states"].loc[
		artifacts["states"]["strategy"].isin(selected)
	].copy()

	delivery_dates = sorted(forecasts["delivery_date"].dropna().unique(), reverse=True)
	if not delivery_dates:
		st.info("No live forecast delivery days are available.")
		return
	delivery = st.selectbox("Delivery date", delivery_dates, key="live_delivery_date")
	delivery_forecasts = forecasts.loc[forecasts["delivery_date"] == delivery].copy()

	st.markdown("#### Strategy state")
	st.dataframe(states, hide_index=True)
	st.markdown("#### Forecast vs actual")
	if delivery_forecasts["actual"].isna().all():
		st.info("Actual spreads are not available for this delivery day yet.")
	st.plotly_chart(forecast_vs_actual_chart(delivery_forecasts))
	st.dataframe(delivery_forecasts, hide_index=True)
	st.markdown("#### Retraining events")
	if events.empty:
		st.info("No live retraining events have been recorded.")
	else:
		st.plotly_chart(retraining_events_chart(events))
	st.dataframe(events, hide_index=True)


def main() -> None:
	"""Render saved backtest exports and optional live S3 artifacts."""
	import streamlit as st

	st.set_page_config(page_title="DE-FR Spread Forecasts", layout="wide")
	st.title("DE-FR Spread Forecasts")
	live_store_default = os.environ.get("ETP_STORE", "").strip()
	exports_default = (
		f"{live_store_default.rstrip('/')}/reports/dashboard_exports"
		if live_store_default.startswith("s3://")
		else "reports/dashboard_exports"
	)
	exports_dir = st.sidebar.text_input(
		"Exports directory",
		value=exports_default,
		disabled=live_store_default.startswith("s3://"),
	)
	live_store = st.sidebar.text_input(
		"Live artifact store",
		value=live_store_default,
		disabled=bool(live_store_default),
	).strip()
	if live_store:
		live_tab, backtest_tab = st.tabs(["Live", "Backtest"])
		with live_tab:
			_render_live(st, live_store)
		with backtest_tab:
			_render_backtest(st, exports_dir)
	else:
		_render_backtest(st, exports_dir)


if __name__ == "__main__":
	main()
