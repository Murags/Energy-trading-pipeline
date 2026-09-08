# Record Cleaning

Story 3.2 provides `clean_records` in `preprocessing/cleaning.py` and the read-only
`summarize_records` helper in `preprocessing/validation.py`. These are Python
utilities, not a new CLI command. Timestamp normalization comes first; joining
sources, filling hourly indexes, spread calculation, and processed artifact
exports are outside this story.

## Rules

- Inputs must be nonempty, with unique column names and parsed timezone-aware
  timestamps without nulls. Use `normalize_timestamps` for parsing and DST policy.
- `timestamp` is always required. Supply other required columns per source, e.g.
  `price_de` for German prices, not both markets before alignment.
- Absent required columns always fail. Required null cells either fail (`raise`)
  or remove the affected rows (`drop_rows`). Removing every row fails.
- Duplicate timestamps refer to the same UTC instant. `duplicate_count` counts
  surplus rows. `raise` rejects duplicates; `keep_first` preserves the first row
  in original input order for each instant, even if a later duplicate is more
  complete. Conflicting prices are never averaged.
- Duplicates are resolved before required-null handling. `keep_first` followed
  by `drop_rows` can therefore remove a timestamp whose first record is null.
- All columns not required are optional. Declare expected optional columns to
  detect their absence. Absent optional columns or columns with any input nulls
  warn and are excluded; complete optional columns remain. This conservative
  reduced-column policy is based on input missingness, before row removal.
- Input null counts include every present column, including zero counts. Absent
  optional columns are recorded separately, not counted as null cells.
- Outputs are UTC, stably sorted, and reset to a consecutive index. Inputs are
  not mutated. No imputation, interpolation, resampling, or missing-hour insertion
  occurs. Row removal may create gaps; later hourly alignment must address them.

## Usage

`configs/experiment.yaml` contains explicit fail-fast defaults under
`data.cleaning`. Supported alternatives are `keep_first` and `drop_rows`; the
cleaning function validates policies on invocation. No config-loader change is
required, and the utility has no hidden policy defaults.

For a caller that already has `normalized_df` and a run directory created under
its configured logs root:

```python
from pathlib import Path

from energy_trading_pipeline.config.loader import load_config
from energy_trading_pipeline.preprocessing.cleaning import clean_records

config = load_config(Path("configs/experiment.yaml"))
cleaned_df, audit = clean_records(
    normalized_df,
    required_columns=["price_de"],
    optional_columns=[],
    run_dir=run_dir,
    dataset="prices_de",
    **config["data"]["cleaning"],
)
```

The German synthetic fixture deliberately contains a duplicate, so the default
policy rejects it. Set `duplicate_policy: keep_first` explicitly to clean it.

## Audit Artifact

Every call appends one JSON object to `<run_dir>/preprocessing_log.jsonl`, normally
under `logs/runs/run_YYYYMMDD_HHMMSS/`. Callers provide the run directory explicitly
from their configured artifact root. Multiple source datasets share a log and
are distinguished by `dataset`.

Records contain stage/run/dataset identity, input date range, row counts, null
counts, duplicate instants, configured policies, row-removal counts, required-null
timestamps, excluded optional columns, retained columns, and completion status.
Validation failures include the error and diagnostics available before failure;
they do not claim output rows. The returned audit matches the persisted JSON.
Filesystem errors propagate rather than returning an unaudited successful result.

No generated logs are committed. Tests write audit artifacts under `tmp_path`.
