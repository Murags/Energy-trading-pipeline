# Training Window Selection

`energy_trading_pipeline.models.trainer` selects the training and validation
rows of a feature dataset from configured date ranges. Every training row
precedes every validation row, which is how model fitting avoids seeing a row
it is later scored on.

Two pieces make that up:

- `TrainingWindow` — a reusable set of window parameters, validated on
  construction so an invalid window fails before any data is touched.
- `select_training_window(df, window)` — returns a `TrainingSplit` of aligned
  feature and target arrays for both sides of the window.

```python
from energy_trading_pipeline.models.trainer import (
    TrainingWindow,
    select_training_window,
)
from energy_trading_pipeline.models.xgboost_model import XGBoostSpreadModel

window = TrainingWindow.from_config(config["dates"])
split = select_training_window(feature_dataset, window)

model = XGBoostSpreadModel.from_config(config["model"])
model.fit(split.train_features, split.train_target)
predictions = model.predict(split.validation_features)
```

## Configuration

The window is read from the `dates` section of the experiment config. All four
keys are required; they are not defaulted from `dates.start_date` and
`dates.end_date`, because an implied split point would silently decide which
rows a model is scored on.

```yaml
dates:
  start_date: "2023-01-01"
  end_date: "2023-01-08"
  train_start_date: "2023-01-02"
  train_end_date: "2023-01-06"
  validation_start_date: "2023-01-07"
  validation_end_date: "2023-01-08"
```

Construct a `TrainingWindow` directly with the same four bounds when a caller
derives its own windows rather than reading one config, as backtesting and
retraining do when they walk forward.

## Rules

- Bounds are UTC calendar dates (`YYYY-MM-DD` strings or Python dates) and both
  ranges are inclusive of their end date. A training range ending `2023-01-06`
  covers every hourly row through `2023-01-06T23:00`.
- `train_end_date` must be strictly before `validation_start_date`. A shared
  boundary date is rejected as an overlap, because with end-inclusive ranges it
  would put the same 24 rows on both sides. An inverted range fails the same way.
- The selection is verified against the rows it actually found, not only the
  declared bounds: if the last training timestamp is not before the first
  validation timestamp, the call fails rather than returning a leaking split.
- Rows are sorted by `timestamp`, so the returned arrays are chronological even
  if an upstream artifact was written out of order. The input is not mutated.
- `feature_columns` defaults to every column except `timestamp` and the target,
  in frame order. Pass it explicitly to pin the feature contract, which is what
  a retraining run needs to keep matching an existing model. Naming `timestamp`
  or the target as a feature fails: at the prediction timestamp they are the
  index or the target, never predictors.
- Both sides carry the same feature columns in the same order, target values
  come back as a `Series` named for the target column, and indices are reset, so
  the arrays can go straight to `XGBoostSpreadModel.fit` and `predict`.
- `train_timestamps` and `validation_timestamps` are returned alongside, because
  the feature frames exclude the timestamp and forecast logging needs the row
  identity back.
- A range that selects no rows fails with the range covered by the dataset. A
  window reaching outside `dates.start_date`/`dates.end_date` only warns.
- `split.metadata` records the window, feature and target columns, row counts,
  and the actual UTC endpoints of each side, for run and model registry metadata.

Model artifact persistence and registry metadata are separate concerns and are
not written here.

```bash
uv run pytest tests/unit/test_training_window.py -q
```
