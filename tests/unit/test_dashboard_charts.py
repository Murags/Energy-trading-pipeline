"""Dashboard figures use exported observations without changing their values."""

import numpy as np
import pandas as pd
import pytest
from plotly.graph_objects import Figure

from energy_trading_pipeline.dashboard import charts


@pytest.fixture
def chart_frames():
    timestamps = pd.date_range("2024-01-01", periods=3, freq="h", tz="UTC")
    forecasts = pd.DataFrame(
        [
            {
                "timestamp": timestamp,
                "strategy": strategy,
                "prediction": float(position),
                "actual": np.nan if position == 1 else float(position + 1),
                "rolling_rmse": np.nan if position == 0 else float(position),
                "model_version": "model_a" if position < 2 else "model_b",
            }
            for strategy in ("fixed_schedule", "no_retraining")
            for position, timestamp in enumerate(timestamps)
        ]
    ).iloc[::-1].reset_index(drop=True)
    return {
        "forecasts": forecasts,
        "events": pd.DataFrame({
            "timestamp": [timestamps[2]],
            "strategy": ["fixed_schedule"],
            "trigger_reason": ["scheduled"],
            "threshold": [np.nan],
            "rolling_rmse": [2.0],
            "model_version": ["model_b"],
        }),
        "metrics": pd.DataFrame({
            "strategy": ["fixed_schedule", "no_retraining"],
            "rmse": [123.0, 456.0],
            "mae": [12.0, 45.0],
        }),
    }


CHART_INPUTS = [
    ("forecast_vs_actual_chart", "forecasts"),
    ("rolling_rmse_chart", "forecasts"),
    ("retraining_events_chart", "events"),
    ("model_versions_chart", "forecasts"),
    ("strategy_comparison_chart", "metrics"),
]


@pytest.mark.parametrize("function_name,frame_name", CHART_INPUTS)
def test_charts_return_figures_without_mutating_inputs(
    chart_frames, function_name, frame_name
):
    frame = chart_frames[frame_name]
    original = frame.copy(deep=True)
    figure = getattr(charts, function_name)(frame)
    assert isinstance(figure, Figure)
    assert len(figure.data) > 0
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize("function_name,frame_name", CHART_INPUTS)
def test_charts_accept_empty_exports(chart_frames, function_name, frame_name):
    figure = getattr(charts, function_name)(chart_frames[frame_name].iloc[:0])
    assert isinstance(figure, Figure)
    assert not figure.data


def test_forecast_chart_separates_strategies_and_preserves_missing_actuals(
    chart_frames,
):
    figure = charts.forecast_vs_actual_chart(chart_frames["forecasts"])
    assert len(figure.data) == 4
    for trace in figure.data:
        assert trace.legendgroup in ("fixed_schedule", "no_retraining")
        assert pd.DatetimeIndex(trace.x).is_monotonic_increasing
        assert trace.connectgaps is False
        assert trace.mode == "lines+markers"
        values = [1.0, np.nan, 3.0] if "actual" in trace.name else [0.0, 1.0, 2.0]
        np.testing.assert_equal(list(trace.y), values)


def test_rolling_rmse_chart_uses_stored_values(chart_frames):
    figure = charts.rolling_rmse_chart(chart_frames["forecasts"])
    assert len(figure.data) == 2
    for trace in figure.data:
        np.testing.assert_equal(list(trace.y), [np.nan, 1.0, 2.0])
        assert trace.connectgaps is False
        assert trace.mode == "lines+markers"
        assert pd.DatetimeIndex(trace.x).is_monotonic_increasing


def test_events_show_timestamp_strategy_and_model_metadata(chart_frames):
    figure = charts.retraining_events_chart(chart_frames["events"])
    trace = figure.data[0]
    assert trace.mode == "markers"
    assert list(trace.y) == ["fixed_schedule"]
    assert list(trace.x) == list(chart_frames["events"]["timestamp"])
    assert "scheduled" in list(trace.customdata[0])
    assert "model_b" in list(trace.customdata[0])


def test_model_chart_shows_chronological_step_changes(chart_frames):
    figure = charts.model_versions_chart(chart_frames["forecasts"])
    for trace in figure.data:
        assert list(trace.y) == ["model_a", "model_a", "model_b"]
        assert trace.line.shape == "hv"
        assert pd.DatetimeIndex(trace.x).is_monotonic_increasing


def test_comparison_chart_does_not_recalculate_metrics(chart_frames):
    figure = charts.strategy_comparison_chart(chart_frames["metrics"])
    assert figure.layout.barmode == "group"
    assert [trace.name for trace in figure.data] == ["RMSE", "MAE"]
    assert list(figure.data[0].y) == [123.0, 456.0]
    assert list(figure.data[1].y) == [12.0, 45.0]