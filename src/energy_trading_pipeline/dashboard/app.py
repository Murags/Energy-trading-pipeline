"""Streamlit review interface that reads only saved dashboard exports."""

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
)


def main() -> None:
	"""Render exported results; importing this module needs no Streamlit runtime."""
	import streamlit as st

	st.set_page_config(page_title="DE-FR Spread Forecasts", layout="wide")
	st.title("DE-FR Spread Forecasts")
	exports_dir = st.sidebar.text_input(
		"Exports directory", value="reports/dashboard_exports"
	)
	try:
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


if __name__ == "__main__":
	main()
