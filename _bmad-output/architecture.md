---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - _bmad-output/prds/prd-Energy-trading-pipeline-2026-06-15/prd.md
  - _bmad-output/prds/prd-Energy-trading-pipeline-2026-06-15/addendum.md
  - user-provided-architecture-constraints-2026-06-15
workflowType: 'architecture'
lastStep: 8
status: 'complete'
completedAt: '2026-06-15'
project_name: 'Energy-trading-pipeline'
user_name: 'Murage'
date: '2026-06-15'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**

The PRD defines 73 functional requirements across ingestion, preprocessing, feature engineering, model training, backtesting, retraining strategies, evaluation/reporting, dashboard/review interface, documentation, and implementation phasing.

Architecturally, the core system is a modular local data and ML evaluation pipeline, not a production trading platform. The architecture must make these flows explicit:

- Raw data acquisition from local files first, APIs second.
- Deterministic transformation from raw data to aligned hourly datasets.
- Leakage-safe feature generation.
- XGBoost model training and artifact persistence.
- Historical backtesting over a shared timeline and feature set.
- Three interchangeable retraining policies.
- Evaluation exports for academic evidence.
- Lightweight dashboard or report for inspection.

**Non-Functional Requirements:**

The architecture is driven by reproducibility, traceability, cost control, configurability, modularity, robustness to missing optional variables, academic defensibility, and maintainability.

The strongest architectural requirements are:

- Reproducible reruns from saved data, configuration, and artifacts.
- Traceable links between datasets, features, model versions, forecasts, errors, retraining events, and metrics.
- Leakage prevention in feature generation, forecasting, and retraining decisions.
- Local-first execution without cloud dependency.
- Config-driven experiment execution.
- Optional external API and AWS adapters that do not contaminate the core local workflow.

**Scale & Complexity:**

- Primary domain: local-first ML/DataOps research pipeline with a lightweight web/reporting interface.
- Complexity level: medium.
- Estimated architectural components: 10-12 core modules.

The project is not enterprise-scale, but it has meaningful data and experiment-governance complexity because the academic claim depends on controlled comparisons and reproducible evidence.

### Technical Constraints & Dependencies

Known constraints:

- Python 3.11+ is the main implementation language.
- XGBoost is the only forecasting model.
- Rolling RMSE is the primary retraining trigger.
- PSI may be logged only as a secondary diagnostic.
- Weekly retraining is the default fixed-schedule comparator.
- 7-day rolling RMSE is the default monitoring window.
- Rolling RMSE threshold is configurable and initially derived from validation-period performance.
- Processed data should use Parquet.
- Configuration should use YAML or TOML.
- Streamlit is preferred for dashboard delivery, with notebook/static report fallback.
- API ingestion is optional and modular.
- AWS is optional and limited to S3, Lambda/EventBridge, CloudWatch, and Terraform after local success.

Explicit exclusions:

- No SageMaker.
- No Airflow.
- No Kubernetes.
- No Spark.
- No always-on EC2 by default.
- No live trading.
- No P&L simulation.
- No intraday forecasting.
- No multi-model architecture comparison.

### Cross-Cutting Concerns Identified

- Reproducibility: config, data snapshots, model artifacts, metrics, and logs must be persisted consistently.
- Traceability: model versions, training windows, feature sets, and retraining events need stable identifiers.
- Leakage prevention: rolling and lagged feature generation must only use information available at prediction time.
- Experiment comparability: all strategies must share the same dataset, feature set, model configuration, and evaluation period.
- Configurability: date ranges, file paths, feature settings, model parameters, retraining interval, rolling RMSE window, and threshold must live in config.
- Missing-data robustness: optional weather/grid variables may be absent without breaking the entire pipeline.
- Cost control: local execution is the default architecture path; cloud is a demonstration extension only.
- Academic reporting: outputs must produce tables, plots, diagrams, and documentation suitable for final submission and defence.

## Starter Template Evaluation

### Primary Technology Domain

The primary technology domain is a local-first Python ML/DataOps research pipeline with a lightweight dashboard/reporting interface.

This is not a conventional web application, mobile app, full-stack app, or API backend. The dashboard is secondary to the reproducible evaluation pipeline.

### Starter Options Considered

**Generic web/full-stack starters: Rejected**

Examples: Next.js, Vite, Remix, T3, RedwoodJS.

Rationale: These optimize for browser application development and would incorrectly make UI architecture central. The PRD states that dashboard work must not block the MVP.

**Enterprise data/ML platforms: Rejected**

Examples: SageMaker projects, Airflow DAG templates, Spark project templates, Kubernetes-based ML stacks.

Rationale: These conflict with the project’s local-first, cost-conscious, academic prototype constraints.

**Custom Python research-pipeline skeleton: Selected**

Rationale: The architecture needs explicit control over ingestion, preprocessing, feature generation, backtesting, retraining policies, evaluation artifacts, and reproducibility. A custom skeleton is smaller, clearer, and better aligned with the academic evaluation.

### Selected Starter: Custom Python Research Pipeline Skeleton

**Rationale for Selection:**

The selected foundation is a custom Python package-style repository using `src/` layout, configuration files, local data folders, notebook/report support, and optional dashboard/infrastructure folders.

This gives the project:

- Local-first experiment execution.
- Clear module boundaries.
- First-class local CSV/Parquet loading.
- Optional API adapters.
- Reproducible configuration-driven backtests.
- Lightweight dashboard integration without making UI the core system.
- Optional AWS demonstration without cloud dependency.

**Initialization Command:**

No external starter CLI is required. Initialize the repository using standard Python project files and the agreed repository structure.

```bash
python3.11 -m venv .venv
```

Dependency and packaging setup should be captured in `pyproject.toml` and/or `requirements.txt`.

**Architectural Decisions Provided by Starter:**

**Language & Runtime:**

Python 3.11+.

**Core Libraries:**

pandas, NumPy, scikit-learn, XGBoost, Matplotlib/Plotly, PyArrow for Parquet support, Streamlit for dashboard delivery.

**Configuration:**

YAML or TOML configuration for data paths, date ranges, feature settings, model parameters, backtesting windows, retraining intervals, rolling RMSE windows, and thresholds.

**Build Tooling:**

Lightweight local Python environment. No managed ML platform or distributed execution layer is required for MVP.

**Testing Framework:**

Python unit and integration tests should validate data loading, preprocessing, feature leakage prevention, metrics, retraining policy behavior, and backtesting outputs.

**Code Organization:**

Use a `src/` package layout with separate modules for config, ingestion, preprocessing, features, models, backtesting, monitoring, retraining, evaluation, dashboard, and utilities.

**Development Experience:**

Local-first commands should support small debug runs before full 2020-2025 backtests. Notebooks may be used for exploration, but reusable logic belongs in `src/`.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**

- Configuration format: YAML experiment configuration.
- Artifact registry: filesystem-based artifacts with JSON/YAML metadata.
- Backtest execution: Python CLI as the primary execution path, with optional notebooks as wrappers.
- Data validation: lightweight custom validation checks for MVP.
- Testing framework: pytest with small fixture datasets.
- Dashboard contract: dashboard reads exported artifacts only.

**Important Decisions (Shape Architecture):**

- Optional AWS layout mirrors the local artifact layout in S3.
- Reusable logic belongs in `src/`; notebooks are exploratory or presentation wrappers.
- API ingestion remains modular and optional; local CSV/Parquet loading is the default path.

**Deferred Decisions (Post-MVP):**

- MLflow or a database-backed experiment registry is deferred because the project needs moderate traceability, not enterprise experiment management.
- Pandera or Great Expectations is deferred unless validation complexity grows beyond lightweight custom checks.
- Cloud scheduling and logging are deferred until the local pipeline, model training, backtesting, retraining policies, and evaluation outputs work.

### Data Architecture

**Storage format:**

Parquet is the preferred format for processed, aligned, feature, forecast, metric, and event artifacts. CSV may be accepted for raw/local input and lightweight exports where readability matters.

**Artifact registry:**

Use a filesystem-based registry. Each experiment run writes artifacts into a run-specific folder and includes metadata files in JSON or YAML describing configuration, data range, feature set, model version, training window, strategy, metrics, and generated outputs.

**Validation strategy:**

Use lightweight custom validation checks for MVP:

- Required columns exist.
- Timestamps are parseable and hourly after alignment.
- Duplicate timestamps are detected.
- Missing-value counts are reported.
- Target spread is present after preprocessing.
- Feature generation does not use future values.
- Backtest periods are ordered correctly.

Pandera or Great Expectations may be introduced later only if custom validation becomes insufficient.

### Authentication & Security

No application authentication is required for MVP because the system is a local research pipeline and dashboard.

Security concerns are limited to:

- Keeping API credentials out of source control.
- Loading secrets from `.env` or local environment variables.
- Providing `.env.example` without real credentials.
- Avoiding committed raw credentials, tokens, or cloud secrets.

If AWS is added, IAM permissions should be least-privilege for the narrow prototype tasks: S3 object access, Lambda execution, EventBridge scheduling, and CloudWatch logging.

### API & Communication Patterns

The core pipeline is not designed as a service API. Communication between modules should happen through Python function calls and explicit artifact files.

External data APIs are adapter modules:

- ENTSO-E adapter for optional market/grid/load/generation ingestion.
- Open-Meteo adapter for optional weather ingestion.

Adapters must write raw cached outputs to disk so downstream steps can run without repeated API calls.

Errors should be logged with enough context to identify data source, request parameters, date range, and failure reason.

### Frontend Architecture

The dashboard is a lightweight review interface, not the core application.

Streamlit is preferred. A notebook dashboard or static report remains an acceptable fallback.

The dashboard must read exported artifacts only:

- Forecasts.
- Actuals.
- Errors.
- Rolling RMSE.
- Metrics summaries.
- Retraining events.
- Model version metadata.

The dashboard should not run ingestion, training, or backtesting by default. This keeps UI work from mutating experiment state or coupling tightly to pipeline internals.

### Infrastructure & Deployment

Local execution is the primary deployment model.

Primary execution path:

- Python CLI commands invoke pipeline stages and full experiments.
- Notebooks may call CLI commands or import stable pipeline functions for exploration and reporting.

Optional AWS prototype:

- S3 mirrors the local artifact layout for raw data, processed data, features, model artifacts, forecasts, actuals, events, metrics, plots, and logs.
- Lambda/EventBridge may run small ingestion or monitoring tasks only after local success.
- CloudWatch may capture lightweight logs.
- Terraform may define the optional cloud resources.

AWS must not become required for local reproducibility.

### Decision Impact Analysis

**Implementation Sequence:**

1. Define repository structure, `pyproject.toml` and/or `requirements.txt`, `.env.example`, and YAML config schema.
2. Implement config loading and path resolution.
3. Implement local CSV/Parquet data loading.
4. Implement raw and processed artifact layout.
5. Implement preprocessing, alignment, spread calculation, and feature generation.
6. Implement model training and filesystem model registry metadata.
7. Implement CLI-driven backtesting.
8. Implement retraining policies and event logging.
9. Implement evaluation exports and plots.
10. Implement Streamlit or fallback report interface reading exported artifacts.
11. Add optional AWS artifact mirroring and lightweight scheduled tasks only if needed.

**Cross-Component Dependencies:**

- Dashboard depends on exported evaluation artifacts, not pipeline internals.
- Backtesting depends on finalized feature datasets and configuration.
- Retraining policies depend on forecast/error logs and rolling RMSE calculations.
- Model registry depends on trainer output and run metadata.
- Optional AWS depends on local artifact layout remaining stable.

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:**

The architecture identifies 8 conflict areas where AI agents could make incompatible choices:

- Python naming.
- File and directory naming.
- Timestamp handling.
- Artifact layout.
- Configuration schema.
- Dataframe schema conventions.
- Logging and metadata formats.
- Dashboard-to-pipeline boundaries.

### Naming Patterns

**Code Naming Conventions:**

- Python modules and files use `snake_case`.
- Python functions and variables use `snake_case`.
- Python classes use `PascalCase`.
- Constants use `UPPER_SNAKE_CASE`.
- Strategy names use stable lowercase identifiers: `no_retraining`, `fixed_schedule`, `performance_triggered`.

Examples:

- Good: `load_local_prices`, `FeatureDataset`, `ROLLING_RMSE_WINDOW_DAYS`.
- Avoid: `loadLocalPrices`, `feature-dataset.py`, `PerformanceTriggeredStrategy` as an artifact identifier.

**Data Column Naming Conventions:**

All dataframe columns use `snake_case`.

Required canonical columns:

- `timestamp`
- `price_de`
- `price_fr`
- `spread`
- `prediction`
- `actual`
- `error`
- `squared_error`
- `absolute_error`
- `rolling_rmse`
- `strategy`
- `model_version`

**File and Directory Naming:**

- Directories use `snake_case`.
- Experiment run folders use timestamped IDs: `run_YYYYMMDD_HHMMSS`.
- Model versions use stable IDs: `model_YYYYMMDD_HHMMSS`.
- Strategy-specific outputs use the strategy identifier in the path or filename.

### Structure Patterns

**Project Organization:**

Reusable logic belongs in `src/`.

Notebooks may be used for exploration, reporting, or demonstration, but notebooks must not contain core pipeline logic that is absent from `src/`.

Tests live under `tests/`.

Configuration files live under `configs/`.

Generated artifacts live under `data/`, `models/`, `reports/`, or `logs/`, not under `src/`.

### Format Patterns

**Configuration Format:**

YAML is the canonical experiment configuration format.

Config files should include:

- `data`
- `dates`
- `features`
- `model`
- `backtest`
- `retraining`
- `evaluation`
- `artifacts`

**Data Exchange Formats:**

- Processed datasets, feature datasets, forecasts, metrics, and retraining events should be written as Parquet where practical.
- JSON or YAML should be used for metadata.
- CSV may be exported for academic readability but should not be the canonical internal format if Parquet is available.
- Timestamps should be stored in ISO 8601-compatible format and normalized consistently before modelling.

**Metadata Format:**

Each experiment run should include a metadata file recording:

- Run ID.
- Config file path.
- Data date range.
- Feature columns.
- Target column.
- Model parameters.
- Strategy.
- Training windows.
- Evaluation window.
- Metrics.
- Artifact paths.

### Communication Patterns

**Pipeline Communication:**

Pipeline stages communicate through explicit function inputs/outputs and persisted artifacts.

No stage should depend on hidden global state.

**Dashboard Communication:**

The dashboard reads exported artifacts only. It must not trigger ingestion, training, backtesting, or retraining by default.

### Process Patterns

**Error Handling Patterns:**

- Validation errors should fail fast with clear messages.
- Missing optional variables should warn and continue with documented reduced features.
- Missing required variables should fail.
- API failures should be logged and should not prevent local cached-file runs.

**Logging Patterns:**

Logs should include:

- Stage name.
- Run ID.
- Date range.
- Strategy where applicable.
- Model version where applicable.
- Error or warning details.

**Leakage Prevention Patterns:**

- Lag features must be shifted before use.
- Rolling features must not include the prediction target timestamp unless explicitly valid for the forecast horizon.
- Retraining decisions must use only errors available at the decision time.
- Backtest splits must preserve chronological order.

### Enforcement Guidelines

**All AI Agents MUST:**

- Keep reusable logic in `src/`.
- Use `snake_case` for Python files, functions, variables, dataframe columns, and artifact identifiers.
- Use the canonical strategy identifiers: `no_retraining`, `fixed_schedule`, `performance_triggered`.
- Treat local CSV/Parquet loading as first-class.
- Keep API ingestion optional.
- Keep dashboard reads artifact-only.
- Preserve chronological ordering in all training, validation, forecasting, and retraining logic.
- Write run metadata for every experiment.

**Anti-Patterns:**

- Putting core pipeline logic only in notebooks.
- Making AWS required for local reproducibility.
- Letting the dashboard mutate model or backtest state.
- Comparing strategies with different datasets, features, model parameters, or evaluation windows.
- Computing rolling features or rolling RMSE with future values.
- Introducing alternative model families.

## Project Structure & Boundaries

### Complete Project Directory Structure

```text
Energy-trading-pipeline/
  README.md
  pyproject.toml
  requirements.txt
  .env.example
  .gitignore

  configs/
    experiment.yaml
    local_paths.yaml
    model_params.yaml

  data/
    raw/
      entsoe/
        prices/
        load/
        generation/
      open_meteo/
        weather/
    processed/
      aligned_hourly/
    features/
      feature_dataset.parquet

  models/
    registry/
      models_index.yaml
    artifacts/
      model_YYYYMMDD_HHMMSS/
        model.json
        metadata.yaml

  reports/
    figures/
      forecasts_vs_actuals/
      rolling_rmse/
      retraining_events/
      strategy_comparison/
    tables/
      metrics_summary.csv
      retraining_summary.csv
    dashboard_exports/
      forecasts.parquet
      metrics.parquet
      retraining_events.parquet
      model_versions.parquet

  docs/
    diagrams/
      component_diagram.md
      artifact_flow_diagram.md
      optional_deployment_diagram.md

  logs/
    runs/
      run_YYYYMMDD_HHMMSS/
        run_metadata.yaml
        ingestion_log.jsonl
        preprocessing_log.jsonl
        backtest_log.jsonl
        retraining_events.parquet
        metrics.parquet

  notebooks/
    01_data_exploration.ipynb
    02_feature_review.ipynb
    03_backtest_review.ipynb
    04_report_figures.ipynb

  src/
    energy_trading_pipeline/
      __init__.py

      cli.py

      config/
        __init__.py
        loader.py
        schema.py
        paths.py

      data_ingestion/
        __init__.py
        local_loader.py
        entsoe_client.py
        open_meteo_client.py
        cache.py

      preprocessing/
        __init__.py
        timestamps.py
        cleaning.py
        alignment.py
        spread.py
        validation.py

      features/
        __init__.py
        lag_features.py
        rolling_features.py
        calendar_features.py
        weather_features.py
        grid_features.py
        dataset_builder.py

      models/
        __init__.py
        xgboost_model.py
        trainer.py
        registry.py

      backtesting/
        __init__.py
        splitter.py
        backtest_runner.py
        forecast_log.py

      monitoring/
        __init__.py
        metrics.py
        rolling_rmse.py
        psi.py

      retraining/
        __init__.py
        policies.py
        no_retraining.py
        fixed_schedule.py
        performance_triggered.py
        events.py

      evaluation/
        __init__.py
        strategy_comparison.py
        plots.py
        exports.py

      dashboard/
        __init__.py
        app.py
        data_loader.py
        charts.py

      utils/
        __init__.py
        logging.py
        time.py
        io.py

  infrastructure/
    terraform/
      main.tf
      variables.tf
      outputs.tf
      README.md

  tests/
    fixtures/
      sample_prices_de.csv
      sample_prices_fr.csv
      sample_weather.csv
      sample_config.yaml

    unit/
      test_config_loader.py
      test_local_loader.py
      test_timestamp_alignment.py
      test_spread_calculation.py
      test_lag_features.py
      test_rolling_features.py
      test_metrics.py
      test_retraining_policies.py

    integration/
      test_feature_dataset_build.py
      test_backtest_runner_small_range.py
      test_strategy_comparison.py
```

### Architectural Boundaries

**API Boundaries:**

There is no internal service API in the MVP.

External APIs are isolated behind adapter modules:

- `data_ingestion/entsoe_client.py`
- `data_ingestion/open_meteo_client.py`

The rest of the pipeline must be able to run from local cached files without calling these clients.

**Component Boundaries:**

- `config/` owns configuration loading, validation, and path resolution.
- `data_ingestion/` owns local and optional API data retrieval.
- `preprocessing/` owns timestamp normalization, cleaning, alignment, and spread calculation.
- `features/` owns feature dataset generation.
- `models/` owns XGBoost training, prediction wrapper, and model registry metadata.
- `backtesting/` owns chronological evaluation execution and forecast logging.
- `monitoring/` owns RMSE, MAE, rolling RMSE, and optional PSI calculations.
- `retraining/` owns retraining policy decisions and event records.
- `evaluation/` owns strategy comparison outputs, plots, and report exports.
- `dashboard/` owns artifact-only visualization.
- `infrastructure/` owns optional AWS demonstration resources.

**Service Boundaries:**

Pipeline modules communicate by explicit function calls and persisted artifacts. No hidden global state.

**Data Boundaries:**

- Raw data is immutable once cached.
- Processed data is generated from raw data.
- Feature data is generated from processed data.
- Model artifacts are generated from feature data and config.
- Forecast, event, metric, and plot artifacts are generated from backtesting outputs.
- Dashboard reads only from `reports/dashboard_exports/` and related exported artifacts.

### Requirements to Structure Mapping

**Data Ingestion FR-001 to FR-007**

- `src/energy_trading_pipeline/data_ingestion/`
- `data/raw/`
- `logs/runs/*/ingestion_log.jsonl`

**Preprocessing FR-008 to FR-014**

- `src/energy_trading_pipeline/preprocessing/`
- `data/processed/aligned_hourly/`
- `tests/unit/test_timestamp_alignment.py`
- `tests/unit/test_spread_calculation.py`

**Feature Engineering FR-015 to FR-022**

- `src/energy_trading_pipeline/features/`
- `data/features/`
- `tests/unit/test_lag_features.py`
- `tests/unit/test_rolling_features.py`

**Forecast Model FR-023 to FR-027**

- `src/energy_trading_pipeline/models/`
- `models/artifacts/`
- `models/registry/`

**Backtesting FR-028 to FR-033**

- `src/energy_trading_pipeline/backtesting/`
- `logs/runs/*/backtest_log.jsonl`
- `tests/integration/test_backtest_runner_small_range.py`

**Retraining FR-034 to FR-041**

- `src/energy_trading_pipeline/retraining/`
- `src/energy_trading_pipeline/monitoring/rolling_rmse.py`
- `logs/runs/*/retraining_events.parquet`
- `tests/unit/test_retraining_policies.py`

**Evaluation and Reporting FR-042 to FR-050**

- `src/energy_trading_pipeline/evaluation/`
- `reports/tables/`
- `reports/figures/`
- `reports/dashboard_exports/`

**Dashboard FR-051 to FR-056**

- `src/energy_trading_pipeline/dashboard/`
- `reports/dashboard_exports/`

**Documentation FR-057 to FR-062**

- `README.md`
- `docs/`
- Architecture document
- UML diagrams in `docs/diagrams/` if added

**Implementation Phases FR-063 to FR-073**

- Reflected by the staged implementation sequence and directory boundaries.

### Integration Points

**Internal Communication:**

- CLI loads YAML config.
- CLI invokes pipeline stages.
- Pipeline stages pass dataframes and metadata explicitly.
- Long-lived artifacts are persisted to agreed directories.
- Dashboard reads exported Parquet/CSV artifacts.

**External Integrations:**

- ENTSO-E API through `entsoe_client.py`.
- Open-Meteo API through `open_meteo_client.py`.
- Optional AWS S3/Lambda/EventBridge/CloudWatch through `infrastructure/terraform/`.

**Data Flow:**

1. Local/API raw data to `data/raw/`.
2. Cleaned aligned hourly data to `data/processed/aligned_hourly/`.
3. Feature dataset to `data/features/`.
4. XGBoost model artifacts to `models/artifacts/`.
5. Backtest forecasts, metrics, and retraining events to `logs/runs/`.
6. Report-ready outputs to `reports/tables/`, `reports/figures/`, and `reports/dashboard_exports/`.
7. Dashboard reads exported report artifacts.

### File Organization Patterns

**Configuration Files:**

- `configs/experiment.yaml`: main experiment configuration.
- `configs/local_paths.yaml`: local paths and artifact locations.
- `configs/model_params.yaml`: XGBoost parameters.

**Source Organization:**

All reusable logic lives under `src/energy_trading_pipeline/`.

**Test Organization:**

- `tests/unit/` for deterministic small-function tests.
- `tests/integration/` for small end-to-end pipeline slices.
- `tests/fixtures/` for sample local datasets.

**Asset Organization:**

- Generated figures live under `reports/figures/`.
- Generated tables live under `reports/tables/`.
- Dashboard-ready artifacts live under `reports/dashboard_exports/`.

### Development Workflow Integration

**Development Server Structure:**

The main pipeline is CLI-driven. Streamlit runs separately and reads exported artifacts.

**Build Process Structure:**

No complex build process is required. Python packaging and dependency installation are handled through `pyproject.toml` and/or `requirements.txt`.

**Deployment Structure:**

Local execution is the primary deployment model. Optional cloud demonstration mirrors the local artifact layout to S3 and defines resources in Terraform.

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**

The architecture decisions are compatible:

- Python 3.11+, pandas, NumPy, scikit-learn, XGBoost, PyArrow, Matplotlib/Plotly, and Streamlit work together as a coherent local ML/DataOps stack.
- YAML configuration aligns with the local-first CLI execution model.
- Filesystem metadata aligns with the moderate traceability needs of an academic prototype.
- Streamlit artifact-only reads align with the decision that dashboard work must not block or mutate the core MVP.
- Optional AWS mirroring aligns with the cost-conscious deployability-demonstration boundary.
- Docker and GitHub Actions support reproducibility and quality control without becoming MVP blockers or replacing the local Python CLI path.

No contradictory decisions were found.

**Pattern Consistency:**

The implementation patterns support the architecture:

- `snake_case` naming fits Python, dataframe columns, artifact identifiers, and strategy names.
- Canonical strategy identifiers prevent inconsistent output naming.
- Artifact-only dashboard communication preserves pipeline boundaries.
- Leakage-prevention rules directly support the research validity requirement.
- Run metadata requirements support reproducibility and traceability.

**Structure Alignment:**

The project structure supports all architectural decisions:

- `src/energy_trading_pipeline/` separates reusable modules.
- `configs/` supports config-driven experiments.
- `data/`, `models/`, `logs/`, and `reports/` separate artifact types clearly.
- `tests/fixtures/`, `tests/unit/`, and `tests/integration/` support local verification.
- `infrastructure/terraform/` keeps optional AWS work separate from the core local system.

### Requirements Coverage Validation ✅

**Feature Coverage:**

All major PRD feature areas are architecturally supported:

- Data ingestion.
- Preprocessing and alignment.
- Feature engineering.
- XGBoost model training.
- Backtesting.
- Retraining strategies.
- Monitoring metrics.
- Evaluation exports.
- Dashboard/review interface.
- Documentation and academic artifacts.
- Optional AWS prototype.
- Lightweight Docker support for reproducible execution.
- Lightweight GitHub Actions CI for tests and optional formatting/linting checks.

**Functional Requirements Coverage:**

FR-001 to FR-073 are supported by the module layout, artifact structure, and implementation patterns.

Coverage examples:

- FR-001 to FR-007: `data_ingestion/`, `data/raw/`, ingestion logs.
- FR-008 to FR-014: `preprocessing/`, aligned processed data.
- FR-015 to FR-022: `features/`, feature dataset artifacts.
- FR-023 to FR-027: `models/`, model artifacts and registry metadata.
- FR-028 to FR-033: `backtesting/`, chronological runner and forecast logs.
- FR-034 to FR-041: `retraining/`, `monitoring/rolling_rmse.py`, retraining event artifacts.
- FR-042 to FR-050: `evaluation/`, reports tables and figures.
- FR-051 to FR-056: `dashboard/`, artifact-only dashboard exports.
- FR-057 to FR-062: README, docs, architecture document, UML/diagram path.
- FR-063 to FR-073: reflected in implementation sequence and module boundaries.

**Non-Functional Requirements Coverage:**

- Reproducibility: handled through config, artifacts, and run metadata.
- Traceability: handled through model registry, run folders, event logs, and metadata.
- Cost control: local-first structure and optional cloud boundary.
- Reproducibility and maintainability: Docker and CI provide support paths while local virtualenv execution remains primary.
- Modularity: module boundaries are explicit.
- Configurability: YAML config schema is central.
- Robustness: optional variables can warn and continue.
- Academic defensibility: leakage prevention and strategy comparability are explicit.
- Maintainability: `src/` package layout and tests support inspection.

### Implementation Readiness Validation ✅

**Decision Completeness:**

Critical implementation decisions are documented. Some exact dependency versions are intentionally not pinned in the architecture; they should be pinned during environment setup in `requirements.txt` or `pyproject.toml`.

**Structure Completeness:**

The project structure is complete enough for implementation agents to create files and modules consistently.

**Pattern Completeness:**

Patterns cover naming, structure, formats, communication, error handling, logging, leakage prevention, dashboard boundaries, and anti-patterns.

### Gap Analysis Results

**Critical Gaps:**

None.

**Important Gaps:**

- Exact dependency versions still need to be pinned during setup.
- The architecture should explicitly state the default timezone normalization policy before implementation. Recommendation: normalize modelling timestamps to UTC while preserving original source timezone metadata where useful.
- The config schema is described conceptually but not yet shown as an example YAML.

**Nice-to-Have Gaps:**

- Add a sample `experiment.yaml` later.
- Add a short CLI command catalogue later.
- Add a component diagram and artifact-flow diagram for academic documentation.
- Add a data dictionary for canonical dataframe columns.

### Validation Issues Addressed

No blocking issues were found.

The project tree was updated to explicitly include `docs/diagrams/` for component, artifact-flow, and optional deployment diagrams.

### Architecture Completeness Checklist

**Requirements Analysis**

- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**Architectural Decisions**

- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed

**Implementation Patterns**

- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented

**Project Structure**

- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High

**Key Strengths:**

- Architecture is tightly aligned to the approved PRD.
- Local-first and evaluation-first constraints are preserved.
- Dashboard and AWS are correctly isolated from MVP-critical work.
- Leakage prevention and strategy comparability are treated as architectural concerns, not just implementation details.
- Module boundaries map clearly to PRD requirements.

**Areas for Future Enhancement:**

- Pin dependency versions.
- Add sample config files.
- Add UML/component/deployment diagrams.
- Add a data dictionary.
- Add optional AWS artifact-mirroring design once local pipeline works.
- Add Docker after the local Python setup works.

### Implementation Handoff

**AI Agent Guidelines:**

- Follow all architectural decisions exactly as documented.
- Use implementation patterns consistently across all components.
- Respect project structure and boundaries.
- Refer to this document for all architectural questions.
- Do not introduce cloud or dashboard work before the core local backtesting pipeline is working.
- Do not introduce alternative model families.

**First Implementation Priority:**

Create the repository skeleton, configuration files, package metadata, `.env.example`, local fixture data structure, and config loader.

## Architecture Update: Docker and GitHub Actions Support

### Decision Summary

Docker and GitHub Actions are included as lightweight support for reproducibility, maintainability, and quality control. They are not MVP blockers and must not replace the local-first Python CLI execution path.

### Docker Boundary

Docker should be added after the local Python setup works.

Docker responsibilities:

- Provide a reproducible execution environment for the pipeline and dashboard.
- Support running tests.
- Support running CLI commands.
- Optionally support running the Streamlit dashboard.

Docker constraints:

- The project must still run locally with a normal Python virtual environment.
- Docker must not become required for development or evaluation.
- Docker must not introduce enterprise orchestration requirements.

Docker files:

- `Dockerfile`
- `.dockerignore`
- Optional `docker-compose.yml`

### GitHub Actions Boundary

GitHub Actions should be added early for CI quality checks.

CI responsibilities:

- Install dependencies.
- Run `pytest`.
- Optionally run formatting and linting checks.
- Use only small fixture datasets.

CI constraints:

- CI must not run the full 2020-2025 backtest.
- CI must not require ENTSO-E credentials.
- CI must not require AWS credentials.
- API and AWS-related tests must be skipped, mocked, or marked separately in CI.

GitHub Actions files:

- `.github/workflows/ci.yml`

### Updated Project Structure Additions

```text
Energy-trading-pipeline/
  Dockerfile
  docker-compose.yml
  .dockerignore

  .github/
    workflows/
      ci.yml
```

### Updated Implementation Sequence

Docker and GitHub Actions fit into the implementation sequence as follows:

1. Create repository skeleton, Python environment, package metadata, and configuration files.
2. Add GitHub Actions CI with dependency installation and fixture-based `pytest` checks.
3. Implement local-first pipeline modules and tests.
4. Add Docker after the local Python setup and CLI path work.
5. Keep Docker, CI, and optional AWS separate from the core research pipeline.

### Updated AI Agent Guidelines

- Do not make Docker required for local development.
- Do not make GitHub Actions depend on credentials or full historical datasets.
- Do not run the full 2020-2025 backtest in CI.
- Mock or skip API and AWS tests in CI.
- Keep the local Python CLI as the main execution path.
