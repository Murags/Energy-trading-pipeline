# Weather and Grid Features

`energy_trading_pipeline.features.weather_features.build_weather_features` and
`energy_trading_pipeline.features.grid_features.build_grid_features` select the
optional exogenous predictors for the feature dataset. Both read their column
lists from configuration (`features.weather_columns` and
`features.grid_columns` in `configs/experiment.yaml`) and both delegate to
`features.optional_features.select_optional_features`, which holds the shared
usability rules.

```python
from energy_trading_pipeline.features.grid_features import build_grid_features
from energy_trading_pipeline.features.weather_features import (
    build_weather_features,
)

features, weather_metadata = build_weather_features(
    processed, columns=config["features"]["weather_columns"]
)
features, grid_metadata = build_grid_features(
    features, columns=config["features"]["grid_columns"]
)
```

## Pass-through, not derivation

Weather and grid variables arrive in the processed dataset from the hourly
alignment stage, so these builders do not derive anything from the target. They
decide which configured columns are usable and cast them to `float64` so the
artifact dtype is stable. Because each value belongs to its own timestamp and
nothing is aggregated across rows, no shift is required.

Default column sets:

- Weather (`DEFAULT_WEATHER_COLUMNS`): `temperature_2m_c`,
  `wind_speed_10m_m_s`, `shortwave_radiation_w_m2` — the Open-Meteo variables
  the ingestion layer caches.
- Grid (`DEFAULT_GRID_COLUMNS`): `load_de`, `load_fr`, `generation_de`,
  `generation_fr` — the optional ENTSO-E load and generation series.

Market and target columns (`timestamp`, `price_de`, `price_fr`, `spread`) are
rejected as optional predictor names, because passing a contemporaneous price
through as an exogenous feature would leak the target.

## Warn and continue

A configured column is usable only when it is **present, real numeric, and free
of missing or non-finite values**. Anything else warns and is excluded from
`selected_columns` instead of failing the run, leaving a documented reduced
feature set:

- **Absent** — the variable was never ingested. Grid ingestion in particular is
  optional, so this is a normal local-run outcome and an empty grid selection is
  expected.
- **Unusable** — present but non-numeric, or carrying missing or non-finite
  values. The hourly alignment stage already excludes optional columns with
  missing hours, so this mostly guards against a hand-assembled dataset. Partial
  nulls are excluded rather than tolerated, because the dataset builder drops
  incomplete rows and would otherwise shrink the artifact silently.

An empty configured list is valid and requests no optional predictors at all,
without warnings. Nothing is ever removed from the returned frame: the dataset
builder selects the feature columns from `selected_columns`, so excluded columns
simply never become features.

Both builders sort chronologically, normalize timestamps to UTC, and never
mutate the input.

## Metadata

| Key | Meaning |
| --- | --- |
| `group` | `weather` or `grid` |
| `requested_columns` | Configured columns, de-duplicated in configured order |
| `selected_columns` | Columns that became features |
| `missing_columns` | Configured columns absent from the processed dataset |
| `unusable_columns` | Column name mapped to the reason it was excluded |
| `unavailable_column_policy` | Always `warn_and_continue_with_reduced_feature_set` |
| `dtype` | Dtype selected columns are cast to; always `float64` |
| `output_rows` | Row count of the returned frame |

The metadata dictionaries are intended to be persisted alongside the feature
dataset by the dataset builder, so a run records exactly which exogenous
predictors were available.
