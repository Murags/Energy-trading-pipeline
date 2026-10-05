"""Headless evaluation figures from small, deliberately unsorted fixtures."""

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.image as mpimg
import numpy as np
import pandas as pd
import pytest
from matplotlib.figure import Figure

from energy_trading_pipeline.evaluation import plots


RUN_ID = "run_20261005_120000"
STRATEGIES = ["no_retraining", "fixed_schedule", "performance_triggered"]


@pytest.fixture
def forecasts():
    timestamps = pd.date_range("2024-01-01", periods=4, freq="h", tz="UTC")
    return pd.DataFrame(
        [
            {
                "timestamp": timestamp,
                "strategy": strategy,
                "prediction": actual + offset,
                "actual": actual,
            }
            for offset, strategy in enumerate(STRATEGIES)
            for timestamp, actual in zip(timestamps, [-2.0, 0.0, 3.0, 1.0])
        ]
    ).iloc[::-1].reset_index(drop=True)


@pytest.fixture
def captured_figures(monkeypatch):
    figures = []
    savefig = Figure.savefig

    def capture(figure, *args, **kwargs):
        figures.append(figure)
        return savefig(figure, *args, **kwargs)

    monkeypatch.setattr(Figure, "savefig", capture)
    return figures


def assert_png(path: Path):
    assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    pixels = mpimg.imread(path)
    assert pixels.shape[0] >= 600
    assert pixels.shape[1] >= 1000
    assert float(pixels.max() - pixels.min()) > 0.5


def test_forecasts_render_sorted_shared_actuals_without_mutation(
    tmp_path, forecasts, captured_figures
):
    original = forecasts.copy(deep=True)
    figures_dir = tmp_path / "reports" / "figures"
    path = plots.plot_forecasts_vs_actuals(
        forecasts, run_id=RUN_ID, figures_dir=figures_dir
    )
    assert path == figures_dir / "forecasts_vs_actuals" / f"{RUN_ID}.png"
    assert_png(path)
    pd.testing.assert_frame_equal(forecasts, original)
    axes = captured_figures[0].axes[0]
    assert len(axes.lines) == 4
    assert {line.get_label() for line in axes.lines} == {"Actual", *STRATEGIES}
    assert axes.get_ylabel() == "Spread (EUR/MWh)"
    assert axes.get_xlabel() == "Target timestamp (UTC)"
    for line in axes.lines:
        assert pd.DatetimeIndex(line.get_xdata()).is_monotonic_increasing
    actual = next(line for line in axes.lines if line.get_label() == "Actual")
    np.testing.assert_equal(actual.get_ydata(), [-2.0, 0.0, 3.0, 1.0])


@pytest.mark.parametrize("scenario", ["missing_actuals", "empty"])
def test_forecasts_handle_missing_actuals_and_empty_logs(
    tmp_path, forecasts, captured_figures, scenario
):
    if scenario == "empty":
        forecasts = forecasts.iloc[:0]
    else:
        forecasts["actual"] = pd.NA
    path = plots.plot_forecasts_vs_actuals(
        forecasts, run_id=RUN_ID, figures_dir=tmp_path
    )
    assert_png(path)
    axes = captured_figures[0].axes[0]
    if scenario == "empty":
        assert any("No forecasts" in text.get_text() for text in axes.texts)
    else:
        actual = next(line for line in axes.lines if line.get_label() == "Actual")
        assert np.isnan(actual.get_ydata()).all()


@pytest.mark.parametrize(
    "invalid, message",
    [
        ("column", "Missing required"),
        ("strategy", "strategy"),
        ("timestamp", "timestamp"),
        ("duplicate", "duplicate"),
        ("prediction", "prediction"),
        ("actual", "actual"),
        ("timeline", "timeline"),
        ("actual_mismatch", "actuals"),
        ("run_id", "run_id"),
    ],
)
def test_invalid_forecasts_fail_before_writing(tmp_path, forecasts, invalid, message):
    run_id = RUN_ID
    if invalid == "column":
        forecasts = forecasts.drop(columns="prediction")
    elif invalid == "strategy":
        forecasts.loc[0, "strategy"] = "unknown"
    elif invalid == "timestamp":
        forecasts["timestamp"] = forecasts["timestamp"].dt.tz_localize(None)
    elif invalid == "duplicate":
        forecasts = pd.concat([forecasts, forecasts.iloc[:1]], ignore_index=True)
    elif invalid in {"prediction", "actual"}:
        forecasts.loc[0, invalid] = np.inf
    elif invalid == "timeline":
        forecasts = forecasts.iloc[1:]
    elif invalid == "actual_mismatch":
        forecasts.loc[0, "actual"] = 99.0
    else:
        run_id = "../escape"
    figures_dir = tmp_path / "reports" / "figures"
    with pytest.raises(ValueError, match=message):
        plots.plot_forecasts_vs_actuals(
            forecasts, run_id=run_id, figures_dir=figures_dir
        )
    assert not figures_dir.exists()


@pytest.fixture
def comparison():
    return pd.DataFrame(
        {
            "run_id": RUN_ID,
            "evaluation_start": pd.Timestamp("2024-01-01T00:00:00Z"),
            "evaluation_end": pd.Timestamp("2024-01-03T00:00:00Z"),
            "strategy": STRATEGIES,
            "rmse": [9.0, 4.0, 2.0],
            "mae": [8.0, 3.0, 1.0],
            "retraining_count": [0, 2, 1],
            "retraining_frequency": [0.0, 1.0, 0.5],
        }
    ).iloc[::-1].reset_index(drop=True)


@pytest.mark.parametrize("scenario", ["normal", "no_scores", "empty"])
def test_strategy_comparison_renders_stored_metrics_with_distinct_units(
    tmp_path, comparison, captured_figures, scenario
):
    if scenario == "empty":
        comparison = comparison.iloc[:0]
    elif scenario == "no_scores":
        comparison["rmse"] = pd.NA
        comparison["mae"] = pd.NA
    original = comparison.copy(deep=True)
    path = plots.plot_strategy_comparison(
        comparison, run_id=RUN_ID, figures_dir=tmp_path
    )
    assert path == tmp_path / "strategy_comparison" / f"{RUN_ID}.png"
    assert_png(path)
    pd.testing.assert_frame_equal(comparison, original)
    figure = captured_figures[0]
    assert len(figure.axes) == 4
    metrics = ["rmse", "mae", "retraining_count", "retraining_frequency"]
    units = ["EUR/MWh", "EUR/MWh", "Completed retrains", "Completed retrains/day"]
    for axes, metric, unit in zip(figure.axes, metrics, units):
        assert axes.get_xlabel() == unit
        if scenario == "empty":
            assert any("No comparison" in text.get_text() for text in axes.texts)
        else:
            assert [label.get_text() for label in axes.get_yticklabels()] == STRATEGIES
            expected = comparison.set_index("strategy").loc[STRATEGIES, metric]
            if scenario == "no_scores" and metric in {"rmse", "mae"}:
                assert all(np.isnan(patch.get_width()) for patch in axes.patches)
                assert sum(
                    text.get_text() == "Not available" for text in axes.texts
                ) == 3
            else:
                np.testing.assert_equal(
                    [patch.get_width() for patch in axes.patches], expected.to_numpy()
                )
    if scenario != "empty":
        assert "2024-01-01" in figure._suptitle.get_text()
        assert "2024-01-03" in figure._suptitle.get_text()


@pytest.mark.parametrize(
    "invalid",
    [
        "column", "duplicate", "run_id", "window", "mixed_window", "naive",
        "negative", "infinite", "missing_count", "fractional_count",
    ],
)
def test_invalid_comparison_fails_before_writing(tmp_path, comparison, invalid):
    if invalid == "column":
        comparison = comparison.drop(columns="rmse")
    elif invalid == "duplicate":
        comparison = pd.concat([comparison, comparison.iloc[:1]], ignore_index=True)
    elif invalid == "run_id":
        comparison.loc[0, "run_id"] = "other_run"
    elif invalid == "window":
        comparison["evaluation_end"] = comparison["evaluation_start"]
    elif invalid == "mixed_window":
        comparison.loc[0, "evaluation_end"] += pd.Timedelta(days=1)
    elif invalid == "naive":
        comparison["evaluation_start"] = comparison["evaluation_start"].dt.tz_localize(
            None
        )
    elif invalid == "negative":
        comparison.loc[0, "mae"] = -1.0
    elif invalid == "infinite":
        comparison.loc[0, "rmse"] = np.inf
    elif invalid == "missing_count":
        comparison["retraining_count"] = np.nan
    else:
        comparison["retraining_count"] = 0.5
    figures_dir = tmp_path / "figures"
    with pytest.raises(ValueError):
        plots.plot_strategy_comparison(
            comparison, run_id=RUN_ID, figures_dir=figures_dir
        )
    assert not figures_dir.exists()


@pytest.fixture
def events():
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                ["2024-01-02T00:00:00Z", "2024-01-01T00:00:00Z"], utc=True
            ),
            "strategy": ["performance_triggered", "fixed_schedule"],
        }
    )


@pytest.mark.parametrize("empty", [False, True])
def test_retraining_events_render_strategy_lanes(
    tmp_path, events, captured_figures, empty
):
    if empty:
        events = events.iloc[:0]
    original = events.copy(deep=True)
    path = plots.plot_retraining_events(events, run_id=RUN_ID, figures_dir=tmp_path)
    assert path == tmp_path / "retraining_events" / f"{RUN_ID}.png"
    assert_png(path)
    pd.testing.assert_frame_equal(events, original)
    axes = captured_figures[0].axes[0]
    assert [label.get_text() for label in axes.get_yticklabels()] == STRATEGIES
    assert axes.get_xlabel() == "Retraining timestamp (UTC)"
    if empty:
        assert not axes.collections
        assert any("No retraining events" in text.get_text() for text in axes.texts)
    else:
        assert len(axes.collections) == 2
        for position, collection in enumerate(axes.collections, start=1):
            history = events.loc[events["strategy"] == STRATEGIES[position]]
            offsets = collection.get_offsets()
            np.testing.assert_equal(offsets[:, 1], [position])
            np.testing.assert_equal(
                offsets[:, 0], mdates.date2num(history["timestamp"].to_numpy())
            )


@pytest.mark.parametrize("invalid", ["column", "duplicate", "strategy", "timestamp"])
def test_invalid_events_fail_before_writing(tmp_path, events, invalid):
    if invalid == "column":
        events = events.drop(columns="timestamp")
    elif invalid == "duplicate":
        events = pd.concat([events, events.iloc[:1]], ignore_index=True)
    elif invalid == "strategy":
        events.loc[0, "strategy"] = "unknown"
    else:
        events["timestamp"] = "invalid"
    figures_dir = tmp_path / "figures"
    with pytest.raises(ValueError):
        plots.plot_retraining_events(events, run_id=RUN_ID, figures_dir=figures_dir)
    assert not figures_dir.exists()


def test_same_timestamp_events_have_an_hourly_not_multiyear_axis(
    tmp_path, events, captured_figures
):
    events["timestamp"] = pd.Timestamp("2024-01-01T02:00:00Z")
    plots.plot_retraining_events(events, run_id=RUN_ID, figures_dir=tmp_path)
    lower, upper = captured_figures[0].axes[0].get_xlim()
    timestamp = mdates.date2num(events["timestamp"].iloc[0])
    assert lower < timestamp < upper
    assert upper - lower < 1.0


@pytest.mark.parametrize("scenario", ["normal", "no_history", "empty"])
def test_rolling_rmse_plots_stored_values_and_history_gaps(
    tmp_path, forecasts, captured_figures, scenario
):
    monitoring = forecasts[["timestamp", "strategy"]].copy()
    monitoring["rolling_rmse"] = [np.nan, 12.0, 37.0, 4.0] * 3
    if scenario == "no_history":
        monitoring["rolling_rmse"] = pd.NA
    elif scenario == "empty":
        monitoring = monitoring.iloc[:0]
    original = monitoring.copy(deep=True)
    path = plots.plot_rolling_rmse(
        monitoring, run_id=RUN_ID, figures_dir=tmp_path
    )
    assert path == tmp_path / "rolling_rmse" / f"{RUN_ID}.png"
    assert_png(path)
    pd.testing.assert_frame_equal(monitoring, original)
    axes = captured_figures[0].axes[0]
    assert axes.get_ylabel() == "Rolling RMSE (EUR/MWh)"
    assert axes.get_xlabel() == "Decision timestamp (UTC)"
    if scenario == "empty":
        assert any("No rolling RMSE" in text.get_text() for text in axes.texts)
    else:
        assert len(axes.lines) == 3
        for line in axes.lines:
            assert pd.DatetimeIndex(line.get_xdata()).is_monotonic_increasing
            expected = (
                [np.nan] * 4 if scenario == "no_history"
                else [4.0, 37.0, 12.0, np.nan]
            )
            np.testing.assert_equal(line.get_ydata(), expected)
        if scenario == "no_history":
            assert any("Insufficient history" in text.get_text() for text in axes.texts)


@pytest.mark.parametrize("invalid", ["column", "negative", "infinite"])
def test_invalid_rolling_rmse_fails_before_writing(tmp_path, forecasts, invalid):
    monitoring = forecasts[["timestamp", "strategy"]].copy()
    monitoring["rolling_rmse"] = 1.0
    if invalid == "column":
        monitoring = monitoring.drop(columns="rolling_rmse")
    else:
        monitoring.loc[0, "rolling_rmse"] = -1.0 if invalid == "negative" else np.inf
    figures_dir = tmp_path / "figures"
    with pytest.raises(ValueError, match="rolling_rmse"):
        plots.plot_rolling_rmse(
            monitoring, run_id=RUN_ID, figures_dir=figures_dir
        )
    assert not figures_dir.exists()