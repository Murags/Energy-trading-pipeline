# XGBoost Model Wrapper

`energy_trading_pipeline.models.xgboost_model` wraps `xgboost.XGBRegressor` so
training and prediction share one interface. Every strategy in this project
uses this wrapper, which is how the experiments stay comparable: the same model
family, the same configured parameters, and the same feature contract.

`XGBoostSpreadModel` provides four behaviours:

- `fit(features, target)` trains and returns the wrapper.
- `predict(features)` returns numeric target values.
- `save(output_path)` writes the model artifact.
- `load(model_path)` restores a saved model for prediction.

```python
from energy_trading_pipeline.models.xgboost_model import XGBoostSpreadModel

model = XGBoostSpreadModel.from_config(config["model"])
model.fit(features[feature_columns], features["spread"])
predictions = model.predict(features)

artifact_path = model.save(model_dir / "model.json")
restored = XGBoostSpreadModel.load(artifact_path)
```

## Configuration

Build the wrapper with `from_config(config["model"])`, the `model` section of
the experiment config:

```yaml
model:
  type: xgboost
  target_column: spread
```

`energy_trading_pipeline.config.loader.load_config` merges
`configs/model_params.yaml` into `model.params`, so the XGBoost parameters live
in config rather than in code:

```yaml
n_estimators: 100
max_depth: 4
learning_rate: 0.05
subsample: 0.8
colsample_bytree: 0.8
random_state: 42
objective: reg:squarederror
```

Rules:

- `params` keys must all be accepted by `XGBRegressor`. An unrecognized key
  fails at construction. XGBoost itself would forward the key to the booster
  and only warn at fit time, which would let a typo such as `max_dept` silently
  train with the default `max_depth`.
- Omitted parameters keep XGBoost defaults. `params` may be absent entirely.
- `target_column` defaults to `spread`.
- `type` must be `xgboost`. Any other value fails, because this project
  forecasts with one model family and does not compare alternatives.
- Unrecognized keys in the `model` section warn, so a typo does not silently
  fall back to a default.

Setting `random_state` makes a fit reproducible: the same config and the same
rows produce the same predictions.

## Feature Contract

The column order of the frame passed to `fit` becomes the model's feature
contract. `predict` selects those columns in their recorded training order, so
a caller may pass columns in any order, and may pass a full feature dataset row
that also carries `timestamp` and `spread` — extra columns are ignored. A
missing trained feature column fails and names the column.

`fit` rejects a feature frame that still carries the target column or
`timestamp`. At the prediction timestamp those are the target and the index,
not predictors, so passing the feature dataset straight to `fit` would train on
the target. Select the feature columns first:

```python
feature_columns = [
    column for column in dataset.columns if column not in ("timestamp", "spread")
]
model.fit(dataset[feature_columns], dataset["spread"])
```

Predictions are returned as a float64 NumPy array of one value per input row,
matching the dtype of the pipeline's `spread` column. Neither input frame is
mutated.

## Model Artifact

`save` writes a single JSON artifact and requires a `.json` path, per the
`models/artifacts/model_YYYYMMDD_HHMMSS/model.json` layout in
`_bmad-output/architecture.md`. A missing parent directory is created, and an
existing artifact at the path is replaced.

The configured parameters, feature columns, target column, and model family are
stored as booster attributes *inside* the artifact. `load` reads them back, so a
restored model:

- predicts identically to the model that was saved,
- reports the parameters it was trained under,
- enforces the same feature contract,
- can be refitted with those same parameters.

This keeps the wrapper to one self-describing file. XGBoost's own `load_model`
leaves the scikit-learn parameters unset, so without these attributes a loaded
model could predict but could not report or reproduce its own configuration.

Registry metadata — model version, training window, validation metrics, and
`models/registry/models_index.yaml` — is a separate concern and is **not**
written here.

`load` fails clearly when the artifact is missing, unreadable, or not an
XGBoost regression model; a classifier artifact is rejected rather than loaded
as a regressor.

`fit`, `save`, and `load` log the row and feature counts, the target column, and
the artifact path. Calling `predict` or `save` before `fit` or `load` fails with
a clear message rather than XGBoost's `NotFittedError`.
