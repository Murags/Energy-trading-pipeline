# AGENTS.md

## Project Overview

This repository implements a local-first Python DataOps research pipeline for German-French day-ahead electricity price spread forecasting.

The project compares three retraining strategies using an XGBoost forecasting model:

1. `no_retraining`
2. `fixed_schedule`
3. `performance_triggered`

The target variable is:

```text
spread = price_de - price_fr
```

The main research goal is to evaluate whether performance-triggered retraining, based on rolling RMSE, can maintain forecast accuracy while reducing unnecessary retraining compared with fixed-schedule retraining.

This project is not a trading system. It is not a production enterprise ML platform. It is an academic research and implementation prototype focused on reproducibility, traceability, leakage prevention, and controlled historical backtesting.

---

## Source of Truth Documents

Agents must use the following documents as the source of truth, in this order:

1. `_bmad-output/prds/prd-Energy-trading-pipeline-2026-06-15/prd.md`
2. `_bmad-output/prds/prd-Energy-trading-pipeline-2026-06-15/addendum.md`
3. `_bmad-output/architecture.md`
4. `_bmad-output/epics.md`
5. `_bmad-output/implementation-artifacts/`

When working on a story, the specific story file under `_bmad-output/implementation-artifacts/` is the immediate implementation source of truth.

Do not invent new scope that is not present in the PRD, architecture, epics, or current story file.

---

## Implementation Workflow

Agents must work one story at a time.

Before coding:

1. Read the current story file.
2. Read the relevant architecture sections.
3. Identify the files/modules likely affected.
4. Confirm the acceptance criteria.
5. Implement only the current story.

After coding:

1. Run relevant tests.
2. Confirm acceptance criteria.
3. Summarize files changed.
4. Summarize tests run and results.
5. Mention any incomplete work or blockers.

Do not implement future stories unless explicitly instructed.

---

## Current Implementation Order

Implementation follows the sprint artifacts:

```text
Sprint 1: Project setup and configuration foundation
Sprint 2: Local data loading and CI support
Sprint 3: Preprocessing and spread calculation
Sprint 4: Feature engineering with leakage prevention
Sprint 5: XGBoost model training and model registry
Sprint 6: Backtesting engine and forecast logging
Sprint 7: Retraining strategies and event logging
Sprint 8: Evaluation outputs and report artifacts
Sprint 9: Dashboard and documentation support
Sprint 10: Docker and diagram/documentation polish
Sprint 11: Optional AWS and final evaluation documentation
```

Agents must not jump ahead to dashboard, Docker, AWS, or final reporting before the core local pipeline is working.

---

## Repository Structure Rules

Reusable code must live under:

```text
src/energy_trading_pipeline/
```

Expected module boundaries:

```text
src/energy_trading_pipeline/
  cli.py

  config/
  data_ingestion/
  preprocessing/
  features/
  models/
  backtesting/
  monitoring/
  retraining/
  evaluation/
  dashboard/
  utils/
```

Generated artifacts must not be placed under `src/`.

Generated artifacts belong under:

```text
data/
models/
logs/
reports/
```

Tests belong under:

```text
tests/
```

Configuration files belong under:

```text
configs/
```

Documentation belongs under:

```text
docs/
```

Implementation stories belong under:

```text
_bmad-output/implementation-artifacts/
```

---

## Naming Rules

Use `snake_case` for:

* Python files
* Python modules
* Python functions
* Python variables
* dataframe columns
* artifact identifiers
* directory names

Use `PascalCase` for Python classes.

Use `UPPER_SNAKE_CASE` for constants.

Stable strategy identifiers must be exactly:

```text
no_retraining
fixed_schedule
performance_triggered
```

Do not rename these identifiers.

Avoid:

```text
loadLocalPrices
feature-dataset.py
PerformanceTriggeredStrategy as an artifact identifier
```

Prefer:

```text
load_local_prices
feature_dataset.py
performance_triggered
```

---

## Canonical Data Columns

All dataframe columns must use `snake_case`.

Canonical columns include:

```text
timestamp
price_de
price_fr
spread
prediction
actual
error
squared_error
absolute_error
rolling_rmse
strategy
model_version
```

Use these names consistently across preprocessing, features, modelling, backtesting, evaluation, and dashboard exports.

---

## Dependency Management Rules

This project uses [`uv`](https://docs.astral.sh/uv/) as the Python package and environment manager.

Rules:

* `pyproject.toml` is the single source of truth for dependencies (core, dashboard, test, and optional AWS groups).
* `uv.lock` is the committed lockfile and must be kept in sync with `pyproject.toml`.
* Do not create or maintain a `requirements.txt`. It is redundant with `uv.lock` and must not be reintroduced as a second source of truth.
* Use `uv venv --python 3.11` (or newer) to create the local environment, `uv sync` to install dependencies, and `uv run <command>` (e.g. `uv run pytest`) to execute tools inside that environment.
* If a downstream tool strictly requires a `requirements.txt` (e.g. a constrained deployment target), generate it on demand with `uv export` rather than hand-maintaining one.
* Do not add new dependencies without a clear need; keep AWS and dashboard dependency groups optional per `docs/CODING_STYLE.md`.

---

## Configuration Rules

YAML is the canonical configuration format.

Configuration files live under:

```text
configs/
```

The main experiment configuration should include these top-level sections:

```yaml
data:
dates:
features:
model:
backtest:
retraining:
evaluation:
artifacts:
```

Do not hard-code paths, dates, model parameters, retraining intervals, rolling RMSE windows, or thresholds when they can reasonably live in configuration.

---

## Data and Artifact Rules

Local CSV/Parquet loading is first-class.

API ingestion is optional and must not block local experiments.

Processed datasets, feature datasets, forecasts, metrics, and retraining events should be written as Parquet where practical.

CSV may be exported for academic readability, but Parquet is preferred for internal artifacts.

JSON or YAML should be used for metadata.

Each experiment run should write metadata including:

```text
run_id
config_file_path
data_date_range
feature_columns
target_column
model_parameters
strategy
training_windows
evaluation_window
metrics
artifact_paths
```

Run folders should follow:

```text
run_YYYYMMDD_HHMMSS
```

Model versions should follow:

```text
model_YYYYMMDD_HHMMSS
```

---

## Leakage Prevention Rules

Leakage prevention is critical.

Agents must preserve chronological ordering in:

* training
* validation
* forecasting
* feature generation
* rolling metric calculation
* retraining decisions
* backtesting

Rules:

1. Lag features must be shifted before use.
2. Rolling features must not include future values.
3. Rolling features must not include the prediction target timestamp unless explicitly valid for the forecast horizon.
4. Retraining decisions must use only forecast errors available at the decision time.
5. Backtest splits must preserve chronological order.
6. All retraining strategies must use the same data, feature set, model configuration, and evaluation timeline.

If a design choice risks leakage, stop and document the concern before proceeding.

---

## Retraining Strategy Rules

The three retraining strategies are:

```text
no_retraining
fixed_schedule
performance_triggered
```

`no_retraining` trains once and keeps the model fixed.

`fixed_schedule` retrains on a configurable interval. The default comparator is weekly retraining.

`performance_triggered` retrains when rolling RMSE exceeds a configurable threshold.

Rolling RMSE is the primary trigger.

PSI may be logged only as a secondary diagnostic. PSI must not drive retraining in this project.

---

## Dashboard Rules

The dashboard is a lightweight review interface.

The dashboard must read exported artifacts only.

The dashboard must not trigger by default:

* ingestion
* preprocessing
* training
* backtesting
* retraining
* AWS operations

Dashboard inputs should come from:

```text
reports/dashboard_exports/
```

Expected dashboard artifacts include:

```text
forecasts.parquet
metrics.parquet
retraining_events.parquet
model_versions.parquet
```

---

## AWS Rules

AWS is optional and must not be required for local reproducibility.

Allowed optional AWS components:

* S3 for artifact mirroring
* Lambda/EventBridge for lightweight scheduled tasks
* CloudWatch for basic logs
* Terraform for optional infrastructure definition

Do not introduce:

* SageMaker
* Airflow
* Kubernetes
* Spark
* always-on EC2
* full cloud backtesting

Local execution remains the primary path.

---

## Docker and GitHub Actions Rules

Docker and GitHub Actions are supporting tools, not core MVP blockers.

GitHub Actions should:

* install dependencies
* run pytest on fixture datasets
* skip external API tests
* skip AWS tests
* skip full historical backtests

Docker should:

* support reproducible execution
* run tests
* optionally run the Streamlit dashboard
* not replace the local virtual environment workflow

Do not make Docker required for development.

---

## Testing Rules

Use `pytest`.

Tests should live under:

```text
tests/unit/
tests/integration/
tests/fixtures/
```

Use small fixture datasets.

CI must not require:

* ENTSO-E credentials
* AWS credentials
* full 2020-2025 datasets
* network access
* long-running backtests

Tests should cover:

* config loading
* local data loading
* timestamp normalization
* spread calculation
* lag features
* rolling features
* metrics
* retraining policies
* small-range backtesting
* strategy comparison

Mark slow, external API, and AWS tests so they can be skipped by default.

---

## Error Handling Rules

Validation errors should fail fast with clear messages.

Missing required variables should fail.

Missing optional variables should warn and continue with a documented reduced feature set.

API failures should be logged and must not prevent local cached-file runs.

No stage should depend on hidden global state.

Pipeline stages should communicate through explicit function inputs/outputs and persisted artifacts.

---

## Agent Anti-Patterns

Agents must not:

* Put core pipeline logic only in notebooks.
* Make AWS required for local reproducibility.
* Let the dashboard mutate experiment state.
* Compare strategies using different datasets, feature sets, model parameters, or evaluation windows.
* Compute rolling features using future values.
* Compute rolling RMSE using future errors.
* Introduce alternative model families.
* Replace XGBoost with another model.
* Add live trading or P&L simulation.
* Add intraday or balancing-market forecasting.
* Introduce enterprise orchestration tools.
* Overbuild the dashboard before the core pipeline works.

---

## Story Completion Checklist

Before marking a story complete, agents must confirm:

```text
The story acceptance criteria are met.
Only the current story scope was implemented.
Relevant tests were added or updated.
Relevant tests pass.
No future story work was introduced.
No architecture boundary was violated.
No secrets were committed.
Generated artifacts are stored in the correct location.
Code follows naming conventions.
```

Completion response should include:

```text
Story implemented:
Files changed:
Tests added:
Tests run:
Result:
Notes/blockers:
```

---

## Default Agent Instruction

When asked to implement a story, follow this default instruction:

```text
Implement only the specified story file from _bmad-output/implementation-artifacts/.
Use the approved PRD, architecture document, epics.md, and this AGENTS.md file as the source of truth.
Do not implement future stories.
Do not change project scope.
Run relevant tests and report results.
```

## Coding Style

Agents must follow the project coding style guide:

- `docs/CODING_STYLE.md`

The coding style guide defines Python formatting, typing, docstrings, dataframe conventions, timestamp handling, leakage-safe feature generation, testing style, CLI style, dependency rules, and review checklist.

If there is a conflict between `AGENTS.md`, the current story file, and `docs/CODING_STYLE.md`, follow this priority order:

1. Current story file
2. `AGENTS.md`
3. `docs/CODING_STYLE.md`
4. Existing code conventions
