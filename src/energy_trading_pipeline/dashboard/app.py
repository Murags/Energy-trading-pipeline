"""Streamlit review interface that reads only saved dashboard exports."""

import os

import pandas as pd

from energy_trading_pipeline.dashboard.charts import (
	forecast_vs_actual_chart,
	monitoring_forecast_chart,
	retraining_events_chart,
	rolling_rmse_triggers_chart,
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


STRATEGY_LABELS = {
	"no_retraining": "No retraining",
	"fixed_schedule": "Fixed schedule",
	"performance_triggered": "Performance-triggered",
}
TRIGGER_LABELS = {
	"rolling_rmse_exceeds_threshold": "RMSE breach",
	"fixed_schedule_interval_elapsed": "Scheduled",
}
# Hourly detail over a whole multi-year run is unreadable, so the view opens on
# the last month: long enough to show several retraining cycles.
DEFAULT_WINDOW_DAYS = 30
# Sidebar dataset choice -> exports folder under the reports root (local or S3).
EXPORT_DATASETS = {
	"Experiment results": "dashboard_exports",
	"Synthetic demo": "dashboard_exports_demo",
}


def strategy_label(strategy: str) -> str:
	"""Readable name for a stable strategy identifier."""
	return STRATEGY_LABELS.get(strategy, strategy)


def short_model_label(model_version: str) -> str:
	"""Compact name for a model version: its refit number, or 'initial'."""
	if "_refit_" in model_version:
		return f"refit {model_version.rsplit('_refit_', 1)[1]}"
	return "initial"


def _format_eur(value: float) -> str:
	return "—" if pd.isna(value) else f"{value:.2f} €/MWh"


def _kpi(column, label: str, value: str, note: str, help_text: str | None = None):
	card = column.container(border=True)
	card.metric(label, value, help=help_text)
	card.caption(note)


def _date_window(
	chosen, first: pd.Timestamp, last: pd.Timestamp
) -> tuple[pd.Timestamp, pd.Timestamp]:
	"""Half-open UTC window for the chosen delivery dates."""
	if not isinstance(chosen, tuple) or len(chosen) != 2:
		return first, last + pd.Timedelta(hours=1)
	return (
		pd.Timestamp(chosen[0], tz="UTC"),
		pd.Timestamp(chosen[1], tz="UTC") + pd.Timedelta(days=1),
	)


def _render_backtest(st, exports_dir: str) -> None:
	"""Render the read-only monitoring view of the historical comparison."""
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

	# if artifacts["metrics"]["run_id"].astype(str).str.startswith("synthetic").any():
	# 	st.warning(
	# 		"Synthetic demo data: these exports were simulated for dashboard "
	# 		"testing and are not experiment results.",
	# 		icon="⚠️",
	# 	)

	available = sorted({
		strategy
		for name in ("forecasts", "metrics", "retraining_events")
		for strategy in artifacts[name]["strategy"].dropna().unique()
	})
	if not available or artifacts["forecasts"].empty:
		st.info("No exported strategies available.")
		return
	all_forecasts = artifacts["forecasts"]
	first = all_forecasts["timestamp"].min()
	last = all_forecasts["timestamp"].max()
	default_start = max(first, last - pd.Timedelta(days=DEFAULT_WINDOW_DAYS - 1))
	default_strategy = (
		"performance_triggered" if "performance_triggered" in available
		else available[0]
	)

	with st.container(border=True):
		form_column, export_column = st.columns(
			[6, 1], vertical_alignment="bottom"
		)
		with form_column, st.form("backtest_filters", border=False):
			date_column, strategy_column, apply_column = st.columns(
				[3, 3, 1.4], vertical_alignment="bottom"
			)
			chosen = date_column.date_input(
				"Date range (UTC)",
				value=(default_start.date(), last.date()),
				min_value=first.date(),
				max_value=last.date(),
			)
			strategy = strategy_column.selectbox(
				"Strategy",
				available,
				index=available.index(default_strategy),
				format_func=strategy_label,
			)
			apply_column.form_submit_button("Apply filters", width="stretch")

	start, end = _date_window(chosen, first, last)
	strategy_forecasts = all_forecasts.loc[all_forecasts["strategy"] == strategy]
	strategy_events = artifacts["retraining_events"].loc[
		artifacts["retraining_events"]["strategy"] == strategy
	]
	forecasts = filter_by_dates(strategy_forecasts, start, end)
	events = filter_by_dates(strategy_events, start, end)
	metrics = artifacts["metrics"]
	strategy_metrics = metrics.loc[metrics["strategy"] == strategy]

	export_column.download_button(
		"Export CSV",
		data=forecasts.to_csv(index=False).encode("utf-8"),
		file_name=(
			f"{strategy}_forecasts_{start.date()}_"
			f"{(end - pd.Timedelta(days=1)).date()}.csv"
		),
		mime="text/csv",
		width="stretch",
		disabled=forecasts.empty,
	)
	if forecasts.empty:
		st.info("No forecasts in the selected dates.")
		return

	scored = forecasts.dropna(subset=["rolling_rmse"])
	latest_rmse = scored["rolling_rmse"].iloc[-1] if not scored.empty else float("nan")
	mae = (
		strategy_metrics["mae"].iloc[0] if not strategy_metrics.empty
		else float("nan")
	)
	active_model = str(forecasts["model_version"].iloc[-1])
	serving_since = strategy_forecasts.loc[
		strategy_forecasts["model_version"] == active_model, "timestamp"
	].min()

	kpi_columns = st.columns(4)
	_kpi(
		kpi_columns[0], "Rolling RMSE", _format_eur(latest_rmse),
		f"latest stored value, {scored['timestamp'].iloc[-1]:%d %b %H:%M} UTC"
		if not scored.empty else "no scored hours in window",
	)
	_kpi(kpi_columns[1], "MAE", _format_eur(mae), "full evaluation window")
	_kpi(
		kpi_columns[2], "Retraining events", f"{len(events):,}",
		"in selected window",
	)
	_kpi(
		kpi_columns[3], "Active model", short_model_label(active_model),
		f"serving since {serving_since:%d %b %Y}", help_text=active_model,
	)

	chart_column, table_column = st.columns([2, 1.15])
	with chart_column.container(border=True):
		st.markdown("**Forecast vs Actual Spread (€/MWh)**")
		if forecasts["actual"].isna().all():
			st.info("Actual spreads unavailable.")
		st.plotly_chart(monitoring_forecast_chart(forecasts))
	with table_column.container(border=True):
		st.markdown("**Recent Retraining Events**")
		if events.empty:
			st.info("No retraining events in the selected window.")
		recent = events.sort_values("timestamp", ascending=False)
		st.dataframe(
			pd.DataFrame({
				"date": recent["timestamp"].dt.strftime("%d %b %Y"),
				"trigger": recent["trigger_reason"].map(
					lambda reason: TRIGGER_LABELS.get(reason, reason)
				),
				"rmse": recent["rolling_rmse"],
				"model_version": recent["model_version"],
			}),
			hide_index=True,
			height=330,
			column_config={
				"date": "Date",
				"trigger": "Trigger",
				"rmse": st.column_config.NumberColumn("RMSE", format="%.2f"),
				"model_version": None,
			},
		)

	chart_column, table_column = st.columns([2, 1.15])
	with chart_column.container(border=True):
		st.markdown("**Rolling RMSE and Retraining Triggers**")
		if forecasts["rolling_rmse"].isna().all():
			st.info("Rolling RMSE unavailable.")
		thresholds = strategy_events["threshold"].dropna()
		st.plotly_chart(rolling_rmse_triggers_chart(
			forecasts,
			events,
			thresholds.iloc[-1] if not thresholds.empty else None,
		))
	with table_column.container(border=True):
		st.markdown("**Strategy Comparison**")
		st.dataframe(
			metrics.assign(
				strategy=metrics["strategy"].map(strategy_label)
			)[["strategy", "rmse", "mae", "retraining_count"]],
			hide_index=True,
			column_config={
				"strategy": "Strategy",
				"rmse": st.column_config.NumberColumn("RMSE", format="%.2f"),
				"mae": st.column_config.NumberColumn("MAE", format="%.2f"),
				"retraining_count": "Retrains",
			},
		)
		for row in metrics[
			["run_id", "evaluation_start", "evaluation_end"]
		].drop_duplicates().itertuples(index=False):
			st.caption(
				f"Stored metrics for {row.evaluation_start:%d %b %Y} to "
				f"{row.evaluation_end:%d %b %Y} (run {row.run_id}); the date "
				"filter does not change them."
			)

	with st.expander("Exported rows for this view"):
		st.dataframe(forecasts, hide_index=True)


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

	st.set_page_config(
		page_title="DE–FR Day-Ahead Spread — Monitoring Dashboard", layout="wide",
		initial_sidebar_state="collapsed",
	)
	st.markdown("### DE–FR Day-Ahead Spread — Monitoring Dashboard")
	live_store_default = os.environ.get("ETP_STORE", "").strip()
	exports_root = (
		f"{live_store_default.rstrip('/')}/reports"
		if live_store_default.startswith("s3://")
		else "reports"
	)
	dataset = st.sidebar.radio("Backtest dataset", list(EXPORT_DATASETS))
	exports_default = f"{exports_root}/{EXPORT_DATASETS[dataset]}"
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
