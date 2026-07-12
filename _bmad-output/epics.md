---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - _bmad-output/prds/prd-Energy-trading-pipeline-2026-06-15/prd.md
  - _bmad-output/architecture.md
workflowType: epics-and-stories
status: ready_for_github_projects
created: 2026-06-18
project_name: Energy-trading-pipeline
github_projects_ready: true
epic_count: 12
story_count: 48
---

# Energy-trading-pipeline - Implementation Epics and Stories

## GitHub Projects Tracking Notes

- Each `Epic` should be created as a GitHub tracking issue with label `type: epic`.
- Each `Story` should be created as a GitHub issue with label `type: story` and linked from its parent epic issue.
- Suggested priority uses `P0`, `P1`, `P2`, where `P0` is MVP-critical.
- Suggested sprint numbers should map to GitHub Milestones, for example `Sprint 1`, `Sprint 2`, and so on.
- GitHub Projects fields should track `Status`, `Priority`, `Sprint`, `Epic`, and optionally `Module`.
- API, dashboard, Docker, GitHub Actions, AWS, and documentation work are intentionally separated from core modelling and backtesting stories.

### Recommended GitHub Labels

- `type: epic`
- `type: story`
- `priority: p0`
- `priority: p1`
- `priority: p2`
- `area: foundation`
- `area: data-ingestion`
- `area: preprocessing`
- `area: features`
- `area: modelling`
- `area: backtesting`
- `area: retraining`
- `area: evaluation`
- `area: dashboard`
- `area: ci`
- `area: docker`
- `area: aws`
- `area: docs`
- `blocked`
- `needs-review`

### Recommended Milestones

- `Sprint 1`: foundation-only setup and configuration.
- `Sprint 2`: local data loading, preprocessing start, and early CI support.
- `Sprint 3`: leakage-safe feature engineering.
- `Sprint 4`: XGBoost model training and registry.
- `Sprint 5`: backtesting engine and forecast logging.
- `Sprint 6`: retraining policies and event logging.
- `Sprint 7`: evaluation outputs and report artifacts.
- `Sprint 8`: dashboard, Dockerfile support, and core documentation.
- `Sprint 9`: dashboard Docker Compose, diagrams, and CLI catalogue.
- `Sprint 10`: optional AWS and final academic evaluation documentation.

### Recommended GitHub Issue Body Template

Use this structure when creating each story issue:

```markdown
## User Story

[Copy user story]

## Description

[Copy description]

## Acceptance Criteria

[Copy acceptance criteria]

## Technical Notes

[Copy technical notes]

## Files / Modules Likely Affected

[Copy files/modules likely affected]

## Testing Requirements

[Copy testing requirements]

## Dependencies

[Copy dependencies]

## Project Fields

- Epic: [Parent epic title]
- Priority: [P0/P1/P2]
- Sprint: [Sprint N]
```

Use this structure when creating each epic tracking issue:

```markdown
## Epic Goal

[Copy epic goal]

## Scope

[Copy scope]

## Out of Scope

[Copy out of scope]

## Key Architecture Modules / Files

[Copy modules/files]

## Dependencies

[Copy dependencies]

## Acceptance Criteria

[Copy acceptance criteria]

## Child Stories

- [ ] Story N.1: ...
- [ ] Story N.2: ...
```

## Epic List

1. Project Setup and Configuration Foundation
2. Local Data Loading and Artifact Handling
3. Data Preprocessing and Spread Calculation
4. Feature Engineering with Leakage Prevention
5. XGBoost Model Training and Model Registry
6. Backtesting Engine and Forecast Logging
7. Retraining Strategies and Event Logging
8. Evaluation Outputs and Report Artifacts
9. Dashboard Reading Exported Artifacts Only
10. Docker, GitHub Actions, and Reproducibility Support
11. Optional AWS Artifact Mirroring
12. Documentation and Diagrams

## Epic 1: Project Setup and Configuration Foundation

- Epic title: Project Setup and Configuration Foundation
- Epic goal: Establish the local-first Python project skeleton, dependency baseline, configuration structure, CLI entry point, and fixture-based test foundation.
- Scope: Repository structure, Python package layout, `pyproject.toml`, `uv.lock`, `.env.example`, `configs/`, initial CLI, config loader, path resolver, and test fixture scaffolding.
- Out of scope: Data ingestion logic, modelling, backtesting, dashboard, Docker, GitHub Actions, AWS, and academic report content.
- Key architecture modules/files: `pyproject.toml`, `uv.lock`, `.env.example`, `configs/experiment.yaml`, `configs/local_paths.yaml`, `configs/model_params.yaml`, `src/energy_trading_pipeline/cli.py`, `src/energy_trading_pipeline/config/loader.py`, `src/energy_trading_pipeline/config/schema.py`, `src/energy_trading_pipeline/config/paths.py`, `tests/fixtures/`.
- Dependencies: Approved PRD and architecture.
- Acceptance criteria: Project skeleton matches the approved architecture, dependencies install in a local virtual environment, config files can be loaded from CLI, path resolution works without external credentials, initial tests run against fixtures.

### Story 1.1: Create Python Project Skeleton

- User story: As a developer, I want the repository structure and package layout created so that implementation agents have stable module boundaries.
- Description: Create the approved directory structure, package namespace, root project files, and placeholder modules without implementing pipeline behavior.
- Acceptance criteria: `src/energy_trading_pipeline/` exists with module folders from the architecture, root files exist, generated artifact directories are represented with `.gitkeep` or documented placeholders, no core logic is placed in notebooks.
- Technical notes: Use `snake_case` directories and keep reusable code under `src/` only.
- Files/modules likely affected: `src/energy_trading_pipeline/`, `configs/`, `data/`, `models/`, `reports/`, `logs/`, `notebooks/`, `tests/`, `docs/`.
- Testing requirements: Verify package import succeeds with a minimal import test.
- Dependencies: None.
- Suggested priority: P0
- Suggested sprint: Sprint 1

### Story 1.2: Define Dependency and Environment Files

- User story: As a developer, I want dependency and environment files so that the project can be installed reproducibly in a local Python environment.
- Description: Add `pyproject.toml`, `uv.lock`, `.env.example`, and initial dependency groups for core, dashboard, test, and optional AWS tooling, managed with `uv`.
- Acceptance criteria: Python 3.11+ is declared, core dependencies include pandas, NumPy, scikit-learn, XGBoost, PyArrow, Matplotlib/Plotly, PyYAML, pytest; `uv.lock` is committed and in sync with `pyproject.toml`; `.env.example` contains placeholder ENTSO-E and AWS variables only; no secrets are committed.
- Technical notes: Pin or constrain versions during implementation setup using `uv add`/`uv lock`; keep AWS dependencies optional; do not introduce a `requirements.txt`.
- Files/modules likely affected: `pyproject.toml`, `uv.lock`, `.env.example`.
- Testing requirements: Create a smoke test that imports the package after dependency installation.
- Dependencies: Story 1.1.
- Suggested priority: P0
- Suggested sprint: Sprint 1

### Story 1.3: Implement YAML Configuration Loader

- User story: As a developer, I want a config loader so that paths, date ranges, model parameters, and retraining settings are controlled outside code.
- Description: Implement config loading and schema validation for experiment, local paths, and model parameter YAML files.
- Acceptance criteria: Loader reads YAML files, validates required top-level sections, merges path/model config into the experiment runtime config, fails clearly on missing required keys, supports configurable start/end dates and retraining defaults.
- Technical notes: Required sections are `data`, `dates`, `features`, `model`, `backtest`, `retraining`, `evaluation`, and `artifacts`.
- Files/modules likely affected: `configs/experiment.yaml`, `configs/local_paths.yaml`, `configs/model_params.yaml`, `src/energy_trading_pipeline/config/loader.py`, `src/energy_trading_pipeline/config/schema.py`, `src/energy_trading_pipeline/config/paths.py`.
- Testing requirements: Unit tests for valid config, missing required section, invalid date order, and path resolution.
- Dependencies: Story 1.2.
- Suggested priority: P0
- Suggested sprint: Sprint 1

### Story 1.4: Add Initial CLI Entry Point

- User story: As a researcher, I want a CLI entry point so that pipeline stages can be run reproducibly from commands.
- Description: Add a minimal CLI that loads config, prints resolved run settings, creates a run ID, and prepares run artifact folders.
- Acceptance criteria: CLI accepts `--config`, creates `run_YYYYMMDD_HHMMSS`, writes `run_metadata.yaml`, and exits successfully without requiring data files or credentials.
- Technical notes: Do not implement ingestion, preprocessing, modelling, or backtesting in this story.
- Files/modules likely affected: `src/energy_trading_pipeline/cli.py`, `src/energy_trading_pipeline/utils/time.py`, `src/energy_trading_pipeline/utils/io.py`, `logs/runs/`.
- Testing requirements: Unit or integration test invokes CLI against `tests/fixtures/sample_config.yaml`.
- Dependencies: Story 1.3.
- Suggested priority: P0
- Suggested sprint: Sprint 1

### Story 1.5: Create Sample Experiment Configuration

- User story: As a developer, I want sample experiment configuration files so that the local-first pipeline has clear defaults before data processing begins.
- Description: Create sample YAML configuration files for experiment settings, local paths, model parameters, and fixture-based tests.
- Acceptance criteria: `configs/experiment.yaml`, `configs/local_paths.yaml`, and `configs/model_params.yaml` exist; test fixture config exists under `tests/fixtures/sample_config.yaml`; defaults include weekly fixed-schedule retraining; defaults include a 7-day rolling RMSE window; rolling RMSE threshold is configurable; local CSV/Parquet paths are represented; no credentials are required.
- Technical notes: Config defaults should support fixture/debug runs and should not imply full 2020-2025 execution by default.
- Files/modules likely affected: `configs/experiment.yaml`, `configs/local_paths.yaml`, `configs/model_params.yaml`, `tests/fixtures/sample_config.yaml`.
- Testing requirements: Config loader tests validate all sample config files.
- Dependencies: Story 1.3.
- Suggested priority: P0
- Suggested sprint: Sprint 1

## Epic 2: Local Data Loading and Artifact Handling

- Epic title: Local Data Loading and Artifact Handling
- Epic goal: Make local CSV/Parquet loading and artifact persistence first-class so MVP experiments do not depend on external APIs.
- Scope: Local loaders, raw artifact layout, cached data handling, ingestion metadata, fixture datasets, and optional API adapter placeholders.
- Out of scope: Actual ENTSO-E/Open-Meteo API implementation, preprocessing, feature engineering, model training, and backtesting.
- Key architecture modules/files: `src/energy_trading_pipeline/data_ingestion/local_loader.py`, `src/energy_trading_pipeline/data_ingestion/cache.py`, `src/energy_trading_pipeline/data_ingestion/entsoe_client.py`, `src/energy_trading_pipeline/data_ingestion/open_meteo_client.py`, `data/raw/`, `tests/fixtures/`.
- Dependencies: Epic 1.
- Acceptance criteria: Local German/French price and weather/grid files can be loaded from config paths, loaders support CSV and Parquet, ingestion metadata is written, API adapters remain optional and do not block local runs.

### Story 2.1: Implement Local CSV and Parquet Loader

- User story: As a researcher, I want to load local CSV/Parquet files so that experiments can run without API access.
- Description: Implement reusable local loading functions for configured dataset paths and supported file formats.
- Acceptance criteria: Loader reads CSV and Parquet, returns pandas DataFrames, validates file existence, logs source path and row count, raises clear errors for unsupported formats.
- Technical notes: Keep local loading independent of ENTSO-E/Open-Meteo clients.
- Files/modules likely affected: `src/energy_trading_pipeline/data_ingestion/local_loader.py`, `src/energy_trading_pipeline/utils/io.py`.
- Testing requirements: Unit tests load sample CSV and sample Parquet fixture data.
- Dependencies: Story 1.3.
- Suggested priority: P0
- Suggested sprint: Sprint 2

### Story 2.2: Define Raw Artifact Cache Layout

- User story: As a developer, I want a raw artifact cache layout so that downloaded and local raw inputs are traceable.
- Description: Implement helpers that resolve and create raw data paths for ENTSO-E prices, load, generation, and Open-Meteo weather.
- Acceptance criteria: Raw artifact paths follow `data/raw/entsoe/...` and `data/raw/open_meteo/...`, helpers create missing directories, path decisions are config-driven, raw files are treated as immutable once cached.
- Technical notes: This story creates storage conventions only; it does not fetch API data.
- Files/modules likely affected: `src/energy_trading_pipeline/data_ingestion/cache.py`, `src/energy_trading_pipeline/config/paths.py`, `data/raw/`.
- Testing requirements: Unit tests verify path resolution and directory creation in a temporary test directory.
- Dependencies: Story 2.1.
- Suggested priority: P0
- Suggested sprint: Sprint 2

### Story 2.3: Add Fixture Datasets for Local Tests

- User story: As a developer, I want small fixture datasets so that CI and local tests can run without credentials or large files.
- Description: Create minimal German price, French price, weather, and optional grid/load fixture files covering enough hourly rows to test alignment and simple backtesting.
- Acceptance criteria: Fixtures include timestamp, German price, French price, and weather columns; fixture date range is small; fixtures contain at least one missing-value or duplicate case for validation tests.
- Technical notes: Fixture data may be synthetic and must not represent research results.
- Files/modules likely affected: `tests/fixtures/sample_prices_de.csv`, `tests/fixtures/sample_prices_fr.csv`, `tests/fixtures/sample_weather.csv`, `tests/fixtures/sample_config.yaml`.
- Testing requirements: Loader tests consume these fixtures.
- Dependencies: Story 2.1.
- Suggested priority: P0
- Suggested sprint: Sprint 2

### Story 2.4: Add Optional API Adapter Interfaces

- User story: As a developer, I want optional API adapter interfaces so that ENTSO-E and Open-Meteo fetching can be added without changing downstream modules.
- Description: Add interface-style functions or classes for ENTSO-E and Open-Meteo clients with explicit not-configured behavior.
- Acceptance criteria: API adapters are importable, missing credentials produce clear skip/fallback messages, downstream code can depend on local cached files instead, no API call is made in tests by default.
- Technical notes: Do not implement full API fetching here; preserve local-first MVP.
- Files/modules likely affected: `src/energy_trading_pipeline/data_ingestion/entsoe_client.py`, `src/energy_trading_pipeline/data_ingestion/open_meteo_client.py`.
- Testing requirements: Unit tests verify missing credentials do not break local loading path.
- Dependencies: Story 2.2.
- Suggested priority: P1
- Suggested sprint: Sprint 2

## Epic 3: Data Preprocessing and Spread Calculation

- Epic title: Data Preprocessing and Spread Calculation
- Epic goal: Produce a cleaned and aligned hourly dataset with the canonical German-French spread target.
- Scope: Timestamp standardization, timezone handling, missing/duplicate checks, hourly alignment, spread calculation, validation, and processed Parquet output.
- Out of scope: Feature generation beyond target creation, model training, backtesting, and evaluation plots.
- Key architecture modules/files: `src/energy_trading_pipeline/preprocessing/timestamps.py`, `cleaning.py`, `alignment.py`, `spread.py`, `validation.py`, `data/processed/aligned_hourly/`.
- Dependencies: Epic 2.
- Acceptance criteria: Local price/weather/grid inputs are cleaned, aligned to hourly timestamps, validated, and written to processed Parquet with canonical `timestamp`, `price_de`, `price_fr`, and `spread` columns.

### Story 3.1: Implement Timestamp Normalization

- User story: As a researcher, I want timestamps normalized consistently so that all datasets align correctly across sources.
- Description: Implement timestamp parsing, timezone normalization, hourly index validation, and daylight-saving-time handling.
- Acceptance criteria: Timestamp column is parsed reliably, modelling timestamps are normalized consistently, non-hourly or ambiguous timestamps are reported, DST handling is documented in metadata.
- Technical notes: Default policy should normalize modelling timestamps to UTC while preserving source timezone metadata where useful.
- Files/modules likely affected: `src/energy_trading_pipeline/preprocessing/timestamps.py`, `src/energy_trading_pipeline/preprocessing/validation.py`.
- Testing requirements: Unit tests cover normal hourly data, missing hours, duplicate timestamps, and DST-like edge cases.
- Dependencies: Story 2.3.
- Suggested priority: P0
- Suggested sprint: Sprint 2

### Story 3.2: Implement Missing and Duplicate Record Cleaning

- User story: As a researcher, I want missing and duplicate records handled reproducibly so that preprocessing decisions are auditable.
- Description: Implement cleaning utilities that detect duplicates, summarize missingness, apply configured missing-value rules, and write preprocessing logs.
- Acceptance criteria: Duplicate timestamps are detected, missing values are counted by column, required missing values fail or are handled by configured rule, optional missing values warn and continue, cleaning decisions are logged.
- Technical notes: Keep rules simple and documented; avoid silent imputation.
- Files/modules likely affected: `src/energy_trading_pipeline/preprocessing/cleaning.py`, `src/energy_trading_pipeline/preprocessing/validation.py`, `logs/runs/*/preprocessing_log.jsonl`.
- Testing requirements: Unit tests for duplicate detection and missing-value behavior.
- Dependencies: Story 3.1.
- Suggested priority: P0
- Suggested sprint: Sprint 2

### Story 3.3: Align Market, Grid, and Weather Data Hourly

- User story: As a researcher, I want all input datasets aligned to hourly delivery periods so that model inputs are consistent.
- Description: Join German price, French price, weather, and optional grid/load/generation data onto a common hourly timestamp index.
- Acceptance criteria: Aligned output includes one row per hourly timestamp, required price columns are present, optional weather/grid columns are included when available, alignment range follows config start/end dates.
- Technical notes: Do not generate lag or rolling model features in this story.
- Files/modules likely affected: `src/energy_trading_pipeline/preprocessing/alignment.py`, `data/processed/aligned_hourly/`.
- Testing requirements: Integration test aligns sample price and weather fixtures.
- Dependencies: Story 3.2.
- Suggested priority: P0
- Suggested sprint: Sprint 2

### Story 3.4: Calculate German-French Spread Target

- User story: As a researcher, I want the target spread calculated consistently so that all downstream modelling uses the same target variable.
- Description: Add spread calculation as `spread = price_de - price_fr` and persist processed aligned output.
- Acceptance criteria: Output includes `spread`, calculation is verified against known fixture values, processed dataset is saved as Parquet, metadata records source files and date range.
- Technical notes: Use canonical column names `price_de`, `price_fr`, and `spread`.
- Files/modules likely affected: `src/energy_trading_pipeline/preprocessing/spread.py`, `data/processed/aligned_hourly/`.
- Testing requirements: Unit test validates spread arithmetic and processed Parquet output.
- Dependencies: Story 3.3.
- Suggested priority: P0
- Suggested sprint: Sprint 2

## Epic 4: Feature Engineering with Leakage Prevention

- Epic title: Feature Engineering with Leakage Prevention
- Epic goal: Build a reproducible feature dataset with lag, rolling, calendar, weather, and grid predictors while preventing look-ahead leakage.
- Scope: Lag features, rolling features, calendar features, optional weather/grid features, feature metadata, and leakage prevention tests.
- Out of scope: Model training, retraining policies, strategy evaluation, and dashboard views.
- Key architecture modules/files: `src/energy_trading_pipeline/features/lag_features.py`, `rolling_features.py`, `calendar_features.py`, `weather_features.py`, `grid_features.py`, `dataset_builder.py`, `data/features/`.
- Dependencies: Epic 3.
- Acceptance criteria: Feature dataset is generated from processed data, lag and rolling features only use information available before prediction time, feature metadata is saved, tests catch obvious leakage cases.

### Story 4.1: Implement Lag Feature Generation

- User story: As a researcher, I want lagged spread and price features so that the model can learn recent market dynamics.
- Description: Generate configured lag features for spread, German price, and French price.
- Acceptance criteria: Lag columns follow `snake_case`, lags are shifted correctly, rows without sufficient history are handled consistently, generated columns are recorded in metadata.
- Technical notes: Lag features must never use the target timestamp value as an input for the same prediction timestamp.
- Files/modules likely affected: `src/energy_trading_pipeline/features/lag_features.py`.
- Testing requirements: Unit tests verify lag values against a simple ordered fixture.
- Dependencies: Story 3.4.
- Suggested priority: P0
- Suggested sprint: Sprint 3

### Story 4.2: Implement Leakage-Safe Rolling Features

- User story: As a researcher, I want rolling features that exclude future values so that backtest results are valid.
- Description: Generate configured rolling means and standard deviations for spread and price variables using shifted windows.
- Acceptance criteria: Rolling windows are shifted before aggregation where required, rolling feature names include window size, insufficient windows are handled consistently, leakage tests fail if current/future values are included incorrectly.
- Technical notes: This is a high-risk research-validity story; keep implementation explicit and tested.
- Files/modules likely affected: `src/energy_trading_pipeline/features/rolling_features.py`.
- Testing requirements: Unit tests compare expected rolling values and verify no current timestamp leakage.
- Dependencies: Story 4.1.
- Suggested priority: P0
- Suggested sprint: Sprint 3

### Story 4.3: Implement Calendar, Weather, and Grid Feature Builders

- User story: As a researcher, I want calendar, weather, and grid predictors so that the model can use relevant exogenous signals.
- Description: Generate hour, day-of-week, month, weekend flag, optional holiday flag, and pass-through or transformed weather/grid predictors when available.
- Acceptance criteria: Calendar features are deterministic, optional weather/grid variables warn and continue if unavailable, feature selection is config-driven, output uses canonical `snake_case` column names.
- Technical notes: Avoid target-derived features in this story except already approved lag/rolling features.
- Files/modules likely affected: `src/energy_trading_pipeline/features/calendar_features.py`, `weather_features.py`, `grid_features.py`.
- Testing requirements: Unit tests for calendar extraction and optional-variable behavior.
- Dependencies: Story 4.2.
- Suggested priority: P0
- Suggested sprint: Sprint 3

### Story 4.4: Build Feature Dataset Artifact

- User story: As a developer, I want a feature dataset builder so that modelling and backtesting consume one reproducible artifact.
- Description: Combine feature generation outputs into a canonical feature dataset and metadata file.
- Acceptance criteria: `data/features/feature_dataset.parquet` is written, metadata records target column, feature columns, source processed dataset, date range, and feature config, builder can run on fixture data.
- Technical notes: Keep feature generation deterministic from processed data and config.
- Files/modules likely affected: `src/energy_trading_pipeline/features/dataset_builder.py`, `data/features/`.
- Testing requirements: Integration test builds a feature dataset from processed fixtures.
- Dependencies: Story 4.3.
- Suggested priority: P0
- Suggested sprint: Sprint 3

## Epic 5: XGBoost Model Training and Model Registry

- Epic title: XGBoost Model Training and Model Registry
- Epic goal: Train and persist the XGBoost spread forecasting model with traceable metadata.
- Scope: XGBoost wrapper, training function, chronological splits, model artifact persistence, metadata registry, and model configuration handling.
- Out of scope: Backtesting loop, retraining policies, strategy comparison, dashboard, and cloud registry tools.
- Key architecture modules/files: `src/energy_trading_pipeline/models/xgboost_model.py`, `trainer.py`, `registry.py`, `models/artifacts/`, `models/registry/models_index.yaml`.
- Dependencies: Epic 4.
- Acceptance criteria: XGBoost model trains on feature data, saves artifacts and metadata, records training window/features/parameters/metrics, and uses the same model configuration for future strategies.

### Story 5.1: Implement XGBoost Model Wrapper

- User story: As a developer, I want a model wrapper so that training and prediction use one consistent XGBoost interface.
- Description: Create a wrapper around XGBoost regression with fit, predict, save, and load behavior.
- Acceptance criteria: Wrapper accepts model parameters from config, predicts numeric spread values, saves model artifact, loads saved model for prediction, does not introduce alternate model families.
- Technical notes: Prefer simple `XGBRegressor` unless implementation needs lower-level `DMatrix` behavior.
- Files/modules likely affected: `src/energy_trading_pipeline/models/xgboost_model.py`.
- Testing requirements: Unit test trains and predicts on tiny fixture features.
- Dependencies: Story 4.4.
- Suggested priority: P0
- Suggested sprint: Sprint 4

### Story 5.2: Implement Training Window Selection

- User story: As a researcher, I want chronological training windows so that model fitting avoids future data leakage.
- Description: Implement training dataset selection by configured train/validation date ranges and reusable window parameters.
- Acceptance criteria: Training rows precede validation/evaluation rows, date ranges are config-driven, invalid overlapping ranges fail clearly, selected feature/target arrays are returned consistently.
- Technical notes: This supports later backtesting and retraining windows.
- Files/modules likely affected: `src/energy_trading_pipeline/models/trainer.py`, `src/energy_trading_pipeline/backtesting/splitter.py` if shared.
- Testing requirements: Unit tests for valid chronological split and invalid overlapping split.
- Dependencies: Story 5.1.
- Suggested priority: P0
- Suggested sprint: Sprint 4

### Story 5.3: Save Model Artifacts and Metadata

- User story: As a researcher, I want trained models saved with metadata so that model versions are traceable.
- Description: Persist model artifacts under `models/artifacts/model_YYYYMMDD_HHMMSS/` and update registry metadata.
- Acceptance criteria: Model artifact is saved, metadata includes model version, training window, feature columns, target column, parameters, validation metrics, and creation timestamp; `models_index.yaml` is updated.
- Technical notes: Use filesystem registry, not MLflow.
- Files/modules likely affected: `src/energy_trading_pipeline/models/registry.py`, `models/artifacts/`, `models/registry/models_index.yaml`.
- Testing requirements: Unit test verifies metadata content and model index update in temp directory.
- Dependencies: Story 5.2.
- Suggested priority: P0
- Suggested sprint: Sprint 4

### Story 5.4: Add Baseline Training CLI Command

- User story: As a researcher, I want a CLI command for baseline training so that model creation is reproducible from config.
- Description: Add CLI support to load feature data, train the model, save artifacts, and write training metadata.
- Acceptance criteria: Command runs on fixture feature data, writes model artifact and metadata, uses configured model parameters, fails clearly if feature dataset is missing.
- Technical notes: Do not implement backtesting or retraining in this story.
- Files/modules likely affected: `src/energy_trading_pipeline/cli.py`, `src/energy_trading_pipeline/models/trainer.py`.
- Testing requirements: Integration test invokes training CLI against fixture data.
- Dependencies: Story 5.3.
- Suggested priority: P0
- Suggested sprint: Sprint 4

## Epic 6: Backtesting Engine and Forecast Logging

- Epic title: Backtesting Engine and Forecast Logging
- Epic goal: Simulate historical forecasting over time and log forecast records consistently for all retraining strategies.
- Scope: Chronological backtest runner, evaluation timeline, model training/prediction orchestration, forecast logging, small-range debug runs, and CLI command.
- Out of scope: Retraining policy implementation beyond hooks, evaluation plots, dashboard, and AWS.
- Key architecture modules/files: `src/energy_trading_pipeline/backtesting/splitter.py`, `backtest_runner.py`, `forecast_log.py`, `logs/runs/*/backtest_log.jsonl`.
- Dependencies: Epic 5.
- Acceptance criteria: Backtest runner processes a configurable date range chronologically, logs predictions and actuals, avoids look-ahead bias, and supports small fixture-based runs.

### Story 6.1: Implement Chronological Backtest Splitter

- User story: As a researcher, I want chronological backtest periods so that historical simulation respects time order.
- Description: Build utilities that generate train, validation, and forecast windows for a configured evaluation range.
- Acceptance criteria: Windows are ordered chronologically, future timestamps are excluded from training, small debug ranges are supported, invalid windows fail clearly.
- Technical notes: This splitter may be reused by model training and retraining logic.
- Files/modules likely affected: `src/energy_trading_pipeline/backtesting/splitter.py`.
- Testing requirements: Unit tests for window generation and leakage boundary cases.
- Dependencies: Story 5.4.
- Suggested priority: P0
- Suggested sprint: Sprint 5

### Story 6.2: Implement Forecast Log Schema

- User story: As a developer, I want a forecast log schema so that all strategies produce comparable prediction records.
- Description: Define forecast log writing for timestamp, target timestamp, prediction, actual, error, squared error, absolute error, strategy, and model version.
- Acceptance criteria: Forecast logs use canonical column names, logs can be written/read as Parquet or CSV, errors are computed consistently, strategy and model version are required.
- Technical notes: Use `forecast_timestamp` if needed in addition to canonical `timestamp` for target period clarity.
- Files/modules likely affected: `src/energy_trading_pipeline/backtesting/forecast_log.py`, `logs/runs/`.
- Testing requirements: Unit tests verify error calculations and required columns.
- Dependencies: Story 6.1.
- Suggested priority: P0
- Suggested sprint: Sprint 5

### Story 6.3: Implement Single-Strategy Backtest Runner

- User story: As a researcher, I want to run a backtest for one strategy at a time so that the runner can be validated before strategy comparison.
- Description: Implement runner orchestration that trains or loads models, predicts over the evaluation timeline, and writes forecast logs for a supplied retraining policy hook.
- Acceptance criteria: Runner executes on fixture feature data, records predictions and actuals, writes forecast logs, supports a static model baseline path, preserves chronological order.
- Technical notes: Keep retraining policy internals minimal until Epic 7; use a placeholder no-retraining hook if needed.
- Files/modules likely affected: `src/energy_trading_pipeline/backtesting/backtest_runner.py`, `src/energy_trading_pipeline/backtesting/forecast_log.py`.
- Testing requirements: Integration test runs a small backtest and verifies output columns and row order.
- Dependencies: Story 6.2.
- Suggested priority: P0
- Suggested sprint: Sprint 5

### Story 6.4: Add Backtesting CLI Command

- User story: As a researcher, I want a CLI command for backtesting so that historical experiments can be rerun from config.
- Description: Add CLI support to run a small or configured backtest and write run metadata, forecast logs, and backtest logs.
- Acceptance criteria: CLI runs a small fixture backtest, writes outputs under `logs/runs/run_*`, accepts config path, and does not require dashboard, AWS, or external API credentials.
- Technical notes: Full strategy comparison happens later; this command establishes execution path.
- Files/modules likely affected: `src/energy_trading_pipeline/cli.py`, `src/energy_trading_pipeline/backtesting/backtest_runner.py`.
- Testing requirements: Integration test invokes CLI on fixture data.
- Dependencies: Story 6.3.
- Suggested priority: P0
- Suggested sprint: Sprint 5

## Epic 7: Retraining Strategies and Event Logging

- Epic title: Retraining Strategies and Event Logging
- Epic goal: Implement the three required retraining strategies with consistent decision logic and event logs.
- Scope: Policy interface, no-retraining policy, fixed-schedule policy, rolling RMSE monitor, performance-triggered policy, retraining event schema, and tests.
- Out of scope: Dashboard, AWS, final academic plots, and alternate retraining signals as primary triggers.
- Key architecture modules/files: `src/energy_trading_pipeline/retraining/policies.py`, `no_retraining.py`, `fixed_schedule.py`, `performance_triggered.py`, `events.py`, `src/energy_trading_pipeline/monitoring/rolling_rmse.py`.
- Dependencies: Epic 6.
- Acceptance criteria: All three strategies can be executed by the backtesting runner, rolling RMSE is the main performance trigger, PSI remains secondary only, events are logged consistently.

### Story 7.1: Define Retraining Policy Interface and No-Retraining Policy

- User story: As a developer, I want a common retraining policy interface so that strategies can be swapped in the same backtest runner.
- Description: Implement base policy contract and no-retraining strategy.
- Acceptance criteria: Policy interface returns retrain/no-retrain decisions, `no_retraining` trains once and never triggers retraining after initial model creation, strategy identifier is stable.
- Technical notes: Do not hard-code strategy behavior into the backtest runner.
- Files/modules likely affected: `src/energy_trading_pipeline/retraining/policies.py`, `src/energy_trading_pipeline/retraining/no_retraining.py`.
- Testing requirements: Unit test verifies no-retraining behavior across multiple decision timestamps.
- Dependencies: Story 6.3.
- Suggested priority: P0
- Suggested sprint: Sprint 6

### Story 7.2: Implement Fixed-Schedule Retraining Policy

- User story: As a researcher, I want weekly fixed-schedule retraining so that scheduled retraining can be compared with performance-triggered retraining.
- Description: Implement `fixed_schedule` policy with configurable retraining interval and weekly default.
- Acceptance criteria: Policy triggers at configured interval, default interval is weekly, training window details are passed to event logging, strategy identifier is `fixed_schedule`.
- Technical notes: Use config values rather than hard-coded intervals where practical.
- Files/modules likely affected: `src/energy_trading_pipeline/retraining/fixed_schedule.py`, `configs/experiment.yaml`.
- Testing requirements: Unit tests verify weekly and custom interval decisions.
- Dependencies: Story 7.1.
- Suggested priority: P0
- Suggested sprint: Sprint 6

### Story 7.3: Implement Rolling RMSE Monitor

- User story: As a researcher, I want rolling RMSE calculated from available forecast errors so that performance deterioration can be detected.
- Description: Implement rolling RMSE calculation with configurable window and no future error leakage.
- Acceptance criteria: Default window supports 7-day rolling RMSE, function uses only available historical errors at decision time, outputs `rolling_rmse`, insufficient history is handled explicitly.
- Technical notes: This metric drives performance-triggered retraining and must be tested carefully.
- Files/modules likely affected: `src/energy_trading_pipeline/monitoring/rolling_rmse.py`, `src/energy_trading_pipeline/monitoring/metrics.py`.
- Testing requirements: Unit tests verify rolling RMSE values and no future error usage.
- Dependencies: Story 7.2.
- Suggested priority: P0
- Suggested sprint: Sprint 6

### Story 7.4: Implement Performance-Triggered Retraining and Event Logging

- User story: As a researcher, I want retraining triggered when rolling RMSE exceeds a threshold so that model updates are tied to observed degradation.
- Description: Implement `performance_triggered` policy and retraining event writer.
- Acceptance criteria: Policy triggers when rolling RMSE exceeds configurable threshold, event log records trigger reason, threshold, rolling RMSE value, training window, model version, timestamp, and strategy; PSI is not used as trigger.
- Technical notes: Threshold may initially be derived from validation-period performance but must remain configurable.
- Files/modules likely affected: `src/energy_trading_pipeline/retraining/performance_triggered.py`, `src/energy_trading_pipeline/retraining/events.py`, `logs/runs/*/retraining_events.parquet`.
- Testing requirements: Unit tests for below-threshold, at-threshold, above-threshold, and insufficient-history behavior.
- Dependencies: Story 7.3.
- Suggested priority: P0
- Suggested sprint: Sprint 6

## Epic 8: Evaluation Outputs and Report Artifacts

- Epic title: Evaluation Outputs and Report Artifacts
- Epic goal: Produce academic-quality strategy comparison metrics, plots, tables, and dashboard-ready exported artifacts.
- Scope: RMSE, MAE, retraining frequency, optional directional accuracy, optional PSI diagnostics, comparison tables, plots, and exports.
- Out of scope: Dashboard UI, AWS storage, Docker, and documentation prose beyond generated artifacts.
- Key architecture modules/files: `src/energy_trading_pipeline/evaluation/strategy_comparison.py`, `plots.py`, `exports.py`, `src/energy_trading_pipeline/monitoring/metrics.py`, `reports/`.
- Dependencies: Epic 7.
- Acceptance criteria: All three strategies are compared on the same backtesting setup, core metrics are exported, plots are generated, and report/dashboard artifacts are written.

### Story 8.1: Implement Core Evaluation Metrics

- User story: As a researcher, I want RMSE, MAE, and retraining frequency calculated by strategy so that the three strategies can be compared.
- Description: Implement metric functions and strategy-level aggregation from forecast logs and retraining events.
- Acceptance criteria: RMSE, MAE, and retraining count/frequency are calculated for each strategy, metrics handle missing actuals consistently, outputs use canonical column names.
- Technical notes: Optional directional accuracy can be added after core metrics pass.
- Files/modules likely affected: `src/energy_trading_pipeline/monitoring/metrics.py`, `src/energy_trading_pipeline/evaluation/strategy_comparison.py`.
- Testing requirements: Unit tests verify metric calculations against known small arrays.
- Dependencies: Story 7.4.
- Suggested priority: P0
- Suggested sprint: Sprint 7

### Story 8.2: Implement Strategy Comparison Tables

- User story: As a researcher, I want strategy comparison tables so that results can be used in the final report.
- Description: Generate summary tables for RMSE, MAE, retraining count, retraining frequency, and optional directional accuracy.
- Acceptance criteria: Tables are written under `reports/tables/`, strategy identifiers are stable, tables include run ID and evaluation period, output can be read by dashboard later.
- Technical notes: CSV exports are acceptable for report readability; Parquet can be used for canonical dashboard exports.
- Files/modules likely affected: `src/energy_trading_pipeline/evaluation/strategy_comparison.py`, `reports/tables/`.
- Testing requirements: Integration test builds comparison table from fixture forecast/event logs.
- Dependencies: Story 8.1.
- Suggested priority: P0
- Suggested sprint: Sprint 7

### Story 8.3: Implement Evaluation Plots

- User story: As a researcher, I want plots for forecasts, rolling RMSE, retraining events, and strategy comparison so that results are easy to interpret.
- Description: Generate report-ready figures using Matplotlib or Plotly from exported forecast and metric artifacts.
- Acceptance criteria: Forecast-vs-actual plot is generated, rolling RMSE plot is generated, retraining event visualization is generated, strategy comparison plot is generated, figures are written under `reports/figures/`.
- Technical notes: Keep plotting separate from metric calculations.
- Files/modules likely affected: `src/energy_trading_pipeline/evaluation/plots.py`, `reports/figures/`.
- Testing requirements: Smoke tests verify plot files are created from small fixtures.
- Dependencies: Story 8.2.
- Suggested priority: P1
- Suggested sprint: Sprint 7

### Story 8.4: Export Dashboard-Ready Artifacts

- User story: As an analyst, I want dashboard-ready exported artifacts so that the dashboard can read results without running the pipeline.
- Description: Write forecast, metric, retraining event, and model version artifacts to `reports/dashboard_exports/`.
- Acceptance criteria: Exports include `forecasts.parquet`, `metrics.parquet`, `retraining_events.parquet`, and `model_versions.parquet`; exports contain only columns needed by the dashboard; export command can run independently after backtests.
- Technical notes: This story enforces the artifact-only dashboard contract.
- Files/modules likely affected: `src/energy_trading_pipeline/evaluation/exports.py`, `reports/dashboard_exports/`.
- Testing requirements: Integration test verifies dashboard export files and schemas.
- Dependencies: Story 8.3.
- Suggested priority: P0
- Suggested sprint: Sprint 7

## Epic 9: Dashboard Reading Exported Artifacts Only

- Epic title: Dashboard Reading Exported Artifacts Only
- Epic goal: Provide a lightweight Streamlit dashboard or fallback review interface that visualizes exported results without mutating experiment state.
- Scope: Artifact loader, Streamlit app, charts, strategy filters, and dashboard fallback notes.
- Out of scope: Running ingestion, training, backtesting, retraining, AWS deployment, and Docker.
- Key architecture modules/files: `src/energy_trading_pipeline/dashboard/app.py`, `data_loader.py`, `charts.py`, `reports/dashboard_exports/`.
- Dependencies: Epic 8.
- Acceptance criteria: Dashboard reads exported artifacts only, shows forecasts/actuals, rolling RMSE, retraining events, model versions, and strategy comparison; missing exports produce clear messages.

### Story 9.1: Implement Dashboard Artifact Loader

- User story: As an analyst, I want the dashboard to load exported artifacts so that results can be viewed without rerunning experiments.
- Description: Implement dashboard-only loaders for forecast, metric, retraining event, and model version exports.
- Acceptance criteria: Loader reads from `reports/dashboard_exports/`, validates expected files/columns, returns display-ready DataFrames, fails with clear user-facing messages for missing exports.
- Technical notes: Loader must not import or invoke backtesting, training, or ingestion functions.
- Files/modules likely affected: `src/energy_trading_pipeline/dashboard/data_loader.py`.
- Testing requirements: Unit tests load dashboard fixture exports and handle missing files.
- Dependencies: Story 8.4.
- Suggested priority: P1
- Suggested sprint: Sprint 8

### Story 9.2: Implement Streamlit Dashboard Views

- User story: As an analyst, I want to view forecasts, actual spreads, rolling RMSE, retraining events, and strategy comparisons so that I can inspect model behavior.
- Description: Build a Streamlit app with charts and tables from exported artifacts.
- Acceptance criteria: Dashboard shows forecast vs actual, RMSE/MAE summaries, rolling RMSE, retraining events, model version changes, and strategy comparison; strategy filters are available; app starts without credentials.
- Technical notes: Keep app simple and avoid overbuilding UI.
- Files/modules likely affected: `src/energy_trading_pipeline/dashboard/app.py`, `src/energy_trading_pipeline/dashboard/charts.py`.
- Testing requirements: Smoke test imports app modules and validates chart functions on fixtures.
- Dependencies: Story 9.1.
- Suggested priority: P1
- Suggested sprint: Sprint 8

### Story 9.3: Document Dashboard Fallback Path

- User story: As a researcher, I want a notebook/static report fallback so that the project remains deliverable if dashboard polish is constrained.
- Description: Document how to inspect exported artifacts through notebook or static report outputs if Streamlit is unavailable.
- Acceptance criteria: README or docs describe Streamlit command, required export files, and fallback notebook/static report path; fallback does not require rerunning the full backtest.
- Technical notes: This supports the PRD boundary that dashboard should not block core MVP.
- Files/modules likely affected: `README.md`, `notebooks/03_backtest_review.ipynb`, `notebooks/04_report_figures.ipynb`, `docs/`.
- Testing requirements: Documentation review; optional notebook smoke run on fixture artifacts.
- Dependencies: Story 9.2.
- Suggested priority: P2
- Suggested sprint: Sprint 8

## Epic 10: Docker, GitHub Actions, and Reproducibility Support

- Epic title: Docker, GitHub Actions, and Reproducibility Support
- Epic goal: Add lightweight quality-control and reproducibility support without making Docker or CI an MVP blocker.
- Scope: GitHub Actions CI, pytest fixture-only runs, optional lint/format checks, Dockerfile, `.dockerignore`, optional `docker-compose.yml`, and CI test markers.
- Out of scope: Full historical backtests in CI, credentialed ENTSO-E/AWS tests, production deployment, and orchestration platforms.
- Key architecture modules/files: `.github/workflows/ci.yml`, `Dockerfile`, `.dockerignore`, optional `docker-compose.yml`, `tests/`.
- Dependencies: Epics 1 through 8 for meaningful tests; Docker can follow local CLI success.
- Acceptance criteria: CI installs dependencies and runs pytest on fixtures only, API/AWS tests are skipped or mocked, Docker can run tests and optionally Streamlit, local virtualenv remains supported.

### Story 10.1: Add GitHub Actions Fixture-Based CI

- User story: As a developer, I want CI checks so that regressions are caught without requiring credentials or large datasets.
- Description: Add `.github/workflows/ci.yml` to install dependencies and run pytest on fixture datasets.
- Acceptance criteria: CI runs on pull requests and pushes, installs project dependencies, runs `pytest`, does not require ENTSO-E or AWS credentials, does not run the full 2020-2025 backtest.
- Technical notes: Keep CI lightweight; use fixture data only.
- Files/modules likely affected: `.github/workflows/ci.yml`, `tests/`.
- Testing requirements: Workflow should pass with current fixture tests.
- Dependencies: Stories 1.2 and 1.5.
- Suggested priority: P1
- Suggested sprint: Sprint 2

### Story 10.2: Add Test Markers for External and Slow Tests

- User story: As a developer, I want API, AWS, and slow tests marked so that CI can skip them safely.
- Description: Define pytest markers for `external_api`, `aws`, and `slow`, and configure CI to exclude them by default.
- Acceptance criteria: Marker definitions exist, CI command excludes marked tests, API/AWS tests are skipped or mocked by default, documentation explains how to run them locally.
- Technical notes: This prevents accidental credential or full-backtest requirements in CI.
- Files/modules likely affected: `pyproject.toml`, `tests/`, `.github/workflows/ci.yml`, `README.md`.
- Testing requirements: Verify marker selection excludes marked tests.
- Dependencies: Story 10.1.
- Suggested priority: P1
- Suggested sprint: Sprint 2

### Story 10.3: Add Dockerfile for Reproducible Execution

- User story: As a researcher, I want a Docker image so that the pipeline can run in a reproducible environment after local setup works.
- Description: Add Dockerfile that installs dependencies and supports running tests and CLI commands.
- Acceptance criteria: Docker build succeeds, container can run pytest against fixtures, container can run a CLI config smoke command, local virtualenv workflow remains documented and primary.
- Technical notes: Docker must not become required for development.
- Files/modules likely affected: `Dockerfile`, `.dockerignore`, `README.md`.
- Testing requirements: Manual or CI-optional Docker build/test command documented.
- Dependencies: Story 1.4 and enough tests from earlier epics.
- Suggested priority: P2
- Suggested sprint: Sprint 8

### Story 10.4: Add Optional Docker Compose for Dashboard

- User story: As an analyst, I want optional Docker Compose support so that the Streamlit dashboard can be launched reproducibly.
- Description: Add optional `docker-compose.yml` for dashboard execution against mounted/exported artifacts.
- Acceptance criteria: Compose file can run the Streamlit dashboard, dashboard reads mounted `reports/dashboard_exports/`, compose is documented as optional, no AWS or API credentials are required.
- Technical notes: Only add after dashboard artifact contract is stable.
- Files/modules likely affected: `docker-compose.yml`, `src/energy_trading_pipeline/dashboard/app.py`, `README.md`.
- Testing requirements: Manual smoke command documented; optional CI check if cheap.
- Dependencies: Story 9.2 and Story 10.3.
- Suggested priority: P2
- Suggested sprint: Sprint 9

## Epic 11: Optional AWS Artifact Mirroring

- Epic title: Optional AWS Artifact Mirroring
- Epic goal: Demonstrate lightweight deployability by mirroring local artifacts to AWS without making cloud infrastructure a core dependency.
- Scope: Optional S3 artifact layout, Terraform skeleton, artifact mirror script, and optional Lambda/EventBridge/CloudWatch demonstration notes.
- Out of scope: SageMaker, Airflow, Kubernetes, Spark, always-on EC2, full cloud backtesting, and credential-dependent CI.
- Key architecture modules/files: `infrastructure/terraform/main.tf`, `variables.tf`, `outputs.tf`, optional `src/energy_trading_pipeline/utils/io.py`, optional `scripts/` if added.
- Dependencies: Core local artifact layout and evaluation outputs.
- Acceptance criteria: AWS support is optional, S3 mirrors local artifact layout, Terraform is documented, local reproducibility works without AWS credentials.

### Story 11.1: Define Optional S3 Artifact Layout and Terraform Skeleton

- User story: As a researcher, I want optional S3 storage defined so that cloud deployability can be demonstrated without changing local artifacts.
- Description: Add Terraform skeleton for an S3 bucket and document the mirrored artifact layout.
- Acceptance criteria: Terraform files define S3 bucket variables and outputs, README explains optional usage, local paths map clearly to S3 prefixes, no AWS resources are required for local runs.
- Technical notes: Keep IAM and resources minimal.
- Files/modules likely affected: `infrastructure/terraform/main.tf`, `variables.tf`, `outputs.tf`, `infrastructure/terraform/README.md`.
- Testing requirements: Terraform format/validation can be documented; do not require AWS in CI.
- Dependencies: Story 8.4.
- Suggested priority: P2
- Suggested sprint: Sprint 10

### Story 11.2: Implement Optional Artifact Mirror Utility

- User story: As a developer, I want an optional artifact mirroring utility so that selected local outputs can be copied to S3 when credentials are available.
- Description: Add utility or script that uploads selected report/log/model artifacts to configured S3 prefixes.
- Acceptance criteria: Utility is disabled unless AWS config is present, missing credentials produce a clear skip message, local runs are unaffected, mirrored paths match local artifact layout.
- Technical notes: Mark AWS tests separately and mock S3 interactions.
- Files/modules likely affected: `src/energy_trading_pipeline/utils/io.py`, optional `src/energy_trading_pipeline/utils/aws.py`, `configs/experiment.yaml`.
- Testing requirements: Unit tests use mocks and are marked to avoid real AWS calls.
- Dependencies: Story 11.1.
- Suggested priority: P2
- Suggested sprint: Sprint 10

### Story 11.3: Document Optional Lambda/EventBridge/CloudWatch Demonstration

- User story: As a researcher, I want optional AWS scheduling/logging documented so that deployability can be explained without overengineering.
- Description: Document how Lambda, EventBridge, and CloudWatch could support small ingestion or monitoring tasks after local success.
- Acceptance criteria: Documentation states this is optional, does not imply full cloud backtesting, excludes SageMaker/Airflow/Kubernetes/Spark, and identifies required credentials/permissions.
- Technical notes: This may remain documentation-only unless implementation time allows.
- Files/modules likely affected: `infrastructure/terraform/README.md`, `docs/optional_aws.md` if added.
- Testing requirements: Documentation review; no CI cloud execution.
- Dependencies: Story 11.2.
- Suggested priority: P2
- Suggested sprint: Sprint 10

## Epic 12: Documentation and Diagrams

- Epic title: Documentation and Diagrams
- Epic goal: Produce reproduction, architecture, OOAD/UML, data dictionary, and academic reporting documentation aligned with the implemented system.
- Scope: README, setup instructions, data source docs, config docs, leakage-prevention notes, retraining policy docs, diagrams, and final reproduction guide.
- Out of scope: New features, model architecture expansion, dashboard enhancements, and cloud implementation beyond optional documentation.
- Key architecture modules/files: `README.md`, `docs/`, `docs/diagrams/`, `configs/`, generated `reports/` outputs.
- Dependencies: Core implementation epics; some docs can start early and be finalized after implementation.
- Acceptance criteria: Another reader can reproduce the local experiment, understand architecture/module boundaries, inspect data/feature/model artifacts, and include diagrams/results in academic submission.

### Story 12.1: Write Setup and Reproduction README

- User story: As a researcher, I want setup and reproduction instructions so that the project can be rerun and evaluated by others.
- Description: Document local virtualenv setup, dependency installation, config files, fixture tests, CLI commands, and output locations.
- Acceptance criteria: README includes local setup, test command, config explanation, core pipeline command sequence, dashboard command, and notes that Docker/AWS are optional.
- Technical notes: Keep commands aligned with actual CLI behavior.
- Files/modules likely affected: `README.md`.
- Testing requirements: Documentation command review against implemented CLI.
- Dependencies: Stories 1.4, 6.4, 8.4, 9.2.
- Suggested priority: P1
- Suggested sprint: Sprint 8

### Story 12.2: Create Data Dictionary and Artifact Catalogue

- User story: As a researcher, I want a data dictionary and artifact catalogue so that columns and outputs are interpretable in the final report.
- Description: Document canonical columns, feature groups, artifact paths, metadata files, and report outputs.
- Acceptance criteria: Data dictionary includes `timestamp`, `price_de`, `price_fr`, `spread`, `prediction`, `actual`, `error`, `squared_error`, `absolute_error`, `rolling_rmse`, `strategy`, `model_version`; artifact catalogue maps raw, processed, feature, model, log, report, and dashboard paths.
- Technical notes: This supports academic traceability.
- Files/modules likely affected: `docs/data_dictionary.md`, `docs/artifacts.md`.
- Testing requirements: Documentation review against implemented schemas.
- Dependencies: Stories 4.4, 6.2, 8.4.
- Suggested priority: P1
- Suggested sprint: Sprint 8

### Story 12.3: Create Component, Artifact-Flow, and Optional Deployment Diagrams

- User story: As a researcher, I want diagrams so that the architecture and artifact flow can be included in academic documentation.
- Description: Create diagram source files for component architecture, artifact/data flow, and optional AWS deployment.
- Acceptance criteria: Component diagram shows key modules and boundaries, artifact-flow diagram shows raw-to-report flow, optional deployment diagram clearly marks AWS as optional, diagrams align with architecture document.
- Technical notes: Mermaid markdown is acceptable and easy to version.
- Files/modules likely affected: `docs/diagrams/component_diagram.md`, `docs/diagrams/artifact_flow_diagram.md`, `docs/diagrams/optional_deployment_diagram.md`.
- Testing requirements: Render or review Mermaid syntax where possible.
- Dependencies: Architecture approval and Stories 8.4, 11.1 for optional deployment detail.
- Suggested priority: P1
- Suggested sprint: Sprint 9

### Story 12.4: Finalize Academic Evaluation Documentation

- User story: As a researcher, I want the final evaluation documented so that results can support submission and defence.
- Description: Document evaluation period, data exclusions, chosen rolling RMSE threshold, rolling window, training window, model parameters, strategy comparison, and limitations.
- Acceptance criteria: Documentation states evaluation period, missing/incomplete data exclusions, threshold selection method, 7-day rolling RMSE default or final value, weekly fixed-schedule comparator, RMSE/MAE/retraining frequency results, and reproducibility steps.
- Technical notes: This story depends on actual experiment outputs and should be finalized late.
- Files/modules likely affected: `docs/evaluation.md`, `reports/tables/`, `reports/figures/`, `README.md`.
- Testing requirements: Cross-check documented metrics against generated artifacts.
- Dependencies: Epic 8 and final experiment run.
- Suggested priority: P1
- Suggested sprint: Sprint 10

### Story 12.5: Document CLI Command Catalogue

- User story: As a researcher, I want a CLI command catalogue so that setup, debug runs, full experiments, and dashboard launch are easy to reproduce.
- Description: Document the main CLI commands and distinguish fixture/debug commands from full historical experiment commands.
- Acceptance criteria: README or docs list the main CLI commands for setup, config validation, preprocessing, feature building, training, backtesting, evaluation, and dashboard launch; commands match the implemented CLI; full 2020-2025 backtest is documented separately from fixture/debug runs.
- Technical notes: This story should be updated after CLI commands stabilize and before final submission.
- Files/modules likely affected: `README.md`, `docs/cli_commands.md` if added.
- Testing requirements: Documentation review against implemented CLI behavior.
- Dependencies: Stories 1.4, 6.4, 8.4, 9.2.
- Suggested priority: P1
- Suggested sprint: Sprint 9

## Coverage Map

- FR-001 to FR-007: Epic 2, with support from Epic 1 and optional AWS boundaries in Epic 11.
- FR-008 to FR-014: Epic 3.
- FR-015 to FR-022: Epic 4.
- FR-023 to FR-027: Epic 5.
- FR-028 to FR-033: Epic 6.
- FR-034 to FR-041: Epic 7.
- FR-042 to FR-050: Epic 8.
- FR-051 to FR-056: Epic 9.
- FR-057 to FR-062: Epic 12.
- FR-063 to FR-073: Sequencing across Epics 1 through 12, with Sprint 1 reserved for foundation-only work and local data loading beginning in Sprint 2.
- NFR-001 reproducibility: Epics 1, 2, 5, 6, 8, 10, 12.
- NFR-002 traceability: Epics 2, 5, 6, 7, 8, 12.
- NFR-003 cost control: Epics 1 through 12 preserve local-first execution; Epic 11 remains optional.
- NFR-004 modularity: All epics follow the architecture module boundaries.
- NFR-005 configurability: Epics 1, 2, 5, 6, 7, 8.
- NFR-006 robustness: Epics 2, 3, 4, 10.
- NFR-007 academic defensibility: Epics 3, 4, 6, 7, 8, 12.
- NFR-008 maintainability: Epics 1, 10, 12.
