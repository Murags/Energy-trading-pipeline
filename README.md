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
this command. Other strategies fail clearly until their policies are available.

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
