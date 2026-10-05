"""Report comparison exports from small persisted forecast and event fixtures."""

import numpy as np
import pandas as pd
import pytest

from energy_trading_pipeline.backtesting.forecast_log import (
    read_forecast_log,
    write_forecast_log,
)
from energy_trading_pipeline.evaluation.strategy_comparison import (
    build_strategy_comparison,
    write_strategy_comparison,
)
from energy_trading_pipeline.retraining.events import write_retraining_events


START = pd.Timestamp("2024-01-01T00:00:00Z")
END = pd.Timestamp("2024-01-03T00:00:00Z")
RUN_ID = "run_20241005_120000"
COMPARISON_COLUMNS = [
    "run_id",
    "evaluation_start",
    "evaluation_end",
    "strategy",
    "rmse",
    "mae",
    "retraining_count",
    "retraining_frequency",
]


@pytest.fixture
def fixture_logs(tmp_path):
    timestamps = pd.date_range(START, periods=4, freq="12h")
    actuals = [-2.0, np.nan, 2.0, 3.0]
    predictions = {
        "no_retraining": [-1.0, 100.0, 0.0, 5.0],
        "fixed_schedule": [-2.0, 100.0, 1.0, 2.0],
        "performance_triggered": [-2.0, 100.0, 2.0, 3.0],
    }
    forecasts = pd.DataFrame(
        [
            {
                "timestamp": timestamp,
                "forecast_timestamp": timestamp - pd.Timedelta(days=1),
                "prediction": prediction,
                "actual": actual,
                "strategy": strategy,
                "model_version": "fixture_model",
            }
            for strategy, values in predictions.items()
            for timestamp, prediction, actual in zip(timestamps, values, actuals)
        ]
    )
    events = pd.DataFrame(
        [
            {
                "timestamp": timestamp,
                "strategy": strategy,
                "trigger_reason": reason,
                "threshold": threshold,
                "rolling_rmse": rolling_rmse,
                "training_window_start": timestamp - pd.Timedelta(days=10),
                "training_window_end": timestamp,
                "model_version": f"retrained_{index}",
            }
            for index, (timestamp, strategy, reason, threshold, rolling_rmse)
            in enumerate(
                [
                    (START, "fixed_schedule", "scheduled", np.nan, np.nan),
                    (
                        START + pd.Timedelta(days=1),
                        "fixed_schedule", "scheduled", np.nan, np.nan,
                    ),
                    (
                        START + pd.Timedelta(hours=12),
                        "performance_triggered", "rmse_threshold_exceeded", 1.0, 2.0,
                    ),
                    (END, "fixed_schedule", "scheduled", np.nan, np.nan),
                ]
            )
        ]
    )
    input_dir = tmp_path / "logs" / "runs" / RUN_ID
    forecast_path = write_forecast_log(forecasts, input_dir / "forecasts.parquet")
    event_path = write_retraining_events(
        events, input_dir / "retraining_events.parquet"
    )
    return read_forecast_log(forecast_path), pd.read_parquet(event_path)


def export(forecasts, events, tables_dir, run_id=RUN_ID):
    return write_strategy_comparison(
        forecasts,
        events,
        run_id=run_id,
        evaluation_start=START.tz_convert("Europe/Berlin"),
        evaluation_end=END.tz_convert("Europe/Berlin"),
        tables_dir=tables_dir,
    )


@pytest.mark.parametrize("scenario", ["normal", "no_events", "no_actuals", "empty"])
def test_fixture_log_comparison_export_round_trip(tmp_path, fixture_logs, scenario):
    forecasts, events = fixture_logs
    if scenario in {"no_events", "empty"}:
        events = events.iloc[:0]
    if scenario == "empty":
        forecasts = forecasts.iloc[:0]
    if scenario == "no_actuals":
        forecasts["actual"] = np.nan
    original_forecasts = forecasts.copy(deep=True)
    original_events = events.copy(deep=True)
    tables_dir = tmp_path / "reports" / "tables"
    paths = export(forecasts, events, tables_dir)
    assert paths == {
        "parquet": tables_dir / RUN_ID / "strategy_comparison.parquet",
        "csv": tables_dir / RUN_ID / "strategy_comparison.csv",
    }
    expected = build_strategy_comparison(
        forecasts, events, run_id=RUN_ID, evaluation_start=START, evaluation_end=END
    )
    saved = pd.read_parquet(paths["parquet"])
    assert list(saved.columns) == COMPARISON_COLUMNS
    pd.testing.assert_frame_equal(saved, expected)
    csv = pd.read_csv(
        paths["csv"],
        dtype={"run_id": "string", "strategy": "string"},
        float_precision="round_trip",
    )
    for column in ("evaluation_start", "evaluation_end"):
        csv[column] = pd.to_datetime(csv[column], utc=True).astype(
            "datetime64[ns, UTC]"
        )
    csv = csv.astype(expected.dtypes.to_dict())
    pd.testing.assert_frame_equal(csv, expected)
    pd.testing.assert_frame_equal(forecasts, original_forecasts)
    pd.testing.assert_frame_equal(events, original_events)
    if scenario == "normal":
        rows = saved.set_index("strategy")
        assert rows.loc["no_retraining", "rmse"] == pytest.approx(np.sqrt(3))
        assert rows.loc["no_retraining", "mae"] == pytest.approx(5 / 3)
        assert rows.loc["fixed_schedule", "rmse"] == pytest.approx(np.sqrt(2 / 3))
        assert rows.loc["fixed_schedule", "mae"] == pytest.approx(2 / 3)
        assert rows.loc["performance_triggered", "rmse"] == 0.0
        assert rows.loc["performance_triggered", "mae"] == 0.0
        assert rows["retraining_count"].to_dict() == {
            "fixed_schedule": 2, "no_retraining": 0, "performance_triggered": 1
        }
        assert rows["retraining_frequency"].to_dict() == {
            "fixed_schedule": 1.0, "no_retraining": 0.0, "performance_triggered": 0.5
        }


def test_exports_isolate_runs_and_replace_only_the_current_run(tmp_path, fixture_logs):
    forecasts, events = fixture_logs
    tables_dir = tmp_path / "reports" / "tables"
    first = export(forecasts, events, tables_dir)
    original = pd.read_parquet(first["parquet"])
    second = export(forecasts, events, tables_dir, "run_20241005_130000")
    export(forecasts, events.iloc[:0], tables_dir, "run_20241005_130000")
    pd.testing.assert_frame_equal(pd.read_parquet(first["parquet"]), original)
    replaced = pd.read_parquet(second["parquet"])
    assert (replaced["run_id"] == "run_20241005_130000").all()
    assert (replaced["retraining_count"] == 0).all()
    assert len(list(tables_dir.glob("*/*"))) == 4


@pytest.mark.parametrize("invalid", ["run_id", "forecasts", "events", "window"])
def test_invalid_export_inputs_create_no_output_directory(
    tmp_path, fixture_logs, invalid
):
    forecasts, events = fixture_logs
    kwargs = {
        "run_id": RUN_ID,
        "evaluation_start": START,
        "evaluation_end": END,
        "tables_dir": tmp_path / "reports" / "tables",
    }
    if invalid == "run_id":
        kwargs["run_id"] = "../outside"
    elif invalid == "forecasts":
        forecasts = forecasts.drop(columns="prediction")
    elif invalid == "events":
        events = events.drop(columns="model_version")
    else:
        kwargs["evaluation_end"] = START
    with pytest.raises(ValueError):
        write_strategy_comparison(forecasts, events, **kwargs)
    assert not kwargs["tables_dir"].exists()