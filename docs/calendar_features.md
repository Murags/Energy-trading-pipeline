# Calendar Features

`energy_trading_pipeline.features.calendar_features.build_calendar_features`
appends the configured calendar columns to a processed hourly dataset. The
selection comes from `features.calendar_features` in `configs/experiment.yaml`,
and the optional holiday flag reads `features.holiday_dates`.

```python
from energy_trading_pipeline.features.calendar_features import (
    build_calendar_features,
)

features, metadata = build_calendar_features(
    processed,
    features=config["features"]["calendar_features"],
    holiday_dates=config["features"]["holiday_dates"],
)
```

## Supported features

| Column | Type | Meaning |
| --- | --- | --- |
| `hour` | `int16` | UTC hour of day, `0`-`23` |
| `day_of_week` | `int16` | UTC day of week, Monday `0` through Sunday `6` |
| `month` | `int16` | UTC calendar month, `1`-`12` |
| `is_weekend` | `bool` | True on Saturday and Sunday (`WEEKEND_DAYS_OF_WEEK`) |
| `is_holiday` | `bool` | True on a configured holiday date; optional |

Integer columns use a fixed `int16` width so the artifact dtype does not depend
on the host platform. An unsupported name in `features.calendar_features` fails
with the supported list rather than being ignored, because it can only be a
configuration mistake.

## Determinism

Every calendar column is a pure function of the row's own UTC timestamp, so two
runs over the same processed data produce identical values, and no calendar
column can leak information from another row. Because nothing looks beyond its
own row, hourly gaps are tolerated here (unlike the lag and rolling builders,
which require contiguous hours).

Columns are always appended in the canonical order listed above, so the order
they appear in configuration never changes the generated dataset. Duplicate
entries are ignored. The function sorts chronologically, normalizes timestamps
to UTC, never mutates the input, and recomputes existing calendar columns of the
same name rather than duplicating them.

No target-derived columns are added by this builder; lag and rolling features
remain the only target-derived features, and they are built by their own
modules.

## Optional holiday flag

`is_holiday` is opt-in and depends on `features.holiday_dates`, a list of ISO
`YYYY-MM-DD` calendar dates. Holidays are matched on the **UTC calendar date**
of each row, which is recorded in metadata as `holiday_date_basis`.

- Requesting `is_holiday` with no configured dates warns, skips the column, and
  reports it under `skipped_features`. Emitting a column that is uniformly false
  would silently look like a real predictor.
- Configuring holiday dates without requesting `is_holiday` warns that the dates
  are unused, so a config mistake is visible.
- Dates may be ISO strings or `datetime.date` values (YAML parses an unquoted
  `2023-01-01` as a date). A timestamp is rejected, because an instant would make
  holiday matching depend on an unstated timezone.

Since German and French holiday calendars differ and no holiday dependency is
approved for this project, the dates are configuration rather than a generated
calendar.

## Metadata

| Key | Meaning |
| --- | --- |
| `requested_features` | Requested features, de-duplicated in canonical order |
| `generated_columns` | Columns actually appended |
| `skipped_features` | Optional features that were requested but unavailable |
| `unconfigured_holiday_policy` | Always `warn_and_skip_is_holiday` |
| `weekend_days_of_week` | Days treated as the weekend; always `[5, 6]` |
| `holiday_dates` | Sorted ISO holiday dates that were applied |
| `holiday_date_basis` | Always `utc_calendar_date` |
| `output_rows` | Row count of the returned frame |

The metadata dictionary is intended to be persisted alongside the feature
dataset by the dataset builder.
