# Epic 6 Context: Backtesting Engine and Forecast Logging

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Provide a reproducible historical forecasting simulation that advances chronologically through a configurable evaluation period and records forecasts, observed spreads, errors, and model identity consistently. This establishes the execution foundation for comparing retraining strategies fairly and producing auditable evidence about forecast accuracy and retraining frequency in a local-first academic research pipeline.

## Stories

- Story 6.1: Implement Chronological Backtest Splitter
- Story 6.2: Implement Forecast Log Schema
- Story 6.3: Implement Single-Strategy Backtest Runner
- Story 6.4: Add Backtesting CLI Command

## Requirements & Constraints

- Forecast the hourly German-French day-ahead spread, defined as `price_de - price_fr`, using XGBoost only. The experiment evaluates forecasting and model maintenance; trading, P&L simulation, and alternative model families are outside scope.
- Support configuration-controlled evaluation dates and small development/debug runs. The target historical range is 2020–2025, subject to data completeness; document shortened ranges and exclusions rather than requiring the full dataset for development.
- Preserve chronological order across training, validation, forecasting, and eventual retraining. Training rows must precede validation/evaluation rows; overlapping or otherwise invalid windows must fail clearly. Future information must never enter model fitting or forecast inputs.
- Information availability governs simulation: compare forecasts with actual spreads only once those actuals are available, and expose only already-available errors to retraining decisions. Shifted lag and rolling features must remain leakage-safe for the forecast horizon.
- All strategies must share the dataset, feature set, tuned model configuration, and evaluation timeline. Use the stable identifiers `no_retraining`, `fixed_schedule`, and `performance_triggered` throughout persisted outputs.
- Epic completion means a configurable chronological backtest can run on small local fixtures, produce traceable predictions and actuals, and demonstrate leakage prevention. Verification should cover temporal boundaries, invalid windows, consistent forecast errors, output ordering, and the CLI execution path using pytest. CI must use small fixtures without external credentials or full historical backtests.
- Keep this epic focused on execution, forecast logging, and policy hooks. Full retraining policies and event logging follow in Epic 7; strategy comparison, plots, and report exports follow in Epic 8. Dashboard and AWS work do not belong in this epic.

## Technical Decisions

- Keep reusable execution logic in the Python package. `backtesting/` owns chronological evaluation and forecast logging; `models/` owns XGBoost fitting, prediction, and filesystem model registration. `monitoring/` owns performance calculations, while `retraining/` owns policy decisions. Pass dataframes, configuration, and metadata through explicit inputs/outputs and persisted artifacts; avoid hidden global state.
- Consume the finalized feature dataset and its recorded feature/target selection. Use the upstream consistently normalized hourly timestamps; UTC is the recommended modelling normalization, with source timezone metadata retained where useful. Timestamp normalization and cleaning remain preprocessing responsibilities.
- YAML configuration controls paths, date ranges, model settings, backtesting windows, and eventual retraining settings. Exact historical train/validation/test dates remain undecided. The planning material also does not prescribe a precise forecast issuance schedule, endpoint-inclusivity convention, or rolling-versus-expanding training-window policy; make these assumptions explicit in story-level design rather than treating an invented default as approved.
- Orchestrate training or model loading and prediction through a supplied policy hook. Support a static model baseline that trains once and holds the model fixed; keep strategy internals out of the runner. Later policy integration uses weekly fixed scheduling by default and a configurable 7-day rolling RMSE monitor with a configurable threshold. PSI is diagnostic only and must not drive retraining.
- Forecast records must distinguish forecast issuance time from target delivery time. Preserve canonical target `timestamp`, using `forecast_timestamp` for issuance clarity, together with `prediction`, `actual`, `error`, `squared_error`, `absolute_error`, `strategy`, and `model_version`. Error calculation must be consistent across strategies; the planning material does not specify its signed convention. Use `snake_case` columns and artifact identifiers.
- Prefer Parquet for forecast artifacts, with CSV supported for readable exports. Store run outputs under `logs/runs/run_YYYYMMDD_HHMMSS/`, including `run_metadata.yaml` and `backtest_log.jsonl`. Use JSON/YAML metadata and filesystem model versions named `model_YYYYMMDD_HHMMSS`; generated artifacts must remain outside `src/`.
- Run metadata must trace configuration path, data range, feature columns, target, model parameters, strategy, training windows, evaluation window, metrics, and artifact paths to the run ID. Operational logs should identify stage, run, date range, strategy/model where relevant, and warning or failure details. Missing required inputs fail clearly; absent optional variables permit a documented reduced feature set.

## UX & Interaction Patterns

- The Python CLI is the primary research interface: accept a configuration path, support small-range runs, and persist inspectable run outputs. Local CSV/Parquet and saved model artifacts must support reproducible execution without API or AWS credentials. Notebooks may wrap stable functions or commands; they must not become the sole implementation of backtesting logic.

## Cross-Story Dependencies

- Epic 6 depends on Epic 5 model training and registry capabilities, with finalized feature artifacts supplied by Epic 4 and configuration/local-data foundations supplied by earlier epics.
- Story 6.1 follows Story 5.4 and builds on the chronological training-window concepts from Story 5.2. Its windows may later be reused by model training and retraining.
- The declared sequence is 6.1 → 6.2 → 6.3 → 6.4: chronological periods precede the forecast-record contract, runner orchestration, and CLI integration.
- Epic 7 integrates policies through the runner and consumes historical forecast errors. Epic 8 consumes forecast and event artifacts for comparable metrics and exports. Maintain those contracts without implementing the downstream work here.
