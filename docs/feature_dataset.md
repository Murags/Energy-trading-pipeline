# Feature Dataset Artifact

`energy_trading_pipeline.features.dataset_builder` combines every feature
builder into the one artifact that modelling and backtesting consume:

- `build_feature_dataset(df, feature_config, *, source_dataset)` returns the
  dataset and its metadata.
- `save_feature_dataset(df, output_path, *, feature_config, source_dataset)`
  builds it and writes the Parquet artifact plus a metadata sidecar.

```python
from energy_trading_pipeline.features.dataset_builder import save_feature_dataset

feature_path, metadata_path = save_feature_dataset(
    processed,
    config["paths"]["feature_data_parquet_path"],
    feature_config=config["features"],
    source_dataset=processed_path,
)
```

The output path is the configured `feature_data_parquet_path` in
`configs/local_paths.yaml`, which resolves to
`data/features/feature_dataset.parquet`. The metadata is written beside it as
`data/features/feature_dataset.metadata.yaml`. Both are generated artifacts and
are git-ignored.

## Contents

The artifact holds exactly `timestamp`, the `spread` target, and the generated
feature columns, in that order. Contemporaneous `price_de` and `price_fr` are
**not** passed through: at the target timestamp they *are* the target, since
`spread = price_de - price_fr`. Their lagged and rolling forms are features.

Feature columns are collected in a fixed stage order so the artifact is
reproducible from the processed data and config alone:

| Stage | Source | Columns |
| --- | --- | --- |
| `lag` | `features.lag_hours` | `<source>_lag_<hours>` |
| `rolling` | `features.rolling_window_hours` | `<source>_rolling_<statistic>_<hours>` |
| `calendar` | `features.calendar_features`, `features.holiday_dates` | `hour`, `day_of_week`, `month`, `is_weekend`, `is_holiday` |
| `weather` | `features.weather_columns` | selected weather variables |
| `grid` | `features.grid_columns` | selected load/generation variables |

Colliding column names across stages fail rather than silently overwriting one
another. See `docs/lag_features.md`, `docs/rolling_features.md`,
`docs/calendar_features.md`, and `docs/exogenous_features.md` for each builder.

## Configuration

`feature_config` is the `features` section of the experiment config.
`lag_hours` and `rolling_window_hours` are required. The calendar, holiday,
weather, and grid keys are optional; an absent exogenous key requests no
predictors from that group rather than guessing which optional variables the
processed dataset happens to carry. Unrecognized keys warn, so a typo such as
`calender_features` does not silently fall back to a default.

Optional weather and grid variables that were never ingested warn and are left
out of the feature set instead of failing the run, so a price-only processed
dataset still builds.

## Incomplete rows

The leading hours of the processed range cannot have a complete feature vector,
because the configured lags and rolling windows need history that does not exist
yet. Those rows are dropped, so every retained row is usable by modelling and
all retraining strategies compare on identical rows. The count is recorded as
`incomplete_rows_dropped`, and `date_range` describes the retained rows while
`source_date_range` describes the processed input. With the shipped config
(`lag_hours: [1, 24]`, `rolling_window_hours: [24]`), the first 24 hours are
dropped.

If no row has a complete feature vector, the build fails with a message naming
the two config keys to adjust rather than writing an empty artifact.

## Metadata

| Key | Meaning |
| --- | --- |
| `target_column` | Always `spread` |
| `feature_columns` | Ordered feature columns, the modelling contract |
| `source_processed_dataset` | Path of the processed dataset that was built from |
| `source_date_range` / `source_rows` | Bounds and row count of the processed input |
| `date_range` / `output_rows` | Bounds and row count of the retained rows |
| `feature_config` | Normalized feature settings each stage actually applied |
| `excluded_columns` | Processed columns deliberately not used as features |
| `incomplete_row_policy` | Always `drop_rows_without_a_complete_feature_vector` |
| `incomplete_rows_dropped` | Leading rows dropped for insufficient history |
| `feature_stages` | Each builder's own metadata report, in stage order |
| `artifact_paths` | Written Parquet and metadata paths |

Because `feature_config` records the resolved settings and `feature_stages`
records what each builder did, a run can be reproduced from the processed
dataset and the metadata alone.
