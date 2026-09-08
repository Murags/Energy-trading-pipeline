"""XGBoost regression wrapper: config-driven fit, predict, save, and load."""

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import xgboost as xgb

from energy_trading_pipeline.config.loader import load_config
from energy_trading_pipeline.models.xgboost_model import (
    MODEL_ARTIFACT_SUFFIX,
    MODEL_TYPE,
    TARGET_COLUMN,
    XGBoostSpreadModel,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HOURS = 48
# The wrapper is model-family logic, not feature logic, so the fixture mimics
# the shape of a feature dataset row rather than reusing the real builders.
FEATURE_COLUMNS = ["spread_lag_1", "spread_rolling_mean_3", "hour"]
MODEL_CONFIG = {
    "type": "xgboost",
    "target_column": "spread",
    "params": {
        "n_estimators": 8,
        "max_depth": 2,
        "learning_rate": 0.1,
        "random_state": 42,
        "objective": "reg:squarederror",
    },
}


@pytest.fixture
def features():
    """Tiny feature matrix with the canonical snake_case feature columns."""
    return pd.DataFrame(
        {
            "spread_lag_1": [10.0 + 0.5 * index for index in range(HOURS)],
            "spread_rolling_mean_3": [9.0 + 0.5 * index for index in range(HOURS)],
            "hour": [index % 24 for index in range(HOURS)],
        }
    )


@pytest.fixture
def target():
    """Numeric spread target aligned to the feature fixture."""
    return pd.Series(
        [10.5 + 0.5 * index for index in range(HOURS)], name=TARGET_COLUMN
    )


@pytest.fixture
def fitted_model(features, target):
    """Wrapper built from config and fitted on the tiny fixture."""
    return XGBoostSpreadModel.from_config(MODEL_CONFIG).fit(features, target)


def test_from_config_accepts_model_parameters_from_config():
    model = XGBoostSpreadModel.from_config(MODEL_CONFIG)

    assert model.params == MODEL_CONFIG["params"]
    assert model.target_column == "spread"
    assert model.is_fitted is False


def test_configured_parameters_reach_the_underlying_regressor():
    model = XGBoostSpreadModel.from_config(MODEL_CONFIG)

    regressor_params = model.regressor.get_params()

    for name, value in MODEL_CONFIG["params"].items():
        assert regressor_params[name] == value


def test_shipped_config_params_reach_the_wrapper():
    config = load_config(
        PROJECT_ROOT / "configs" / "experiment.yaml",
        model_params_config_path=PROJECT_ROOT / "configs" / "model_params.yaml",
        base_dir=PROJECT_ROOT,
    )

    model = XGBoostSpreadModel.from_config(config["model"])

    # Pins the acceptance criterion that parameters come from config rather than
    # from defaults hidden in the wrapper.
    assert model.params == config["model"]["params"]
    assert model.params["random_state"] == 42
    assert model.target_column == config["model"]["target_column"]


def test_shipped_config_params_train_and_predict_on_the_fixture(features, target):
    config = load_config(
        PROJECT_ROOT / "configs" / "experiment.yaml",
        model_params_config_path=PROJECT_ROOT / "configs" / "model_params.yaml",
        base_dir=PROJECT_ROOT,
    )

    model = XGBoostSpreadModel.from_config(config["model"]).fit(features, target)

    assert model.predict(features).shape == (HOURS,)


def test_feature_columns_are_unknown_before_fit():
    assert XGBoostSpreadModel.from_config(MODEL_CONFIG).feature_columns is None


def test_from_config_defaults_target_column_to_spread():
    model = XGBoostSpreadModel.from_config({"type": "xgboost", "params": {}})

    assert model.target_column == TARGET_COLUMN


def test_from_config_without_params_uses_xgboost_defaults():
    model = XGBoostSpreadModel.from_config({"type": "xgboost"})

    assert model.params == {}


def test_from_config_rejects_a_non_mapping_model_section():
    with pytest.raises(ValueError, match="model"):
        XGBoostSpreadModel.from_config(["xgboost"])


def test_from_config_warns_on_unrecognized_model_config_keys(caplog):
    with caplog.at_level(logging.WARNING):
        XGBoostSpreadModel.from_config({**MODEL_CONFIG, "targt_column": "spread"})

    assert "targt_column" in caplog.text


def test_from_config_rejects_a_non_mapping_params_section():
    with pytest.raises(ValueError, match="params"):
        XGBoostSpreadModel.from_config({"type": "xgboost", "params": ["max_depth"]})


def test_unknown_model_parameters_fail_instead_of_warning_at_fit_time():
    with pytest.raises(ValueError, match="max_dept"):
        XGBoostSpreadModel({"max_dept": 4})


def test_fit_returns_the_wrapper_and_records_the_feature_contract(
    features, target
):
    model = XGBoostSpreadModel.from_config(MODEL_CONFIG)

    result = model.fit(features, target)

    assert result is model
    assert model.is_fitted is True
    assert model.feature_columns == FEATURE_COLUMNS


def test_predict_returns_numeric_spread_values(fitted_model, features):
    predictions = fitted_model.predict(features)

    assert isinstance(predictions, np.ndarray)
    assert predictions.shape == (HOURS,)
    assert predictions.dtype == np.float64
    assert np.isfinite(predictions).all()


def test_predictions_track_the_spread_target_on_the_fixture(
    fitted_model, features, target
):
    predictions = fitted_model.predict(features)

    # A monotone target on 48 rows is easy to fit; this guards against a
    # wrapper that trains on the wrong column or returns a constant.
    assert np.corrcoef(predictions, target.to_numpy())[0, 1] > 0.9


def test_predict_selects_feature_columns_in_the_recorded_training_order(
    fitted_model, features
):
    reordered = features[FEATURE_COLUMNS[::-1]]

    np.testing.assert_allclose(
        fitted_model.predict(reordered), fitted_model.predict(features)
    )


def test_predict_ignores_non_feature_columns_carried_by_the_dataset(
    fitted_model, features, target
):
    with_extras = features.assign(
        timestamp=pd.date_range("2023-01-01", periods=HOURS, freq="h", tz="UTC"),
        spread=target,
    )

    np.testing.assert_allclose(
        fitted_model.predict(with_extras), fitted_model.predict(features)
    )


def test_predict_fails_clearly_when_a_trained_feature_column_is_missing(
    fitted_model, features
):
    with pytest.raises(ValueError, match="spread_rolling_mean_3"):
        fitted_model.predict(features.drop(columns=["spread_rolling_mean_3"]))


def test_predict_before_fit_fails_clearly(features):
    model = XGBoostSpreadModel.from_config(MODEL_CONFIG)

    with pytest.raises(ValueError, match="not fitted"):
        model.predict(features)


def test_fit_rejects_features_holding_the_target_column(features, target):
    model = XGBoostSpreadModel.from_config(MODEL_CONFIG)

    with pytest.raises(ValueError, match=TARGET_COLUMN):
        model.fit(features.assign(spread=target), target)


def test_fit_rejects_features_holding_the_timestamp_column(features, target):
    model = XGBoostSpreadModel.from_config(MODEL_CONFIG)

    with pytest.raises(ValueError, match="timestamp"):
        model.fit(
            features.assign(
                timestamp=pd.date_range(
                    "2023-01-01", periods=HOURS, freq="h", tz="UTC"
                )
            ),
            target,
        )


def test_fit_rejects_a_target_of_a_different_length(features, target):
    model = XGBoostSpreadModel.from_config(MODEL_CONFIG)

    with pytest.raises(ValueError, match="length"):
        model.fit(features, target.iloc[:-1])


def test_fit_rejects_an_empty_feature_matrix(target):
    model = XGBoostSpreadModel.from_config(MODEL_CONFIG)

    with pytest.raises(ValueError, match="empty"):
        model.fit(pd.DataFrame(columns=FEATURE_COLUMNS), target.iloc[:0])


def test_fit_rejects_a_feature_matrix_without_columns(target):
    model = XGBoostSpreadModel.from_config(MODEL_CONFIG)

    with pytest.raises(ValueError, match="feature column"):
        model.fit(pd.DataFrame(index=range(HOURS)), target)


def test_fit_does_not_mutate_the_input_frames(features, target):
    features_before = features.copy()
    target_before = target.copy()

    XGBoostSpreadModel.from_config(MODEL_CONFIG).fit(features, target)

    pd.testing.assert_frame_equal(features, features_before)
    pd.testing.assert_series_equal(target, target_before)


def test_fit_is_deterministic_for_a_seeded_configuration(features, target):
    first = XGBoostSpreadModel.from_config(MODEL_CONFIG).fit(features, target)
    second = XGBoostSpreadModel.from_config(MODEL_CONFIG).fit(features, target)

    np.testing.assert_array_equal(first.predict(features), second.predict(features))


def test_save_writes_the_model_artifact(fitted_model, tmp_path):
    output_path = tmp_path / "artifacts" / "model_20230101_000000" / "model.json"

    result = fitted_model.save(output_path)

    assert result == output_path
    assert output_path.is_file()
    assert json.loads(output_path.read_text(encoding="utf-8"))


def test_save_before_fit_fails_clearly(tmp_path):
    model = XGBoostSpreadModel.from_config(MODEL_CONFIG)

    with pytest.raises(ValueError, match="not fitted"):
        model.save(tmp_path / "model.json")


def test_save_requires_the_json_artifact_suffix(fitted_model, tmp_path):
    with pytest.raises(ValueError, match=MODEL_ARTIFACT_SUFFIX):
        fitted_model.save(tmp_path / "model.parquet")


def test_load_restores_a_model_that_predicts_identically(
    fitted_model, features, tmp_path
):
    output_path = fitted_model.save(tmp_path / "model.json")

    loaded = XGBoostSpreadModel.load(output_path)

    assert loaded.is_fitted is True
    np.testing.assert_array_equal(
        loaded.predict(features), fitted_model.predict(features)
    )


def test_load_restores_the_parameters_and_feature_contract(
    fitted_model, tmp_path
):
    output_path = fitted_model.save(tmp_path / "model.json")

    loaded = XGBoostSpreadModel.load(output_path)

    assert loaded.params == MODEL_CONFIG["params"]
    assert loaded.feature_columns == FEATURE_COLUMNS
    assert loaded.target_column == "spread"


def test_a_loaded_model_can_be_refitted_with_its_recorded_parameters(
    fitted_model, features, target, tmp_path
):
    loaded = XGBoostSpreadModel.load(fitted_model.save(tmp_path / "model.json"))

    refitted = loaded.fit(features, target)

    np.testing.assert_array_equal(
        refitted.predict(features), fitted_model.predict(features)
    )


def test_load_enforces_the_recorded_feature_contract(fitted_model, tmp_path):
    loaded = XGBoostSpreadModel.load(fitted_model.save(tmp_path / "model.json"))

    with pytest.raises(ValueError, match="hour"):
        loaded.predict(pd.DataFrame({"spread_lag_1": [1.0], "unrelated": [2.0]}))


def test_load_fails_clearly_when_the_artifact_is_missing(tmp_path):
    with pytest.raises(FileNotFoundError, match="model.json"):
        XGBoostSpreadModel.load(tmp_path / "model.json")


def test_save_and_load_round_trip_is_byte_identical(fitted_model, tmp_path):
    first_path = fitted_model.save(tmp_path / "first" / "model.json")
    second_path = XGBoostSpreadModel.load(first_path).save(
        tmp_path / "second" / "model.json"
    )

    assert first_path.read_bytes() == second_path.read_bytes()


def test_wrapper_reports_the_single_supported_model_family():
    assert MODEL_TYPE == "xgboost"
    assert XGBoostSpreadModel.from_config(MODEL_CONFIG).model_type == MODEL_TYPE


def test_from_config_rejects_an_alternate_model_family():
    with pytest.raises(ValueError, match="lightgbm"):
        XGBoostSpreadModel.from_config({**MODEL_CONFIG, "type": "lightgbm"})


def test_load_rejects_an_artifact_from_an_alternate_model_family(
    features, target, tmp_path
):
    classifier_path = tmp_path / "model.json"
    classifier = xgb.XGBClassifier(n_estimators=4, max_depth=2, random_state=42)
    classifier.fit(features, (target > target.median()).astype(int))
    classifier.save_model(classifier_path)

    with pytest.raises(ValueError, match="not a"):
        XGBoostSpreadModel.load(classifier_path)


def test_the_wrapper_uses_xgboost_regression_only(fitted_model):
    assert isinstance(fitted_model.regressor, xgb.XGBRegressor)
    assert fitted_model.regressor.get_params()["objective"] == "reg:squarederror"
