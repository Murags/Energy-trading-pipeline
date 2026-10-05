"""Fixture-sized orchestration and issuance-time leakage checks."""

import numpy as np
import pandas as pd
import pytest

from energy_trading_pipeline.backtesting.backtest_runner import run_backtest
from energy_trading_pipeline.backtesting.forecast_log import (
    FORECAST_LOG_COLUMNS,
    read_forecast_log,
)
from energy_trading_pipeline.models.xgboost_model import XGBoostSpreadModel
from energy_trading_pipeline.retraining.no_retraining import NoRetrainingPolicy


@pytest.fixture
def runner_inputs(tmp_path):
    timestamps = pd.date_range("2024-01-01", periods=96, freq="h", tz="UTC")
    frame = pd.DataFrame(
        {
            "timestamp": timestamps,
            "spread": np.sin(np.arange(96)),
            "hour": timestamps.hour,
            # Calendar features are known in advance; actuals arrive after delivery.
            "feature_available_at": timestamps - pd.Timedelta(days=1),
            "actual_available_at": timestamps + pd.Timedelta(hours=2),
        }
    )
    config = {
        "backtest": {
            "evaluation_start_date": "2024-01-03",
            "evaluation_end_date": "2024-01-04",
            "train_window_days": 1,
            "validation_window_days": 1,
            "forecast_horizon_hours": 24,
        },
        "model": {"params": {"n_estimators": 3, "max_depth": 2, "n_jobs": 1}},
    }
    kwargs = {
        "feature_columns": ["hour"],
        "model_version": "model_20240103_000000",
        "model_output_path": tmp_path / "models" / "model.json",
        "forecast_path": tmp_path / "logs" / "forecasts.parquet",
    }
    return frame, config, kwargs


def test_static_runner_trains_once_and_round_trips(runner_inputs, monkeypatch):
    frame, config, kwargs = runner_inputs
    original = frame.copy(deep=True)
    fit = XGBoostSpreadModel.fit
    fitted_rows = []

    def spy_fit(self, features, target):
        fitted_rows.append(target.copy())
        return fit(self, features, target)

    monkeypatch.setattr(XGBoostSpreadModel, "fit", spy_fit)
    decisions = []

    def policy(timestamp, history):
        decisions.append((timestamp, history.copy()))
        history.loc[:, "actual"] = 999  # Hook gets an isolated snapshot.
        return False

    result = run_backtest(
        frame.sample(frac=1, random_state=4), config, policy_hook=policy, **kwargs
    )
    assert len(fitted_rows) == 1
    np.testing.assert_allclose(fitted_rows[0], frame["spread"].iloc[:24])
    assert list(result.columns) == list(FORECAST_LOG_COLUMNS)
    assert len(result) == 48
    assert result["timestamp"].is_monotonic_increasing
    assert result["model_version"].unique().tolist() == [kwargs["model_version"]]
    assert result["strategy"].unique().tolist() == ["no_retraining"]
    np.testing.assert_allclose(result["actual"], frame["spread"].iloc[48:])
    np.testing.assert_allclose(result["error"], result["actual"] - result["prediction"])
    assert decisions[0][1].empty
    assert len(decisions[1][1]) == 23  # Last actual is still unavailable.
    assert (decisions[1][1]["timestamp"] < decisions[1][0]).all()
    pd.testing.assert_frame_equal(read_forecast_log(kwargs["forecast_path"]), result)
    pd.testing.assert_frame_equal(frame, original)


def test_no_retraining_policy_drives_the_runner(runner_inputs, monkeypatch):
    frame, config, kwargs = runner_inputs
    fit = XGBoostSpreadModel.fit
    fit_calls = []

    def spy_fit(self, features, target):
        fit_calls.append(len(target))
        return fit(self, features, target)

    monkeypatch.setattr(XGBoostSpreadModel, "fit", spy_fit)
    policy = NoRetrainingPolicy()

    result = run_backtest(frame, config, policy_hook=policy.as_policy_hook(), **kwargs)
    assert len(fit_calls) == 1
    assert result["strategy"].unique().tolist() == [policy.strategy]
    assert result["model_version"].unique().tolist() == [kwargs["model_version"]]


def test_loaded_baseline_matches_without_fitting(runner_inputs, monkeypatch):
    frame, config, kwargs = runner_inputs
    expected = run_backtest(frame, config, **kwargs)

    def unexpected_fit(*args, **kwargs):
        pytest.fail("Loaded static model must not be refitted")

    monkeypatch.setattr(XGBoostSpreadModel, "fit", unexpected_fit)
    kwargs["initial_model_path"] = kwargs.pop("model_output_path")
    kwargs["initial_model_history_end"] = pd.Timestamp("2024-01-02", tz="UTC")
    actual = run_backtest(frame, config, **kwargs)
    pd.testing.assert_frame_equal(actual, expected)


@pytest.mark.parametrize("fault", ["late_feature", "late_label", "duplicate", "gap"])
def test_invalid_data_fails_before_artifacts(runner_inputs, fault):
    frame, config, kwargs = runner_inputs
    if fault == "late_feature":
        frame.loc[49, "feature_available_at"] = frame.loc[49, "timestamp"]
        message = "features.*issuance"
    elif fault == "late_label":
        frame.loc[0, "actual_available_at"] = frame.loc[50, "timestamp"]
        message = "training actuals.*issuance"
    elif fault == "duplicate":
        frame.loc[1, "timestamp"] = frame.loc[0, "timestamp"]
        message = "duplicate"
    else:
        frame = frame.drop(index=60)
        message = "hourly coverage"
    with pytest.raises(ValueError, match=message):
        run_backtest(frame, config, **kwargs)
    assert not kwargs["forecast_path"].exists()
    assert not kwargs["model_output_path"].exists()


def test_future_actual_changes_cannot_change_predictions(runner_inputs):
    frame, config, kwargs = runner_inputs
    expected = run_backtest(frame, config, **kwargs)
    frame.loc[48:, "spread"] += 1000
    actual = run_backtest(frame, config, **kwargs)
    np.testing.assert_array_equal(actual["prediction"], expected["prediction"])


def test_positive_hook_is_not_silently_ignored(runner_inputs):
    frame, config, kwargs = runner_inputs
    with pytest.raises(NotImplementedError, match="Epic 7"):
        run_backtest(frame, config, policy_hook=lambda timestamp, history: True, **kwargs)


def test_loaded_model_requires_pre_evaluation_provenance(runner_inputs):
    frame, config, kwargs = runner_inputs
    run_backtest(frame, config, **kwargs)
    kwargs["initial_model_path"] = kwargs.pop("model_output_path")
    with pytest.raises(ValueError, match="history_end"):
        run_backtest(frame, config, **kwargs)
    kwargs["initial_model_history_end"] = pd.Timestamp("2024-01-03", tz="UTC")
    with pytest.raises(ValueError, match="history_end"):
        run_backtest(frame, config, **kwargs)


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("timestamp", "2024-01-01", "timezone-aware"),
        ("feature_available_at", None, "timezone-aware"),
        ("actual_available_at", None, "timezone-aware"),
        ("spread", np.inf, "finite numeric"),
    ],
)
def test_invalid_training_inputs(runner_inputs, column, value, message):
    frame, config, kwargs = runner_inputs
    frame[column] = frame[column].astype(object)
    frame.loc[0, column] = value
    with pytest.raises(ValueError, match=message):
        run_backtest(frame, config, **kwargs)


def test_missing_evaluation_actuals_remain_missing(runner_inputs):
    frame, config, kwargs = runner_inputs
    frame.loc[48, "spread"] = np.nan
    result = run_backtest(frame, config, **kwargs)
    assert result.loc[0, ["actual", "error", "squared_error", "absolute_error"]].isna().all()
    assert np.isfinite(result.loc[0, "prediction"])


def test_loaded_model_contract_mismatch_fails(runner_inputs):
    frame, config, kwargs = runner_inputs
    run_backtest(frame, config, **kwargs)
    kwargs["initial_model_path"] = kwargs.pop("model_output_path")
    kwargs["initial_model_history_end"] = pd.Timestamp("2024-01-02", tz="UTC")
    config["model"]["params"]["max_depth"] = 4
    with pytest.raises(ValueError, match="does not match"):
        run_backtest(frame, config, **kwargs)
