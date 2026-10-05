# Energy Trading Pipeline

Local-first Python pipeline for German-French electricity price spread forecasting, backtesting, and retraining-strategy evaluation. See `_bmad-output/architecture.md` for the full architecture and `_bmad-output/epics.md` for the implementation roadmap.

## Project Structure

- `src/energy_trading_pipeline/` — reusable pipeline code (config, data ingestion, preprocessing, features, models, backtesting, monitoring, retraining, evaluation, dashboard, utils).
- `configs/` — YAML experiment, path, and model configuration.
- `data/` — raw, processed, and feature datasets (generated, not hand-authored).
- `models/` — trained model artifacts and registry metadata (generated).
- `reports/` — figures, tables, and dashboard-ready exports (generated).
- `logs/` — per-run metadata and event logs (generated).
- `notebooks/` — exploratory and presentation notebooks; no core pipeline logic.
- `tests/` — unit, integration, and fixture-based tests.
- `docs/` — coding standards and architecture diagrams.

## Setup

Dependency management uses [`uv`](https://docs.astral.sh/uv/). `pyproject.toml` is the canonical dependency source; `uv.lock` is the committed lockfile. There is no `requirements.txt`.

Full dependency declarations, `uv sync` setup instructions, and CLI usage will be documented as Stories 1.2-1.4 land.

## Baseline Training

Train once from an existing feature Parquet using explicit experiment, path, and
XGBoost parameter configurations:

```bash
uv run python -m energy_trading_pipeline.cli train \
  --config configs/experiment.yaml \
  --paths-config configs/local_paths.yaml \
  --model-params-config configs/model_params.yaml
```

The paths file must define `feature_data_parquet_path`, `models_dir`, and
`logs_dir`. Relative paths resolve against the repository root. Model parameters
may instead be declared inline under `model.params`; an explicitly supplied
parameters file replaces that mapping. No companion config is loaded implicitly.

The command fits only the configured training dates and reports RMSE and MAE on
the later validation dates. Both date ranges include their full final day in UTC.
It saves `model.json` and `metadata.yaml` under
`<models_dir>/artifacts/model_YYYYMMDD_HHMMSS/`, updates
`<models_dir>/registry/models_index.yaml`, and writes resolved configuration,
selected windows, metrics, and artifact paths to
`<logs_dir>/runs/run_YYYYMMDD_HHMMSS/run_metadata.yaml`.

Use the canonical feature artifact, not processed prices: same-hour `price_de`
and `price_fr` are rejected to prevent target leakage. Missing feature data fails
clearly; training does not generate features, fetch data, backtest, or retrain.
The registry supports one writer at a time and rejects duplicate second-resolution
model versions rather than overwriting prior artifacts. Retry a collision in a
later second. The configured strategy is recorded for provenance, not executed.

The existing config-only bootstrap remains available:

```bash
uv run python -m energy_trading_pipeline.cli --config configs/experiment.yaml
```

## Backtesting

The `backtest` command runs the static `no_retraining` baseline from an existing
local feature Parquet. Create a copy of the experiment config, for example
`configs/backtest.yaml`, and set these sections for the desired data range:

```yaml
backtest:
  evaluation_start_date: "2024-01-03"
  evaluation_end_date: "2024-01-04"
  train_window_days: 1
  validation_window_days: 1
  forecast_horizon_hours: 24
  feature_columns: [hour]  # Explicit ordered predictors present in the Parquet.
retraining:
  strategy: no_retraining
```

Keep the other required experiment sections. Set `dates.start_date` and
`dates.end_date` to describe the input data range. Supply paths and model
parameters with the same flags as training:

```bash
uv run python -m energy_trading_pipeline.cli backtest \
  --config configs/backtest.yaml \
  --paths-config configs/local_paths.yaml \
  --model-params-config configs/model_params.yaml
```

Alternatively, put `paths` (`feature_data_parquet_path`, `models_dir`, `logs_dir`)
and `model.params` directly in the experiment YAML and supply only `--config`.
Relative artifact/input paths resolve against the repository root. The current
shared sample config uses `fixed_schedule`; select `no_retraining` explicitly for
this command. The CLI remains static-only; the policy API below does not enable
scheduled model refits through this command.

### Input and timing contract

The Parquet must contain `timestamp`, `spread` (or the configured model target),
the selected predictor columns, and timezone-aware `feature_available_at` and
`actual_available_at` columns. `feature_available_at` must be the latest actual
availability time of **all selected predictors** in that row;
`actual_available_at` records when its target becomes observable. These are
caller-supplied provenance, not timestamps inferred by the command. Feature
artifacts produced by the current feature builder need these annotations before
backtesting.

Every predictor in a forecast block must be available at block issuance, including
predictors for later delivery hours in that block. Training labels must be
available at first issuance. The runner checks these constraints and complete
hourly training/evaluation coverage before saving a model or forecasts.

Evaluation dates include their full final UTC day. The example trains once on
January 1, holds January 2 out, and forecasts January 3–4. Backtest windows come
from `backtest`, independently of the `dates.train_*` settings used by `train`.
The final forecast block is clipped to the evaluation end. Saved window bounds
use `[start, end)` (exclusive end); the data date range records observed endpoints.

### Outputs

The command prints the run ID and output locations and writes:

- `<logs_dir>/runs/run_YYYYMMDD_HHMMSS/forecasts.parquet` — chronological canonical
  forecast records, actuals, errors, strategy, and model version.
- `run_metadata.yaml` in the same directory — resolved configuration, input data
  range, predictors, parameters, the actual training window, held-out validation
  window, evaluation window, and artifact paths.
- `backtest_log.jsonl` in the same directory — start/completion events with run,
  strategy, model, evaluation range, and forecast count; execution failures record
  an error event and may leave partial artifacts for inspection.
- `<models_dir>/artifacts/model_YYYYMMDD_HHMMSS/model.json` — the fitted model with
  its embedded feature/parameter contract, linked from run metadata.

With `logs_dir: logs`, run outputs are under `logs/runs/run_*`. Run and model
directory collisions fail instead of overwriting; retry in a later second.
Validation is held out but not scored by this command, and run `metrics` is `{}`;
aggregate evaluation and strategy comparison follow in later stories. Model
provenance is in the run metadata; this command does not update the training
registry's validation-metric index. No API credentials, AWS, or dashboard
dependencies are required.

To exercise the command against temporary synthetic fixtures:

```bash
uv run pytest tests/integration/test_backtest_cli.py -q
```

## Retraining Policies

`FixedSchedulePolicy` implements the `fixed_schedule` boolean decision contract.
Its first decision anchors the already-created model's schedule and returns
`False`. Subsequent decisions return `True` once the interval has elapsed, then
restart the interval from that decision time. Repeated timestamps do not trigger
twice. Days are elapsed 24-hour UTC durations, not local calendar days across DST.
Create a new policy instance for each backtest run.

`FixedSchedulePolicy()` defaults to weekly decisions. For experiments, use
`FixedSchedulePolicy.from_config(config)` to read
`retraining.fixed_schedule_interval_days` from the full loaded config. The existing
experiment YAML sets this to `7`; custom intervals must be positive integers.

The standard `policy.as_policy_hook()` receives an aware issuance timestamp and
canonical observable forecast history, returning a boolean. To hand scheduled
request metadata to an event logger, supply both optional callbacks:

```python
from energy_trading_pipeline.backtesting.splitter import (
  generate_backtest_windows_from_config,
)
from energy_trading_pipeline.retraining.fixed_schedule import FixedSchedulePolicy

policy = FixedSchedulePolicy.from_config(config)
training_windows = {
  window.forecast.start: window.train
  for window in generate_backtest_windows_from_config(config)
}
scheduled_requests = []
hook = policy.as_policy_hook(
  training_window_provider=training_windows.__getitem__,
  event_logger=scheduled_requests.append,
)
```

The provider returns the exact candidate `TimeWindow`, preserving the splitter's
held-out validation gap. Windows must end no later than issuance. On a positive
decision, the logger receives UTC ISO `timestamp`, `strategy`, `trigger_reason`,
`interval_days`, and half-open `training_window` bounds (`start`, `end`). These
records describe scheduled requests, not completed training events; the caller
owns execution, model-version metadata, and persistence.

The programmatic runner accepts this hook but still raises `NotImplementedError`
on a positive decision because retraining execution is not yet implemented.
The performance policy and shared event writer below are separate from execution.

### Rolling RMSE Monitor

`calculate_rolling_rmse` returns a dictionary containing `rolling_rmse` at an
explicit timezone-aware decision timestamp. Read the window from the existing
experiment configuration:

```python
from energy_trading_pipeline.monitoring.rolling_rmse import calculate_rolling_rmse

metrics = calculate_rolling_rmse(
  forecast_history,
  decision_timestamp,
  window_days=config["retraining"]["rolling_rmse_window_days"],
)
rolling_rmse = metrics["rolling_rmse"]
```

The default window is seven elapsed UTC days, selecting target timestamps in
`(decision_timestamp - window, decision_timestamp]`. Future target errors and
future issuances are excluded. An error at the decision timestamp is included
only when already observed. Callers must leave errors missing until actuals are
available, including any publication delay; the log does not track publication
times. Required columns are `timestamp` and `error`; canonical forecast logs also
provide the checked `forecast_timestamp` and `strategy` columns.

The default minimum is `window_days * 24` observed hourly errors, so a seven-day
window needs 168. Missing errors do not count or become zeros; insufficient
history returns `NaN`, not an RMSE of zero. Supply a positive `min_periods`
explicitly for a smaller/debug history. Expired errors cannot fill the window.
Select one strategy and one issuance per target before calling the monitor;
mixed strategies and duplicate observed targets fail clearly. Model-version
changes do not reset error history, and the input dataframe remains unchanged.

The monitor only calculates the metric; the policy below makes decisions.

### Performance-Triggered Policy and Events

`PerformanceTriggeredPolicy.from_config(config)` reads
`retraining.rolling_rmse_threshold` and `retraining.rolling_rmse_window_days`.
The existing experiment configuration sets these to `10.0` and `7`. The threshold
must be finite and non-negative. A decision returns `True` only when observed
rolling RMSE is **strictly greater** than the threshold. Equality, lower values,
and insufficient history return `False`. PSI never influences the decision.

Use `policy.should_retrain(decision_timestamp, forecast_history)` or the standard
boolean hook. Create a fresh policy for each run, pass only this strategy's
canonical observable history, and request decisions chronologically. The existing
monitor's window and readiness rules apply; `from_config(config, min_periods=1)`
supports small debug histories. The policy does not reset error history or impose
a cooldown: each decision evaluates the available rolling errors again.

For an auditable request, supply all three optional callbacks. The caller provides
the exact candidate training windows, the active or intended model-version label,
and the configured run directory:

```python
import pandas as pd

from energy_trading_pipeline.retraining.events import (
  RETRAINING_EVENT_COLUMNS,
  write_retraining_events,
)
from energy_trading_pipeline.retraining.performance_triggered import (
  PerformanceTriggeredPolicy,
)

policy = PerformanceTriggeredPolicy.from_config(config)
requests = []
hook = policy.as_policy_hook(
  training_window_provider=training_windows.__getitem__,
  model_version_provider=lambda issuance: active_model_version,
  event_logger=requests.append,
)
needs_retraining = hook(decision_timestamp, forecast_history)
write_retraining_events(
  pd.DataFrame(requests, columns=RETRAINING_EVENT_COLUMNS),
  run_directory / "retraining_events.parquet",
)
```

Positive decisions emit `timestamp`, `strategy`, `trigger_reason`
(`rolling_rmse_exceeds_threshold`), `threshold`, `rolling_rmse`,
`training_window_start`, `training_window_end`, and `model_version`. Windows are
half-open and must end at or before the decision. Callback failures propagate.
These records are **requests**, not evidence of a successful refit. Only the
caller can confirm training success and record the actual registered replacement
version; the policy never invents model versions from forecast history.

`build_retraining_events` validates and sorts a complete event dataframe without
mutating it. `write_retraining_events` writes it as Parquet with UTC timestamps,
creating parent directories after validation. Pass the configured path under
`logs/runs/run_YYYYMMDD_HHMMSS/`. Writing replaces the existing artifact; explicitly
accumulate the full log rather than treating the writer as an append operation.
Empty logs retain the same schema. For fixed-schedule records, flatten the existing
`training_window` handoff, supply the model version, and leave inapplicable
`threshold` and `rolling_rmse` values missing.

The CLI remains static-only, and the programmatic runner still rejects positive
refit requests with `NotImplementedError`. This story adds policy decisions and
event persistence, not retraining execution or model lifecycle changes.

```bash
uv run pytest tests/unit/test_retraining_policies.py \
  tests/unit/test_retraining_events.py tests/unit/test_rolling_rmse.py
```

### Core Evaluation Metrics

`calculate_rmse(actual, prediction)` and `calculate_mae(actual, prediction)` in
`monitoring.metrics` accept equal-length pandas Series and pair values by position,
not index labels. Both skip missing actuals and return `NaN` when none are observed.
Predictions must be finite real numbers even where actuals are missing; malformed
inputs fail clearly. Neither function mutates its inputs.

Aggregate canonical forecast and event dataframes over configured, timezone-aware
pandas timestamp bounds:

```python
from energy_trading_pipeline.evaluation.strategy_comparison import (
  calculate_strategy_metrics,
)

strategy_metrics = calculate_strategy_metrics(
  forecasts,
  completed_retraining_events,
  evaluation_start=evaluation_start,
  evaluation_end=evaluation_end,
)
```

The UTC window is half-open: `[evaluation_start, evaluation_end)`. The result has
one row per strategy represented in the input forecasts, with `strategy`, `rmse`,
`mae`, `retraining_count`, and `retraining_frequency`. Frequency is **completed
retraining events per elapsed UTC day**; missing actuals do not shorten that
denominator. No events yields zero count/frequency; no scored actuals yields `NaN`
error metrics. Empty input logs retain the output schema.

Strategies must share target timestamps and actuals, including missingness.
Duplicate strategy/target pairs, duplicate strategy/event timestamps, and events
without a represented forecast strategy fail. Errors are recomputed from
`actual` and `prediction`, not trusted from cached error columns. Supply completed
retrains only, excluding initial training and unexecuted policy requests: the
event schema does not prove execution success. This API performs no training,
file exports, or CLI changes; the runner's existing execution limit still applies.

### Strategy Comparison Tables

`build_strategy_comparison` adds `run_id`, `evaluation_start`, and
`evaluation_end` to the core strategy metrics. Evaluation bounds are stored as
timezone-aware UTC nanosecond timestamps and describe the same half-open window
used to calculate the metrics. Strategy identifiers and deterministic ordering
are preserved. Empty logs retain the typed schema; missing scored actuals remain
`NaN`, not zero. Directional accuracy is optional and is not implemented here.

Export canonical forecast and **completed** retraining-event dataframes after
backtesting, using the `reports_dir` path configured in `configs/local_paths.yaml`:

```python
import pandas as pd

from energy_trading_pipeline.evaluation.strategy_comparison import (
  write_strategy_comparison,
)

table_paths = write_strategy_comparison(
  forecasts,
  completed_retraining_events,
  run_id=run_id,
  evaluation_start=evaluation_start,
  evaluation_end=evaluation_end,
  tables_dir=reports_dir / "tables",
)
comparison = pd.read_parquet(table_paths["parquet"])
```

The writer returns `parquet` and `csv` paths under
`reports/tables/<run_id>/strategy_comparison.parquet` and
`reports/tables/<run_id>/strategy_comparison.csv`. Both exports contain exactly
`run_id`, `evaluation_start`, `evaluation_end`, `strategy`, `rmse`, `mae`,
`retraining_count`, and `retraining_frequency`, without a dataframe index.
Frequency remains completed retraining events per elapsed UTC day.

Parquet preserves types for subsequent artifact-only dashboard consumption; CSV
provides report-readable values with explicit UTC offsets. When reading CSV,
parse the two evaluation columns with `pd.to_datetime(..., utc=True)` and use
string dtypes for `run_id` and `strategy`. Run IDs must start with a letter or
digit and contain only letters, digits, underscores, or hyphens, preventing
directory traversal. Re-exporting replaces only that run's tables. Inputs are
validated before output directories are created and are never mutated.

This API does not execute backtests or retraining and adds no CLI command.
Use the separate Dashboard Exports command below for dashboard-ready outputs.

### Evaluation Figures

The four functions in `evaluation.plots` render stored evaluation artifacts using
headless Matplotlib. They accept dataframes and an explicit output directory,
return PNG paths, and do not calculate metrics or run any pipeline stage.
Read existing artifacts, then pass the configured `reports_dir / "figures"`:

```python
import pandas as pd

from energy_trading_pipeline.evaluation.plots import (
  plot_forecasts_vs_actuals,
  plot_rolling_rmse,
  plot_retraining_events,
  plot_strategy_comparison,
)

forecasts = pd.read_parquet(forecast_path)
monitoring = pd.read_parquet(monitoring_path)
completed_events = pd.read_parquet(event_path)
comparison = pd.read_parquet(table_paths["parquet"])
options = {"run_id": run_id, "figures_dir": reports_dir / "figures"}
figure_paths = [
  plot_forecasts_vs_actuals(forecasts, **options),
  plot_rolling_rmse(monitoring, **options),
  plot_retraining_events(completed_events, **options),
  plot_strategy_comparison(comparison, **options),
]
```

Use artifact paths from the selected run, and select the same evaluation period
before plotting. CSV inputs loaded with `pd.read_csv` also work; timestamp strings
must include timezone offsets. Required input columns are:

| Figure | Required Columns |
| --- | --- |
| Forecasts vs actuals | `timestamp`, `strategy`, `prediction`, `actual` |
| Rolling RMSE | `timestamp` (decision time), `strategy`, `rolling_rmse` |
| Retraining events | `timestamp` (completed event time), `strategy` |
| Strategy comparison | Story 8.2's complete eight-column comparison table |

Rolling RMSE values must already be stored from monitoring; plotting does not
derive them from errors or fill missing history. Supply completed retrains only,
excluding initial training and unexecuted policy decisions. Missing actuals and
rolling values remain gaps, unavailable comparison scores are labelled explicitly,
and empty artifacts produce no-data figures. Forecast strategies must share target
timestamps and actuals. Comparison rows must share one run and evaluation period;
frequency remains completed retrains per elapsed UTC day, not per scored row.

All aware timestamps are normalized to UTC and time-series rows sorted without
mutating inputs. Validation precedes output creation. Figures use consistent
strategy colors, labelled units, and 180-DPI PNG output under:

```text
reports/figures/forecasts_vs_actuals/<run_id>.png
reports/figures/rolling_rmse/<run_id>.png
reports/figures/retraining_events/<run_id>.png
reports/figures/strategy_comparison/<run_id>.png
```

Re-rendering replaces only the selected run's figures. Safe run IDs follow the
same rules as comparison tables. Plotting does not write dashboard exports.

### Dashboard Exports

Export saved results independently after backtesting and evaluation:

```bash
uv run python -m energy_trading_pipeline.cli export-dashboard \
  --config configs/experiment.yaml \
  --paths-config configs/local_paths.yaml \
  --forecasts logs/runs/<run_id>/forecasts.parquet \
  --metrics reports/tables/<run_id>/strategy_comparison.parquet \
  --retraining-events logs/runs/<run_id>/retraining_events.parquet \
  --model-index models/registry/models_index.yaml
```

Replace `<run_id>` with the selected saved run. `paths.reports_dir` is required,
either inline in the experiment YAML or in the explicit paths companion file.
Relative configured paths resolve against the repository root. Explicit artifact
flags resolve relative to the current working directory. All table inputs are
Parquet; the metrics input is Story 8.2's saved eight-column comparison table.
Forecasts must have the complete canonical forecast-log schema, including
issuance and error columns; events must have the full completed-event schema.
For a static backtest, supply an explicitly saved empty canonical event table.

The static backtest command does not update the training registry. For its model,
replace `--model-index` with `--run-metadata logs/runs/<run_id>/run_metadata.yaml`.
Repeat `--run-metadata` for every referenced version when combining saved results.
Choose either registry or run metadata, not both. No model weights are loaded.
The registry must contain metadata for every selected forecast/event version.
Run metadata must contain `model_version` and `config.model.type`.

Optionally pass `--rolling-rmse <saved_monitoring.parquet>`, with `timestamp`,
`strategy`, and `rolling_rmse`. These are stored decision-time values, joined on
exact timestamp/strategy keys present in the selected forecast timeline. They
are not recalculated or shifted to an earlier time. Sparse monitoring is allowed;
unavailable history and omitted monitoring remain `NaN`, not zero. Unmatched or
duplicate monitoring keys fail explicitly.

The command writes exactly these files under `<reports_dir>/dashboard_exports/`:

| Artifact | Columns |
| --- | --- |
| `forecasts.parquet` | `timestamp`, `prediction`, `actual`, `strategy`, `model_version`, `rolling_rmse` |
| `metrics.parquet` | `run_id`, `evaluation_start`, `evaluation_end`, `strategy`, `rmse`, `mae`, `retraining_count`, `retraining_frequency` |
| `retraining_events.parquet` | `timestamp`, `strategy`, `trigger_reason`, `threshold`, `rolling_rmse`, `model_version` |
| `model_versions.parquet` | `model_version`, `model_type` |

All timestamps are aware UTC. Forecast and event rows are chronological and
limited to the comparison table's half-open evaluation window. Strategies must
share evaluation timestamps and actuals. Stored aggregate metrics are copied,
not recomputed; frequency remains completed retraining events per elapsed UTC
day. Only referenced model metadata is exported, without feature lists, model
parameters, filesystem paths, or weights. Model changes can be reviewed through
the timestamped forecast/event version columns; creation times are not inferred.

Repeated exports replace the four-file dashboard snapshot, not the source logs
or per-run comparison tables. Validation failures leave existing exports intact;
source/output path collisions are rejected. Treat this as a single-writer export
and do not read the snapshot concurrently while its four files are being written.
Empty artifacts retain typed schemas. This command does not run ingestion,
preprocessing, training, backtesting, retraining, dashboard code, or AWS operations.
No new run directory is created. Use the same saved results to call the reusable
`evaluation.exports.write_dashboard_exports` dataframe API when needed.

### Dashboard Artifact Loader

Read the saved snapshot without running any pipeline stage:

```python
from pathlib import Path
from energy_trading_pipeline.dashboard.data_loader import (
  DashboardArtifactError,
  load_dashboard_artifacts,
)

try:
  artifacts = load_dashboard_artifacts(Path("reports/dashboard_exports"))
  forecasts = artifacts["forecasts"]
  metrics = artifacts["metrics"]
  events = artifacts["retraining_events"]
  models = artifacts["model_versions"]
except DashboardArtifactError as error:
  print(error)
```

The same directory is the default, relative to the working directory. For custom
report locations, pass the configured `<reports_dir>/dashboard_exports` path.
All four files and their columns listed above are required, even for empty
tables. Additional columns are excluded from the returned DataFrames. Timestamps
are normalized to nanosecond UTC, rows are sorted for display, and indexes are
reset; naive timestamps are interpreted as UTC. Stored predictions, metrics,
and missing values are preserved, not recomputed. Missing, unreadable, or
malformed exports raise file-specific `DashboardArtifactError` messages.
The loader never writes files, loads model weights, or imports pipeline stages.

### Streamlit Dashboard

From the repository root, install the optional dashboard dependency and launch:

```bash
uv sync --locked --extra dashboard --extra test
uv run --extra dashboard streamlit run src/energy_trading_pipeline/dashboard/app.py
```

Open the local URL printed by Streamlit, normally `http://localhost:8501`.
If PyArrow's native `mimalloc` allocator crashes on macOS with Python 3.14,
launch with its system allocator instead (verified in this workspace):

```bash
ARROW_DEFAULT_MEMORY_POOL=system uv run --extra dashboard streamlit run \
  src/energy_trading_pipeline/dashboard/app.py
```

The sidebar's **Exports directory** defaults to `reports/dashboard_exports`;
set it to the configured export directory for a custom report location. Missing
or malformed exports produce an error message rather than running the pipeline.

The directory must contain `forecasts.parquet`, `metrics.parquet`,
`retraining_events.parquet`, and `model_versions.parquet`, including schemas for
empty tables. See [Dashboard Exports](#dashboard-exports) for their columns and
how to export saved results independently. If Streamlit is unavailable, use the
[static-report fallback](#static-report-fallback) below.

The strategy filter applies to the stored RMSE/MAE summary and all five views:
forecast vs actual, rolling RMSE, retraining events, model version changes, and
strategy comparison. Model metadata is limited to versions referenced by the
selected forecasts or events. Charts retain gaps for unavailable observations
and scores; tables include stored retraining counts and frequency per day.
All timestamps are UTC. No credentials, model weights, ingestion, training,
backtesting, retraining, or AWS operations are required or invoked.

The app only reads the four exported Parquet files. It does not recalculate
metrics, write research artifacts, or run experiments. Importing its modules
does not require the optional Streamlit dependency. To run the fixture chart and
Streamlit smoke tests, use:

```bash
uv run --extra dashboard --extra test pytest -q \
  tests/unit/test_dashboard_charts.py tests/unit/test_dashboard_data_loader.py
```

### Static Report Fallback

Streamlit is optional for reviewing saved results. No full backtest, training,
ingestion, external credentials, or AWS operations are needed for this fallback.

If report outputs already exist, open
`reports/tables/<run_id>/strategy_comparison.csv` in a spreadsheet and the selected
run's PNGs under `reports/figures/forecasts_vs_actuals/`, `rolling_rmse/`,
`retraining_events/`, and `strategy_comparison/`. Their filenames are
`<run_id>.png`; see [Evaluation Figures](#evaluation-figures) for the exact paths.
Use one run and evaluation period throughout. These static files can be inspected
without Python or Streamlit; they are not created merely by opening the dashboard.

If only the four-file dashboard snapshot is available, run this from the
repository root after the normal core setup (`uv sync --locked`). No dashboard
or notebook extra is required; preserve any extras you already use when syncing.
For custom paths, change `exports_dir` to the
configured `<reports_dir>/dashboard_exports`; figures go to the same report
root's `figures` directory.

```bash
uv run python - <<'PY'
from pathlib import Path

from energy_trading_pipeline.dashboard.data_loader import load_dashboard_artifacts
from energy_trading_pipeline.evaluation.plots import (
  plot_forecasts_vs_actuals,
  plot_rolling_rmse,
  plot_retraining_events,
  plot_strategy_comparison,
)

exports_dir = Path("reports/dashboard_exports")
artifacts = load_dashboard_artifacts(exports_dir)
for name, table in artifacts.items():
  print(f"\n{name} ({len(table)} rows)")
  print(table.head(24).to_string(index=False))

metrics = artifacts["metrics"]
if metrics.empty:
  print("No evaluation rows; inspect the empty tables above.")
else:
  run_ids = metrics["run_id"].unique()
  if len(run_ids) != 1:
    raise ValueError("Select a snapshot containing exactly one run_id.")
  options = {"run_id": run_ids[0], "figures_dir": exports_dir.parent / "figures"}
  figure_paths = [
    plot_forecasts_vs_actuals(artifacts["forecasts"], **options),
    plot_rolling_rmse(artifacts["forecasts"], **options),
    plot_retraining_events(artifacts["retraining_events"], **options),
    plot_strategy_comparison(metrics, **options),
  ]
  for path in figure_paths:
    print(path)
PY
```

Open the printed PNG paths in an image viewer or include them in the static
report. The table previews show up to 24 rows each, including model metadata;
the exported forecast/event `model_version` columns retain the version timeline.
Figures use the full snapshot, not just the previews. Stored RMSE/MAE, retraining
counts/frequency, and rolling RMSE are displayed, never recalculated. Missing
scores remain unavailable, empty event logs produce a no-events figure, and
omitted monitoring produces an insufficient-history rolling RMSE figure.

All four exports and their schemas are required even when tables are empty.
Missing or invalid files fail with a file-specific loader error; no pipeline
stage is launched to repair them. Use [Dashboard Exports](#dashboard-exports)
to recreate the snapshot from saved forecasts, comparison tables, completed
events, and model metadata, not by rerunning the experiment. If no saved results
exist, this fallback cannot invent them. An entirely empty snapshot prints its
tables without creating figures because it has no run ID/evaluation period.

The example only writes report PNGs, replacing the selected run's existing
figures. It leaves the Parquet snapshot, source logs, tables, and models unchanged.
Do not read a snapshot while another process is exporting its four files.

## Tests

Install the test dependencies and run the local fixture suite:

```bash
uv sync --locked --extra test
uv run pytest -q
```

The default pytest configuration excludes `external_api`, `aws`, and `slow`
tests. CI explicitly applies the same filter:

```bash
uv run pytest -q -m "not external_api and not aws and not slow"
```

Mark tests with `@pytest.mark.external_api` for live API requests,
`@pytest.mark.aws` for live AWS operations, or `@pytest.mark.slow` for long
computations and full historical backtests. Apply every relevant marker to a
test. Keep offline adapter tests and mocked API/AWS unit tests unmarked so they
continue to run by default. Marker names are strict: a typo fails collection.

Opt in locally by overriding the default marker expression:

```bash
uv run pytest -q -m external_api
uv run pytest -q -m aws
uv run pytest -q -m slow
uv run pytest -q -m ""
```

The last command runs all tests. A category selection includes tests with that
marker even when they also carry another marker. Before opting in, provide the
credentials, network access, local datasets, and optional dependencies required
by the selected tests. For AWS tests, install dependencies with
`uv sync --locked --extra test --extra aws`; live AWS operations may incur charges.

There are currently no live API, live AWS, or long-running tests. The existing
API-adapter tests use offline behavior. Marker-selection integration tests use
temporary synthetic tests and never contact external services. A category-only
command returns pytest exit code 5 when no tests match.

Pytest still imports test modules before marker deselection. Keep live calls and
credential checks inside tests or fixtures, and import optional client libraries
there too, so default collection stays independent of credentials and optional
dependencies.
