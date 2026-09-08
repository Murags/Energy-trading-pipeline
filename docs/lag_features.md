# Lag Features

`energy_trading_pipeline.features.lag_features.build_lag_features` appends
lagged copies of the spread and price columns to a processed hourly dataset.
The lags are the hours listed under `features.lag_hours` in
`configs/experiment.yaml`.

```python
from energy_trading_pipeline.features.lag_features import build_lag_features

features, metadata = build_lag_features(processed, lag_hours=config["features"]["lag_hours"])
```

## Naming

Every generated column follows `<source>_lag_<hours>`, for example
`spread_lag_1`, `price_de_lag_24`, `price_fr_lag_24`. Sources default to
`spread`, `price_de`, and `price_fr` and can be overridden with `columns=`.
Generated columns are appended after the input columns, grouped by source and
ordered by ascending lag. Existing columns with the same name are recomputed.

## Leakage rules

- Every lag must be a strictly positive integer. A lag of zero is rejected
  because it would feed the target timestamp's own value into its features.
- The input must contain unique, contiguous hourly UTC timestamps (the output of
  the alignment and spread stages). The function sorts chronologically and
  rejects gaps, duplicates, and off-hour instants so that a shift of `n` rows is
  always exactly `n` hours.
- The input dataframe is never mutated.

## Rows without sufficient history

Rows earlier than the largest configured lag cannot be fully populated. They are
retained with null lag values rather than dropped, so downstream stages see the
full processed range and decide how to treat incomplete rows. The returned
metadata makes this explicit:

| Key | Meaning |
| --- | --- |
| `generated_columns` | Ordered list of new lag columns |
| `lag_hours` | Sorted, de-duplicated lags that were applied |
| `source_columns` | Columns that were lagged |
| `insufficient_history_policy` | Always `retain_rows_with_null_lags` |
| `min_history_hours` | Largest lag; rows before this have at least one null lag |
| `incomplete_history_rows` | Number of rows with at least one null lag |
| `output_rows` | Row count of the returned frame |

The metadata dictionary is intended to be persisted alongside the feature
dataset by the dataset builder.
