"""XGBoost regression wrapper for spread forecasting."""

from collections.abc import Mapping
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb


logger = logging.getLogger(__name__)

# XGBoost is the only forecasting model in this project, so the wrapper accepts
# exactly this `model.type` and refuses to load a non-regression artifact.
MODEL_TYPE = "xgboost"
TARGET_COLUMN = "spread"
MODEL_ARTIFACT_SUFFIX = ".json"
KNOWN_MODEL_CONFIG_KEYS: tuple[str, ...] = ("type", "target_column", "params")
# The target at the prediction timestamp and the timestamp itself are never
# predictors. A feature dataset carries both, so passing the frame straight to
# `fit` is an easy mistake and fails here rather than training on the target.
RESERVED_FEATURE_COLUMNS: tuple[str, ...] = ("timestamp",)
# Booster attributes travel inside `model.json`, so one file restores the
# parameters and feature contract without a competing metadata artifact.
PARAMS_ATTRIBUTE = "model_params"
FEATURE_COLUMNS_ATTRIBUTE = "feature_columns"
TARGET_COLUMN_ATTRIBUTE = "target_column"
MODEL_TYPE_ATTRIBUTE = "model_type"


class XGBoostSpreadModel:
    """One consistent fit, predict, save, and load interface over `XGBRegressor`.

    Training and prediction share this wrapper so every strategy uses the same
    model family and the same configured parameters. The wrapper records the
    feature columns it was trained on and persists them with the artifact, so a
    loaded model predicts on the same columns in the same order it saw at fit
    time regardless of how the caller happens to order its frame.

    Construct from the `model` section of the experiment config with
    `from_config`; `configs/model_params.yaml` is merged into `model.params` by
    `energy_trading_pipeline.config.loader.load_config`.
    """

    def __init__(
        self,
        params: Mapping[str, Any] | None = None,
        *,
        target_column: str = TARGET_COLUMN,
    ) -> None:
        """
        Build an unfitted wrapper around `XGBRegressor`.

        Args:
            params: XGBoost parameters. Every key must be accepted by
                `XGBRegressor`; an unrecognized key fails here rather than
                warning at fit time. Omitted parameters keep XGBoost defaults.
            target_column: Name of the numeric target the model predicts.

        Raises:
            ValueError: If `params` is not a mapping, holds a parameter
                `XGBRegressor` does not accept, or `target_column` is blank.
        """
        self._params = _validate_params(params)
        self._target_column = _validate_target_column(target_column)
        self._regressor = xgb.XGBRegressor(**self._params)
        self._feature_columns: list[str] | None = None
        self._is_fitted = False

    @classmethod
    def from_config(cls, model_config: Mapping[str, Any]) -> "XGBoostSpreadModel":
        """
        Build an unfitted wrapper from the `model` section of the config.

        Reads `params` for the XGBoost parameters and `target_column` for the
        target name, defaulting to `spread`. A `type` other than `xgboost` fails,
        because this project does not compare alternative model families.
        Unrecognized keys warn so a typo does not silently fall back to a default.

        Raises:
            ValueError: If `model_config` or its `params` is not a mapping, if
                `type` names another model family, or if the parameters are
                invalid.
        """
        if not isinstance(model_config, Mapping):
            raise ValueError(
                "model_config must be the 'model' mapping of the experiment config"
            )

        model_type = model_config.get("type", MODEL_TYPE)
        if model_type != MODEL_TYPE:
            raise ValueError(
                f"Unsupported model.type: {model_type!r}. This project forecasts "
                f"with {MODEL_TYPE!r} only and does not add model families."
            )

        unknown = sorted(set(model_config) - set(KNOWN_MODEL_CONFIG_KEYS))
        if unknown:
            logger.warning(
                "Ignoring unrecognized model config key(s): %s; supported: %s",
                unknown,
                sorted(KNOWN_MODEL_CONFIG_KEYS),
            )

        return cls(
            model_config.get("params"),
            target_column=model_config.get("target_column", TARGET_COLUMN),
        )

    @property
    def model_type(self) -> str:
        """The single supported model family identifier."""
        return MODEL_TYPE

    @property
    def params(self) -> dict[str, Any]:
        """Copy of the configured XGBoost parameters."""
        return dict(self._params)

    @property
    def target_column(self) -> str:
        """Name of the numeric target the model predicts."""
        return self._target_column

    @property
    def feature_columns(self) -> list[str] | None:
        """Feature columns recorded at fit time, or None before fitting."""
        return None if self._feature_columns is None else list(self._feature_columns)

    @property
    def is_fitted(self) -> bool:
        """Whether the wrapper holds a trained model, from `fit` or `load`."""
        return self._is_fitted

    @property
    def regressor(self) -> xgb.XGBRegressor:
        """The underlying `XGBRegressor`, exposed for inspection."""
        return self._regressor

    def fit(
        self, features: pd.DataFrame, target: pd.Series
    ) -> "XGBoostSpreadModel":
        """
        Train on aligned feature and target rows and return this wrapper.

        `features` must hold predictors only. The target column and `timestamp`
        are rejected, because at the prediction timestamp they are the target or
        the index rather than predictors. The column order of `features` becomes
        the model's feature contract for `predict`, `save`, and `load`. Neither
        input is mutated.

        Raises:
            ValueError: If `features` is not a DataFrame with at least one
                column and one row, if `target` is not a Series of the same
                length, or if `features` holds a reserved column.
        """
        features = _validate_features(features)
        self._reject_reserved_columns(features)

        if not isinstance(target, pd.Series):
            raise ValueError(
                f"target must be a pandas Series of {self._target_column} values"
            )
        if len(target) != len(features):
            raise ValueError(
                f"features and target must have the same length: got "
                f"{len(features)} feature rows and {len(target)} target values"
            )

        feature_columns = features.columns.tolist()
        self._regressor.fit(features[feature_columns], target)
        self._feature_columns = feature_columns
        self._is_fitted = True
        logger.info(
            "Model fitted: rows=%d, features=%d, target=%s",
            len(features),
            len(feature_columns),
            self._target_column,
        )
        return self

    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """
        Predict numeric target values for the supplied feature rows.

        The trained feature columns are selected in their recorded training
        order, so a caller may pass the columns in any order and may pass a
        frame that also carries `timestamp` or the target; extra columns are
        ignored. Predictions are returned as a float64 array of one value per
        input row, matching the dtype of the pipeline's target column.

        Raises:
            ValueError: If the model is not fitted, if `features` is not a
                DataFrame, or if a trained feature column is absent.
        """
        feature_columns = self._require_fitted("predict")
        if not isinstance(features, pd.DataFrame):
            raise ValueError("features must be a pandas DataFrame")

        missing = [
            column for column in feature_columns if column not in features.columns
        ]
        if missing:
            raise ValueError(f"Missing trained feature column(s): {missing}")

        predictions = self._regressor.predict(features[feature_columns])
        return np.asarray(predictions, dtype=np.float64)

    def save(self, output_path: Path) -> Path:
        """
        Write the trained model to a single `model.json` artifact and return it.

        The configured parameters, feature columns, target column, and model
        family are stored as booster attributes inside the artifact, so `load`
        restores a model that predicts on the same contract. Registry metadata is
        a separate concern and is not written here. A parent directory is created
        if needed, and an existing artifact at the path is replaced.

        Raises:
            ValueError: If the model is not fitted or `output_path` does not have
                a `.json` suffix.
        """
        feature_columns = self._require_fitted("save")
        output_path = Path(output_path)
        if output_path.suffix.lower() != MODEL_ARTIFACT_SUFFIX:
            raise ValueError(
                f"Model output_path must have a {MODEL_ARTIFACT_SUFFIX} suffix: "
                f"got {output_path.name!r}"
            )

        self._regressor.get_booster().set_attr(
            **{
                MODEL_TYPE_ATTRIBUTE: MODEL_TYPE,
                PARAMS_ATTRIBUTE: json.dumps(self._params, sort_keys=True),
                FEATURE_COLUMNS_ATTRIBUTE: json.dumps(feature_columns),
                TARGET_COLUMN_ATTRIBUTE: self._target_column,
            }
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._regressor.save_model(output_path)
        logger.info("Model artifact saved: %s", output_path)
        return output_path

    @classmethod
    def load(cls, model_path: Path) -> "XGBoostSpreadModel":
        """
        Load a saved model artifact and return a wrapper ready to predict.

        The parameters, feature columns, and target column recorded by `save` are
        restored, so a loaded model reports the configuration it was trained
        under, predicts on the same feature contract, and can be refitted with
        those same parameters.

        Raises:
            FileNotFoundError: If `model_path` is not an existing file.
            ValueError: If the artifact is not an XGBoost regression model.
        """
        model_path = Path(model_path)
        if not model_path.is_file():
            raise FileNotFoundError(f"Model artifact not found: {model_path}")

        attributes = _read_artifact_attributes(model_path)
        recorded_type = attributes.get(MODEL_TYPE_ATTRIBUTE, MODEL_TYPE)
        if recorded_type != MODEL_TYPE:
            raise ValueError(
                f"Model artifact is not a {MODEL_TYPE} model: {model_path} "
                f"records {MODEL_TYPE_ATTRIBUTE}={recorded_type!r}"
            )

        model = cls(
            _decode_params(attributes.get(PARAMS_ATTRIBUTE), model_path),
            target_column=attributes.get(TARGET_COLUMN_ATTRIBUTE, TARGET_COLUMN),
        )
        # Loading into an already configured regressor keeps the parameters,
        # which `load_model` would otherwise leave unset.
        try:
            model._regressor.load_model(model_path)
        except TypeError as exc:
            # XGBoost reports a classifier or ranker artifact as a type error.
            raise ValueError(
                f"Model artifact is not an {MODEL_TYPE} regression model: "
                f"{model_path} ({exc})"
            ) from exc
        model._feature_columns = _decode_feature_columns(
            attributes.get(FEATURE_COLUMNS_ATTRIBUTE), model._regressor, model_path
        )
        model._is_fitted = True
        logger.info(
            "Model artifact loaded: %s (features=%d, target=%s)",
            model_path,
            len(model._feature_columns),
            model._target_column,
        )
        return model

    def _reject_reserved_columns(self, features: pd.DataFrame) -> None:
        """Fail when the feature frame still carries the target or timestamp."""
        reserved = [
            column
            for column in (self._target_column, *RESERVED_FEATURE_COLUMNS)
            if column in features.columns
        ]
        if reserved:
            raise ValueError(
                f"features must hold predictors only, but carries {reserved}; "
                "pass the feature columns without the target or timestamp"
            )

    def _require_fitted(self, action: str) -> list[str]:
        """Return the feature contract, failing clearly if there is no model.

        Guards `predict` and `save` so the caller sees a project-level message
        instead of XGBoost's own `NotFittedError`.
        """
        if not self._is_fitted or self._feature_columns is None:
            raise ValueError(
                f"Model is not fitted; call fit() or load() before {action}()"
            )
        return self._feature_columns


def _read_artifact_attributes(model_path: Path) -> dict[str, str]:
    """Return the booster attributes stored inside a model artifact."""
    booster = xgb.Booster()
    try:
        booster.load_model(model_path)
    except xgb.core.XGBoostError as exc:
        raise ValueError(
            f"Model artifact is not a readable XGBoost model: {model_path}"
        ) from exc
    return {
        name: value
        for name, value in booster.attributes().items()
        if value is not None
    }


def _decode_params(raw_params: str | None, model_path: Path) -> dict[str, Any]:
    """Return the parameters recorded by `save`, or none for a foreign artifact."""
    if raw_params is None:
        logger.warning(
            "Model artifact records no %s attribute, so parameters are unknown: %s",
            PARAMS_ATTRIBUTE,
            model_path,
        )
        return {}
    try:
        params = json.loads(raw_params)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Model artifact has an unreadable {PARAMS_ATTRIBUTE} attribute: "
            f"{model_path}"
        ) from exc
    if not isinstance(params, dict):
        raise ValueError(
            f"Model artifact {PARAMS_ATTRIBUTE} attribute must be a mapping: "
            f"{model_path}"
        )
    return params


def _decode_feature_columns(
    raw_columns: str | None, regressor: xgb.XGBRegressor, model_path: Path
) -> list[str]:
    """Return the feature contract, falling back to the booster's own names."""
    if raw_columns is not None:
        columns = json.loads(raw_columns)
        if not isinstance(columns, list) or not all(
            isinstance(column, str) for column in columns
        ):
            raise ValueError(
                f"Model artifact {FEATURE_COLUMNS_ATTRIBUTE} attribute must be a "
                f"list of column names: {model_path}"
            )
        return columns

    booster_columns = regressor.get_booster().feature_names
    if not booster_columns:
        raise ValueError(
            f"Model artifact records no feature columns, so predictions cannot be "
            f"aligned to a feature dataset: {model_path}"
        )
    logger.warning(
        "Model artifact records no %s attribute; using the booster feature "
        "names: %s",
        FEATURE_COLUMNS_ATTRIBUTE,
        model_path,
    )
    return list(booster_columns)


def _validate_features(features: Any) -> pd.DataFrame:
    """Return a feature frame that has at least one column and one row."""
    if not isinstance(features, pd.DataFrame):
        raise ValueError("features must be a pandas DataFrame of predictors")
    if len(features.columns) == 0:
        raise ValueError("features requires at least one feature column")
    if len(features) == 0:
        raise ValueError("features is empty; training requires at least one row")
    return features


def _validate_params(params: Any) -> dict[str, Any]:
    """Return the XGBoost parameters, failing on any the regressor rejects."""
    if params is None:
        return {}
    if not isinstance(params, Mapping):
        raise ValueError(
            "model.params must be a mapping of XGBoost parameter names to values"
        )
    # XGBoost forwards unrecognized keys to the booster and only warns at fit
    # time, which would let a typo silently train with a default instead.
    supported = set(xgb.XGBRegressor().get_params())
    unsupported = sorted(set(params) - supported)
    if unsupported:
        raise ValueError(
            f"Unsupported XGBoost parameter(s) in model.params: {unsupported}. "
            f"Supported parameters: {sorted(supported)}"
        )
    return dict(params)


def _validate_target_column(target_column: Any) -> str:
    """Return a nonempty target column name."""
    if not isinstance(target_column, str) or not target_column.strip():
        raise ValueError("model.target_column must be a nonempty column name")
    return target_column
