---
title: "PRD: German-French Day-Ahead Electricity Price Spread Forecasting Pipeline"
status: final
created: 2026-06-15
updated: 2026-06-15
---

# PRD: German-French Day-Ahead Electricity Price Spread Forecasting Pipeline

> Status: Approved source of truth for architecture and downstream implementation planning.

## 1. Purpose

This PRD defines the requirements for a reproducible DataOps pipeline that forecasts the hourly German-French day-ahead electricity price spread and evaluates three model retraining strategies. It is intended to support both academic submission and developer implementation.

The PRD prioritises requirements that make the project defensible as an academic evaluation: reproducible datasets, controlled backtesting, comparable retraining strategies, traceable model versions, logged metrics, and clear evidence that performance-triggered retraining was evaluated against static and scheduled baselines.

## 2. Product Goal

Build a lightweight forecasting and evaluation system that can answer the central project question:

> Can performance-triggered retraining, using rolling RMSE as the main trigger, maintain German-French day-ahead electricity price spread forecast performance while reducing unnecessary retraining compared with fixed-schedule retraining?

The system will forecast:

```text
spread_t = German day-ahead price_t - French day-ahead price_t
```

The product is not a trading system. It is a research and implementation prototype for forecasting, monitoring, retraining, and evaluation.

## 3. Users and Use Cases

### 3.1 Primary User: Researcher / Analyst

The researcher needs to run experiments, compare retraining strategies, inspect forecast quality, and produce evidence for the final academic report and defence.

Primary use cases:

- Load or fetch historical market, grid, and weather data.
- Build an hourly feature dataset for 2020-2025 or a configurable date range.
- Train an XGBoost spread forecasting model.
- Run historical backtests for all three retraining strategies.
- Inspect forecasts, actual values, errors, rolling RMSE, and retraining events.
- Export metrics, tables, plots, and logs for academic reporting.

### 3.2 Secondary User: Developer / Maintainer

The developer needs clear implementation boundaries, module responsibilities, acceptance criteria, and reproducibility requirements.

Primary use cases:

- Implement ingestion, preprocessing, feature generation, modelling, backtesting, monitoring, retraining, evaluation, and dashboard modules.
- Run tests on local sample data without requiring live API access.
- Reproduce experiments from configuration and saved artifacts.

## 4. Scope

### 4.1 In Scope

- Historical hourly German and French day-ahead electricity price data.
- Historical grid, load, and generation variables from ENTSO-E where available.
- Historical weather variables from Open-Meteo, including temperature, wind speed, and solar-related variables where available.
- Configurable date ranges, with 2020-2025 as the target evaluation period.
- Local CSV and Parquet loading as a first-class MVP path.
- API-based ingestion for ENTSO-E and Open-Meteo where credentials, limits, and data availability allow.
- Hourly cleaning, timestamp standardisation, alignment, missing-value handling, duplicate handling, and daylight-saving-time handling.
- Feature generation for lagged spreads, lagged prices, rolling features, calendar variables, weather predictors, and grid predictors.
- XGBoost regression model for hourly spread forecasting.
- Historical backtesting for three retraining strategies: no retraining, fixed-schedule retraining, and performance-triggered retraining.
- Rolling RMSE as the main performance-triggered retraining signal.
- RMSE, MAE, and retraining frequency as core evaluation metrics.
- Optional directional accuracy and PSI logging as secondary diagnostics.
- Static evaluation outputs, including metrics tables and plots.
- Lightweight dashboard or notebook/static report interface for forecasts, actual spreads, rolling RMSE, retraining events, and strategy comparison.
- OOAD/UML and system architecture documentation aligned with the implementation.

### 4.2 Out of Scope

- Live trading or trading recommendations.
- Profit-and-loss simulation.
- Intraday or balancing-market forecasting.
- Forecasting outside Germany and France.
- Model architecture comparison beyond XGBoost.
- Formal uncertainty quantification.
- Enterprise-scale orchestration, managed ML platforms, or expensive cloud deployment.
- Production SLA guarantees.

## 5. MVP Definition

The MVP is complete when the system can run a reproducible local experiment using cached or local CSV/Parquet data, produce cleaned hourly features, train an XGBoost model, backtest all three retraining strategies, export metrics and plots, and log model versions and retraining events.

The dashboard is a required final project deliverable, but it must not block the core MVP. A notebook or static report is acceptable for early evaluation outputs. The dashboard may be implemented after the core pipeline and backtesting engine are working.

### 5.1 MVP Build Priority

The MVP shall be implemented in a local-first and evaluation-first manner. The first priority is to produce a reproducible backtesting experiment that compares no retraining, fixed-schedule retraining, and performance-triggered retraining using the same dataset, features, model configuration, and evaluation period.

The dashboard and cloud prototype shall be implemented only after the core pipeline, model training, retraining strategies, and evaluation outputs are working. This prevents user-interface or cloud-deployment work from delaying the main research contribution.

## 6. Functional Requirements

### 6.1 Data Ingestion

- FR-001: The system shall support local CSV and Parquet loading for all required datasets.
- FR-002: The system shall support configurable file paths for local datasets.
- FR-003: The system shall support ENTSO-E API ingestion for day-ahead prices, load, and generation-related variables where available.
- FR-004: The system shall support Open-Meteo API ingestion for weather variables.
- FR-005: The system shall allow configurable start and end dates for ingestion and processing.
- FR-006: The system shall cache downloaded raw data to support reproducible reruns and reduce API dependence.
- FR-007: The system shall log ingestion source, date range, retrieval timestamp, and any missing or failed data requests.

### 6.2 Data Preprocessing and Alignment

- FR-008: The system shall standardise timestamps across all sources to a consistent hourly time index.
- FR-009: The system shall align German price, French price, grid, load, generation, and weather records to hourly delivery periods.
- FR-010: The system shall handle missing values using documented, reproducible rules.
- FR-011: The system shall detect and handle duplicate records.
- FR-012: The system shall handle daylight-saving-time transitions explicitly and document the applied approach.
- FR-013: The system shall calculate the target variable as German day-ahead price minus French day-ahead price for each hourly delivery period.
- FR-014: The system shall save cleaned and aligned datasets in a reproducible format, preferably Parquet.

### 6.3 Feature Engineering

- FR-015: The system shall generate lagged spread features.
- FR-016: The system shall generate lagged price features for Germany and France.
- FR-017: The system shall generate rolling statistical features such as rolling means or rolling standard deviations.
- FR-018: The system shall generate calendar features such as hour, day of week, month, weekend flag, and holiday flag where available.
- FR-019: The system shall include weather predictors from Open-Meteo where available.
- FR-020: The system shall include grid, load, and generation predictors from ENTSO-E where available.
- FR-021: The system shall avoid look-ahead leakage when generating lagged and rolling features.
- FR-022: The system shall save the final feature dataset with metadata describing source date range, feature columns, and target column.

### 6.4 Forecast Model

- FR-023: The system shall train an XGBoost regression model to forecast hourly German-French day-ahead price spreads.
- FR-024: The system shall use the same model configuration across all retraining strategies after baseline tuning.
- FR-025: The system shall support configurable model parameters, including learning rate, maximum depth, number of estimators, subsampling, and regularisation terms.
- FR-026: The system shall save trained model artifacts.
- FR-027: The system shall record model metadata, including training window, feature set, parameters, validation metrics, and creation timestamp.

### 6.5 Backtesting

- FR-028: The system shall run historical backtests over a configurable evaluation period.
- FR-029: The system shall support 2020-2025 as the target historical evaluation range, subject to data completeness.
- FR-030: The system shall ensure that future values are not used during training, feature generation, forecasting, or retraining decisions.
- FR-031: The system shall generate forecasts and compare them against actual spreads once actual values are available.
- FR-032: The system shall log forecast timestamp, target timestamp, predicted spread, actual spread, error, strategy name, and model version.
- FR-033: The system shall support smaller date-range runs for development and debugging.

### 6.6 Retraining Strategies

- FR-034: The system shall implement a no-retraining strategy where the model is trained once at the start of the evaluation period and held fixed.
- FR-035: The system shall implement a fixed-schedule retraining strategy with a configurable retraining interval, with weekly retraining as the default comparator.
- FR-036: The system shall implement a performance-triggered retraining strategy based on rolling RMSE.
- FR-037: The system shall allow configuration of the rolling RMSE window size.
- FR-038: The system shall allow configuration of the rolling RMSE threshold.
- FR-039: The system shall retrain under the performance-triggered strategy when rolling RMSE exceeds the configured threshold.
- FR-040: The system shall log retraining events, including trigger reason, threshold, rolling RMSE value, training window, model version, and timestamp.
- FR-041: The system may calculate PSI as a secondary diagnostic, but PSI shall not be the primary retraining trigger for this project.

### 6.7 Evaluation and Reporting

- FR-042: The system shall calculate RMSE for each retraining strategy.
- FR-043: The system shall calculate MAE for each retraining strategy.
- FR-044: The system shall calculate retraining frequency for each retraining strategy.
- FR-045: The system may calculate directional accuracy as a secondary metric.
- FR-046: The system shall export comparison tables suitable for academic reporting.
- FR-047: The system shall export plots showing forecasts versus actual spreads.
- FR-048: The system shall export plots showing rolling RMSE over time.
- FR-049: The system shall export plots or tables showing retraining events and model version changes.
- FR-050: The system shall produce enough evaluation evidence to demonstrate that all strategies were evaluated on the same backtesting setup.

### 6.8 Dashboard and Review Interface

- FR-051: The system shall provide a lightweight dashboard, notebook dashboard, or static report interface for reviewing outputs.
- FR-052: The interface shall show forecasted and actual German-French price spreads.
- FR-053: The interface shall show RMSE, MAE, and rolling RMSE.
- FR-054: The interface shall show retraining events and model version changes.
- FR-055: The interface shall compare no retraining, fixed-schedule retraining, and performance-triggered retraining.
- FR-056: The dashboard shall be simple and cost-conscious; it shall not require enterprise deployment infrastructure.

### 6.9 Documentation and Academic Artifacts

- FR-057: The system shall include setup and reproduction instructions.
- FR-058: The system shall document data sources, required credentials, and local-file fallback usage.
- FR-059: The system shall document preprocessing decisions, including missing-value handling and daylight-saving-time treatment.
- FR-060: The system shall document backtesting assumptions and leakage-prevention measures.
- FR-061: The system shall document retraining policies, thresholds, and evaluation metrics.
- FR-062: The system shall include OOAD/UML diagrams and system architecture documentation aligned with the implemented modules.

### 6.10 Implementation Phases

- FR-063: The implementation shall follow a staged build sequence that prioritises reproducible evaluation before dashboard or cloud work.
- FR-064: Phase 1 shall cover project setup, configuration, repository structure, and environment files.
- FR-065: Phase 2 shall cover local data loading using CSV or Parquet files.
- FR-066: Phase 3 shall cover data cleaning, timestamp alignment, spread calculation, and feature engineering.
- FR-067: Phase 4 shall cover baseline XGBoost model training and prediction.
- FR-068: Phase 5 shall cover the historical backtesting framework.
- FR-069: Phase 6 shall cover no-retraining, fixed-schedule retraining, and performance-triggered retraining strategies.
- FR-070: Phase 7 shall cover evaluation metrics, comparison tables, plots, and logs.
- FR-071: Phase 8 shall cover the lightweight dashboard or notebook/static report interface.
- FR-072: Phase 9 may cover an optional lightweight AWS prototype for storage, scheduling, logging, or deployability demonstration.
- FR-073: Phase 10 shall cover final documentation, diagrams, and academic reporting artifacts.

## 7. Non-Functional Requirements

- NFR-001: Reproducibility: experiments shall be rerunnable from saved data, configuration, and model artifacts.
- NFR-002: Traceability: datasets, feature sets, model versions, training windows, forecasts, actuals, errors, and retraining events shall be traceable through logs or metadata.
- NFR-003: Cost control: the implementation shall favour local execution, notebooks, and lightweight storage over managed ML infrastructure.
- NFR-004: Modularity: ingestion, preprocessing, feature engineering, modelling, backtesting, monitoring, retraining, evaluation, and dashboard concerns shall be separated enough to support testing and explanation.
- NFR-005: Configurability: date ranges, paths, model parameters, retraining intervals, rolling windows, and thresholds shall be configurable without code changes where practical.
- NFR-006: Robustness: the system shall tolerate missing optional variables and still run with a documented reduced feature set.
- NFR-007: Academic defensibility: the implementation shall make leakage prevention, evaluation comparability, and assumptions explicit.
- NFR-008: Maintainability: code shall be organised clearly enough for another developer or evaluator to inspect and reproduce the workflow.

## 8. Data Requirements

### 8.1 Required Data

- German day-ahead electricity prices at hourly resolution.
- French day-ahead electricity prices at hourly resolution.
- Time index covering the selected evaluation period.

### 8.2 Preferred Data

- German and French load or demand variables.
- Generation-related variables where available.
- Weather variables from Open-Meteo, including temperature, wind speed, and solar-related variables.

### 8.3 Target Evaluation Period

The target historical period is 2020-2025. The final usable range may be shorter if data completeness requires it, but the system must support configurable start and end dates and document any exclusions.

### 8.4 Default Experiment Configuration

The initial implementation shall use configurable defaults to avoid blocking development while final values are refined. Weekly retraining shall be used as the default fixed-schedule comparator. A 7-day rolling RMSE window shall be used as the default performance-monitoring window. The rolling RMSE threshold shall be configurable and may initially be set using validation-period performance before sensitivity testing is performed.

The final report shall clearly document the chosen threshold, rolling window, training window, evaluation period, and any data exclusions caused by missing or incomplete records.

## 9. Success Metrics

### 9.1 Product Success Metrics

- The full local experiment can be reproduced from documented commands and configuration.
- All three retraining strategies complete on the same historical backtesting setup.
- Evaluation outputs include RMSE, MAE, and retraining frequency for each strategy.
- Retraining events are explainable from logged rolling RMSE values and thresholds.
- Final documentation includes architecture and OOAD/UML artifacts.

### 9.2 Model and Evaluation Metrics

- RMSE by strategy.
- MAE by strategy.
- Retraining count and retraining frequency by strategy.
- Optional directional accuracy by strategy.
- Optional PSI diagnostic outputs.

### 9.3 Counter-Metrics

- Excessive retraining frequency that weakens the value of performance-triggered retraining.
- Missing data periods large enough to undermine evaluation claims.
- Backtest runtime so high that iteration becomes impractical.
- Dashboard effort consuming time needed for core evaluation and documentation.

## 10. Constraints and Assumptions

- XGBoost is the only forecasting model for this project.
- Rolling RMSE is the main trigger for performance-triggered retraining.
- Local CSV/Parquet loading is first-class for MVP.
- API-based ingestion is valuable but must not block implementation.
- Heavy training and historical backtesting may run locally or in notebooks.
- AWS usage, if included, should be limited to lightweight storage, scheduling, logging, or deployability demonstration.
- The project is time-constrained by academic submission and defence milestones.
- Reproducibility and evaluation clarity are more important than production-scale automation.

## 11. Open Questions

- OQ-001: What exact training, validation, and test split should be used within the 2020-2025 period?
- OQ-002: What default rolling RMSE window should be used for performance-triggered retraining?
- OQ-003: What default rolling RMSE threshold should be used, and will sensitivity analysis be required?
- OQ-004: Which ENTSO-E generation and grid variables are reliably available for both Germany and France?
- OQ-005: Which dashboard format will be selected for final delivery: Streamlit, notebook dashboard, or static report?
- OQ-006: Are the proposal-level UML diagrams sufficient, or should implementation-stage documentation also include a component or deployment diagram for the DataOps pipeline?
