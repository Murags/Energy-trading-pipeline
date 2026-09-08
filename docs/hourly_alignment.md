# Hourly Alignment

`preprocessing.alignment.align_hourly_data` joins normalized and cleaned German
prices, French prices, and optional weather/grid data by exact delivery instant.
Call the local loader, `normalize_timestamps`, and `clean_records` first.

```python
from energy_trading_pipeline.preprocessing.alignment import align_hourly_data

aligned, alignment_report = align_hourly_data(
    cleaned_prices_de,
    cleaned_prices_fr,
    weather=cleaned_weather,  # None when unavailable
    grid=None,  # Or a cleaned frame containing load/generation/grid columns
    start_date=config["dates"]["start_date"],
    end_date=config["dates"]["end_date"],
)
```

## Rules

- Date bounds are inclusive UTC calendar dates (`YYYY-MM-DD` strings or Python
  dates). January 1 through January 8 includes 192 hours, ending January 8 at
  23:00 UTC. A single calendar day is also supported by the function.
- Output has a sorted `timestamp` column and exactly one row per requested hour.
  Source rows outside the configured range do not enter the output.
- Timestamps must already be parsed and timezone-aware. They are converted to
  UTC without changing instants. Distinct fall-back DST hours stay distinct;
  local wall-clock ambiguities must be resolved during normalization.
- Duplicate instants, off-hour timestamps, duplicate column names, and column
  collisions between sources fail. There is no implicit aggregation or suffixing.
- Each price source must contain its own canonical `price_de` or `price_fr`
  column, with non-null values for every requested hour, including endpoints.
  A required-row drop during cleaning can therefore cause alignment to fail.
- Absent or empty optional sources warn and are recorded in
  `missing_optional_sources`. Optional columns with any missing aligned values
  warn and are excluded. Complete optional columns remain unchanged. Source
  columns must have distinct names, such as `load_de` and `load_fr`.
- No rows are silently dropped from the requested timeline; no interpolation,
  forward/backfill, nearest-time joins, or lag/rolling features are applied.
- Inputs are not mutated. The returned report records actual UTC endpoints,
  row count, retained/excluded columns, absent optional sources, and per-column
  missing counts before exclusions. Preserve this report with downstream metadata.

Historical weather/grid alignment does not establish forecast-time availability.
Later feature generation must enforce that constraint before using these values.

The fixture integration test handles the intentional German duplicate with
`keep_first`; cleaning excludes the incomplete temperature column but preserves
wind and radiation. It then verifies all 192 price/weather hours.

```bash
uv run pytest tests/unit/test_alignment.py tests/integration/test_hourly_alignment.py -q
```

This story exposes an in-memory preprocessing function only. Spread calculation,
processed Parquet persistence under `data/processed/aligned_hourly/`, and source
metadata persistence belong to Story 3.4. No CLI command is added here.
