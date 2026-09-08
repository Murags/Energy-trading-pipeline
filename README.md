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
