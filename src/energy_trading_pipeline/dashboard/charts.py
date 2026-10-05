"""Read-only Plotly views of exported forecast and evaluation observations."""

import pandas as pd
import plotly.graph_objects as go


STRATEGY_COLORS = {
	"no_retraining": "#2878B5",
	"fixed_schedule": "#23875B",
	"performance_triggered": "#C44747",
}


def _figure(y_title: str, *, time_axis: bool = True) -> go.Figure:
	figure = go.Figure()
	figure.update_layout(
		template="plotly_white",
		xaxis_title="Timestamp (UTC)" if time_axis else "Strategy",
		yaxis_title=y_title,
		hovermode="x unified" if time_axis else "closest",
		margin={"l": 20, "r": 20, "t": 20, "b": 20},
		legend={"orientation": "h", "y": -0.25},
	)
	if time_axis:
		figure.update_xaxes(type="date")
	return figure


def forecast_vs_actual_chart(forecasts: pd.DataFrame) -> go.Figure:
	"""Plot each strategy's stored predictions and actual spreads, keeping gaps."""
	figure = _figure("Spread (EUR/MWh)")
	for strategy, rows in forecasts.sort_values("timestamp").groupby("strategy"):
		for column in ("prediction", "actual"):
			figure.add_trace(go.Scatter(
				x=rows["timestamp"].tolist(),
				y=rows[column].tolist(),
				name=f"{strategy}: {column}",
				legendgroup=str(strategy),
				mode="lines+markers",
				connectgaps=False,
				line={
					"color": STRATEGY_COLORS.get(str(strategy)),
					"dash": "dash" if column == "actual" else "solid",
				},
			))
	return figure


def rolling_rmse_chart(forecasts: pd.DataFrame) -> go.Figure:
	"""Plot exported rolling RMSE without filling gaps or recalculating scores."""
	figure = _figure("Rolling RMSE (EUR/MWh)")
	for strategy, rows in forecasts.sort_values("timestamp").groupby("strategy"):
		figure.add_trace(go.Scatter(
			x=rows["timestamp"].tolist(),
			y=rows["rolling_rmse"].tolist(),
			name=str(strategy),
			mode="lines+markers",
			connectgaps=False,
			line={"color": STRATEGY_COLORS.get(str(strategy))},
		))
	return figure


def retraining_events_chart(events: pd.DataFrame) -> go.Figure:
	"""Show saved retraining decisions on a strategy timeline with metadata."""
	figure = _figure("Strategy")
	figure.update_layout(hovermode="closest")
	for strategy, rows in events.sort_values("timestamp").groupby("strategy"):
		figure.add_trace(go.Scatter(
			x=rows["timestamp"].tolist(),
			y=rows["strategy"].tolist(),
			name=str(strategy),
			mode="markers",
			marker={"size": 10, "color": STRATEGY_COLORS.get(str(strategy))},
			customdata=rows[
				["trigger_reason", "model_version", "rolling_rmse", "threshold"]
			].to_numpy(),
			hovertemplate=(
				"%{x}<br>%{y}<br>Reason: %{customdata[0]}"
				"<br>Model: %{customdata[1]}<br>RMSE: %{customdata[2]}"
				"<br>Threshold: %{customdata[3]}<extra></extra>"
			),
		))
	return figure


def model_versions_chart(forecasts: pd.DataFrame) -> go.Figure:
	"""Show the active forecast model over time, including step changes."""
	figure = _figure("Model version")
	figure.update_yaxes(type="category")
	for strategy, rows in forecasts.sort_values("timestamp").groupby("strategy"):
		figure.add_trace(go.Scatter(
			x=rows["timestamp"].tolist(),
			y=rows["model_version"].tolist(),
			name=str(strategy),
			mode="lines+markers",
			connectgaps=False,
			line={"shape": "hv", "color": STRATEGY_COLORS.get(str(strategy))},
		))
	return figure


def strategy_comparison_chart(metrics: pd.DataFrame) -> go.Figure:
	"""Compare saved RMSE and MAE values without deriving new metrics."""
	figure = _figure("Error (EUR/MWh)", time_axis=False)
	figure.update_layout(barmode="group")
	if not metrics.empty:
		for column, color in (("rmse", "#2878B5"), ("mae", "#23875B")):
			figure.add_trace(go.Bar(
				x=metrics["strategy"].tolist(),
				y=metrics[column].tolist(),
				name=column.upper(),
				marker_color=color,
			))
	return figure
