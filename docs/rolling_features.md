# Rolling Features

`energy_trading_pipeline.features.rolling_features.build_rolling_features`
appends shifted rolling means and standard deviations of the spread and price
columns to a processed hourly dataset. The windows are the hours listed under
`features.rolling_window_hours` in `configs/experiment.yaml`.

```python
from energy_trading_pipeline.features.rolling_features import build_rolling_features

features, metadata = build_rolling_features(
    processed, window_hours=config["features"]["rolling_window_hours"]
)
```

## Naming

Every generated column follows `<source>_rolling_<statistic>_<window_hours>`,
for example `spread_rolling_mean_24`, `price_de_rolling_std_24`. The window size
is always part of the name, so two configured windows never collide. Sources
default to `spread`, `price_de`, and `price_fr` and can be overridden with
`columns=`. Generated columns are appended after the input columns, grouped by
source, ordered by ascending window, with `mean` before `std`. Existing columns
with the same name are recomputed.

## Leakage rules

- Each source is **shifted by one hour before aggregation**. A row's window
  therefore covers the `n` hours strictly before it and never includes the row's
  own value or any later value. With a 24-hour window, the feature at 12:00
  summarises 12:00 the previous day through 11:00 today.
- A rolling mean over window `n` is exactly the mean of lags `1..n`, which is the
  cross-check asserted in the unit tests against Story 4.1's lag features.
- Windows must be at least 2 hours. A one-hour window is rejected because its
  standard deviation is undefined and would emit a silently all-null column.
- The input must contain unique, contiguous hourly UTC timestamps (the output of
  the alignment and spread stages). The function sorts chronologically and
  rejects gaps, duplicates, and off-hour instants so that a window of `n` rows is
  always exactly `n` hours.
- The input dataframe is never mutated.

The unit tests are mutation-checked: removing the shift, centring the window,
setting `ROLLING_SHIFT_HOURS` to zero, or relaxing `min_periods` each makes
multiple leakage tests fail.

## Rows without a full window

Windows are only aggregated when complete (`min_periods` equals the window), so
a partial window is never silently reported as a shorter-window statistic. Two
cases produce nulls, consistently:

- Rows earlier than the largest configured window lack enough history.
- Windows spanning a null source value cannot be completed.

Those rows are retained with null rolling values rather than dropped, matching
the lag feature policy, so downstream stages see the full processed range and
decide how to treat incomplete rows. The returned metadata makes this explicit:

| Key | Meaning |
| --- | --- |
| `generated_columns` | Ordered list of new rolling columns |
| `window_hours` | Sorted, de-duplicated windows that were applied |
| `statistics` | Always `["mean", "std"]` |
| `source_columns` | Columns that were aggregated |
| `shift_hours` | Hours the source is shifted before aggregation; always `1` |
| `std_ddof` | Delta degrees of freedom for the standard deviation; always `1` |
| `insufficient_window_policy` | Always `retain_rows_with_null_rolling_features` |
| `min_history_hours` | Largest window; rows before this have at least one null |
| `incomplete_window_rows` | Number of leading rows without a full window |
| `output_rows` | Row count of the returned frame |

The metadata dictionary is intended to be persisted alongside the feature
dataset by the dataset builder.
