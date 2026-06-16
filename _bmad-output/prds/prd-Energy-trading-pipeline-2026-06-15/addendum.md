# Addendum

This addendum stores implementation details that inform downstream architecture and story creation but should not dominate the PRD narrative.

## Candidate Module Boundaries

| Module | Responsibility |
| --- | --- |
| DataSource | Represents external or local data providers. |
| DataIngestionService | Retrieves ENTSO-E and Open-Meteo data from APIs or local files. |
| PreprocessingService | Cleans, aligns, and standardises hourly records. |
| FeatureDataset | Stores processed feature matrices and target values. |
| ForecastModel | Wraps the XGBoost regression model. |
| ModelTrainer | Trains and retrains model versions. |
| ForecastService | Generates hourly spread forecasts. |
| PerformanceMonitor | Calculates RMSE, MAE, rolling RMSE, and optional diagnostics. |
| RetrainingPolicy | Encapsulates no-retraining, fixed-schedule, and performance-triggered logic. |
| ModelRegistry | Stores model metadata and artifacts. |
| EvaluationService | Compares strategy outputs. |
| Dashboard | Presents forecasts, actuals, rolling metrics, retraining events, and strategy comparisons. |

## Suggested Implementation Order

1. Project setup, configuration, repository structure, and environment files.
2. Local data loading using CSV or Parquet files.
3. Data cleaning, timestamp alignment, spread calculation, and feature engineering.
4. Baseline XGBoost model training and prediction.
5. Historical backtesting framework.
6. No-retraining, fixed-schedule retraining, and performance-triggered retraining strategies.
7. Evaluation metrics, comparison tables, plots, and logs.
8. Lightweight dashboard or notebook/static report interface.
9. Optional lightweight AWS prototype for storage, scheduling, logging, or deployability demonstration.
10. Final documentation, diagrams, and academic reporting artifacts.

## Default Experiment Configuration

- Fixed-schedule retraining default: weekly.
- Performance-monitoring window default: 7-day rolling RMSE.
- Performance-triggered threshold: configurable, initially set using validation-period performance before sensitivity testing.
- Final report documentation: chosen threshold, rolling window, training window, evaluation period, and data exclusions.

## Suggested Repository Structure

```text
project-root/
  README.md
  requirements.txt
  pyproject.toml
  .env.example
  data/
    raw/
    processed/
    features/
  notebooks/
  src/
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
  infrastructure/
    terraform/
  reports/
    figures/
    tables/
  tests/
```
