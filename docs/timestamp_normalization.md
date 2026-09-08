# Timestamp Normalization

Story 3.1 provides timestamp normalization independently of cleaning, alignment,
or CLI orchestration:

```python
from pathlib import Path

from energy_trading_pipeline.data_ingestion.local_loader import load_local_data
from energy_trading_pipeline.preprocessing.timestamps import normalize_timestamps

raw = load_local_data(Path("tests/fixtures/sample_prices_fr.csv"))
normalized, metadata = normalize_timestamps(raw, source_timezone="UTC")
```

The input must have a canonical `timestamp` column. The returned dataframe is a
copy sorted by UTC timestamp with a reset index; other columns and all rows are
preserved. Equal timestamps retain their original relative order.

## Timezone and DST Policy

- Naive timestamps are localized in the supplied IANA `source_timezone`, default
  `UTC`. Supply `Europe/Berlin` or `Europe/Paris` for naive local market times.
- Aware timestamps retain their explicit instant and are converted to UTC. Their
  offsets take precedence over `source_timezone`, which applies only to naive
  values. Mixed naive and aware inputs follow these same rules per row.
- Repeated fall-back hours without offsets are ambiguous and raise `ValueError`.
  Supply offset-aware values such as `2023-10-29T02:00:00+02:00` and
  `2023-10-29T02:00:00+01:00` to represent the two distinct delivery hours.
- Nonexistent spring-forward local times also raise `ValueError`. No timestamps
  are shifted, inferred from neighboring rows, or silently dropped.
- Invalid or missing timestamps fail with zero-based input row positions. Numeric
  epochs are rejected because seconds versus milliseconds cannot safely be
  inferred. Convert epochs using their documented unit before calling this API.
- Use ISO 8601 strings or datetime objects; normalize source-specific date formats
  explicitly before calling rather than relying on ambiguous day/month ordering.

## Validation and Metadata

`metadata` is a JSON/YAML-serializable dictionary returned explicitly for the
caller to persist with later stage artifacts. This function performs no file I/O.
It records the supplied naive-source timezone, observed aware source timezone
names or fixed offsets, naive-value count, UTC output timezone, and DST policy.
Fixed offsets cannot identify an original IANA timezone.

`metadata["hourly_validation"]` reports sorting, surplus duplicate-row counts,
unique duplicate instants, off-hour row counts and timestamps, missing-hour counts
and timestamps, and `is_hourly`. Issues also emit a logging warning. Missing hours
are whole UTC hours between the observed endpoints, not coverage of an external
experiment range. A single on-hour timestamp has no internal gaps and is valid;
empty input is rejected. Hourly-spaced data starting at `00:30` is not on-hour.

The standalone `validate_hourly_index(series)` accepts parsed timezone-aware
datetime series, checks in UTC, and reports unsorted input without reordering it.
Normalization sorts before invoking this validator. Duplicates and gaps do not
prevent normalization: callers requiring a complete hourly index must check
`is_hourly`. Cleaning and cross-source alignment belong to subsequent stories.

Run the focused tests with `uv run pytest tests/unit/test_timestamps.py`.
