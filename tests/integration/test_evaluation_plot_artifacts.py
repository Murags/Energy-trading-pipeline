"""Render report figures from small persisted evaluation artifacts, offline."""

import matplotlib.image as mpimg
import numpy as np
import pandas as pd
import pytest

from energy_trading_pipeline.backtesting.forecast_log import build_forecast_log
from energy_trading_pipeline.evaluation.plots import (
    plot_forecasts_vs_actuals,
    plot_retraining_events,
    plot_rolling_rmse,
    plot_strategy_comparison,
)
from energy_trading_pipeline.evaluation.strategy_comparison import (
    write_strategy_comparison,
)
from energy_trading_pipeline.retraining.events import build_retraining_events


RUN_ID = "run_20261005_120000"
START = pd.Timestamp("2024-01-01T00:00:00Z")
END = START + pd.Timedelta(hours=4)
PLOTTERS = {
    "forecasts_vs_actuals": plot_forecasts_vs_actuals,
    "rolling_rmse": plot_rolling_rmse,
    "retraining_events": plot_retraining_events,
    "strategy_comparison": plot_strategy_comparison,
}


@pytest.fixture
def exported_artifacts(tmp_path, scenario, file_format):
    timestamps = pd.date_range(START, periods=4, freq="h")
    strategies = ["no_retraining", "fixed_schedule", "performance_triggered"]
    forecasts = pd.DataFrame(
        [
            {
                "timestamp": timestamp,
                "forecast_timestamp": timestamp - pd.Timedelta(days=1),
                "prediction": float(position + offset),
                "actual": float(position),
                "strategy": strategy,
                "model_version": "fixture_model",
            }
            for offset, strategy in enumerate(strategies)
            for position, timestamp in enumerate(timestamps)
        ]
    )
    events = pd.DataFrame(
        [
            {
                "timestamp": timestamps[2],
                "strategy": strategy,
                "trigger_reason": reason,
                "threshold": threshold,
                "rolling_rmse": rolling_rmse,
                "training_window_start": START - pd.Timedelta(days=10),
                "training_window_end": timestamps[2],
                "model_version": f"retrained_{strategy}",
            }
            for strategy, reason, threshold, rolling_rmse in [
                ("fixed_schedule", "scheduled", np.nan, np.nan),
                ("performance_triggered", "rmse_threshold_exceeded", 1.0, 2.0),
            ]
        ]
    )
    monitoring = forecasts[["timestamp", "strategy"]].copy()
    monitoring["rolling_rmse"] = [np.nan, np.nan, 2.0, 1.0] * 3
    if scenario in {"empty", "no_events"}:
        events = events.iloc[:0]
    if scenario == "empty":
        forecasts = forecasts.iloc[:0]
        monitoring = monitoring.iloc[:0]
    elif scenario == "no_scores":
        forecasts["actual"] = pd.NA
        monitoring["rolling_rmse"] = pd.NA
    forecasts = build_forecast_log(forecasts)
    events = build_retraining_events(events)
    table_paths = write_strategy_comparison(
        forecasts, events, run_id=RUN_ID,
        evaluation_start=START, evaluation_end=END,
        tables_dir=tmp_path / "reports" / "tables",
    )
    inputs_dir = tmp_path / "logs" / "runs" / RUN_ID
    inputs_dir.mkdir(parents=True)
    paths = {"strategy_comparison": table_paths[file_format]}
    for name, frame in [
        ("forecasts_vs_actuals", forecasts),
        ("rolling_rmse", monitoring),
        ("retraining_events", events),
    ]:
        path = inputs_dir / f"{name}.{file_format}"
        if file_format == "parquet":
            frame.to_parquet(path, index=False)
        else:
            frame.to_csv(path, index=False)
        paths[name] = path
    return paths


@pytest.mark.parametrize("file_format", ["parquet", "csv"])
@pytest.mark.parametrize("scenario", ["normal", "no_events", "no_scores", "empty"])
def test_exported_artifacts_generate_all_four_report_figures(
    tmp_path, exported_artifacts, file_format, scenario
):
    figures_dir = tmp_path / "reports" / "figures"
    originals = {name: path.read_bytes() for name, path in exported_artifacts.items()}
    for name, input_path in exported_artifacts.items():
        data = (
            pd.read_parquet(input_path) if file_format == "parquet"
            else pd.read_csv(input_path)
        )
        original = data.copy(deep=True)
        path = PLOTTERS[name](data, run_id=RUN_ID, figures_dir=figures_dir)
        assert path == figures_dir / name / f"{RUN_ID}.png"
        assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        pixels = mpimg.imread(path)
        assert pixels.shape[0] >= 600 and pixels.shape[1] >= 1000
        assert np.ptp(pixels) > 0.5
        pd.testing.assert_frame_equal(data, original)
        assert input_path.read_bytes() == originals[name]
        first_bytes = path.read_bytes()
        other_run = "run_20261005_130000"
        if "run_id" in data:
            data["run_id"] = other_run
        second = PLOTTERS[name](data, run_id=other_run, figures_dir=figures_dir)
        assert second != path and second.is_file()
        assert path.read_bytes() == first_bytes
        PLOTTERS[name](data, run_id=other_run, figures_dir=figures_dir)
        assert path.read_bytes() == first_bytes
    assert len(list(figures_dir.glob("*/*.png"))) == 8