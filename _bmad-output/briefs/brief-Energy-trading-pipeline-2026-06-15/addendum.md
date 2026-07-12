# Addendum

This addendum preserves implementation details from the source brief that are useful for downstream PRD, architecture, epic/story, or development workflows but are too detailed for the product brief.

## Proposed Components

| Component | Responsibility |
| --- | --- |
| DataSource | Represents ENTSO-E and Open-Meteo external providers. |
| DataIngestionService | Retrieves market, grid, and weather data from APIs or downloaded datasets. |
| PreprocessingService | Cleans, aligns, and standardises hourly data. |
| FeatureDataset | Stores processed features for training, forecasting, and backtesting. |
| ForecastModel | Wraps the XGBoost regression model. |
| ModelTrainer | Trains and retrains the model using defined windows. |
| ForecastService | Generates hourly day-ahead spread forecasts. |
| PerformanceMonitor | Calculates RMSE, MAE, and rolling RMSE. |
| RetrainingPolicy | Encapsulates no-retraining, fixed-schedule, and performance-triggered policies. |
| ModelRegistry | Stores model metadata, training periods, parameters, and metrics. |
| EvaluationService | Compares retraining strategies using historical backtesting. |
| Dashboard | Presents forecasts, actuals, rolling RMSE, retraining events, and comparison outputs. |

## Suggested Repository Structure

```text
project-root/
  README.md
  pyproject.toml
  uv.lock
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

## BMAD-Ready Epic Breakdown

### Epic 1: Data Pipeline

Goal: Build a reproducible data acquisition and preprocessing pipeline.

- Story 1.1: Fetch or load ENTSO-E market data for German and French prices.
- Story 1.2: Fetch or load Open-Meteo weather data.
- Story 1.3: Clean and align all datasets to hourly timestamps.
- Story 1.4: Generate lag, rolling, weather, grid, and calendar features.

### Epic 2: Forecasting Model

Goal: Train and validate an XGBoost model for price spread forecasting.

- Story 2.1: Train an XGBoost regressor for hourly spread prediction.
- Story 2.2: Tune model parameters for a stable baseline.
- Story 2.3: Save model artefacts and metadata.

### Epic 3: Backtesting and Retraining

Goal: Compare no retraining, fixed-schedule retraining, and performance-triggered retraining.

- Story 3.1: Implement a no-retraining baseline.
- Story 3.2: Implement weekly fixed-schedule retraining.
- Story 3.3: Implement rolling RMSE monitoring.
- Story 3.4: Implement rolling-RMSE-triggered retraining.
- Story 3.5: Log retraining events and model versions.

### Epic 4: Evaluation and Reporting

Goal: Produce outputs required for academic analysis.

- Story 4.1: Compute RMSE and MAE for each strategy.
- Story 4.2: Count retraining events for each strategy.
- Story 4.3: Export plots and tables for the final report.

### Epic 5: Monitoring Dashboard

Goal: Provide a simple interface for viewing forecasts and monitoring outputs.

- Story 5.1: Display forecasted and actual spreads.
- Story 5.2: Display rolling RMSE.
- Story 5.3: Display retraining events.
- Story 5.4: Compare strategy outputs.

## Implementation Sequence

1. Set up repository, environment, configuration files, and documentation.
2. Implement data loaders for ENTSO-E and Open-Meteo.
3. Implement cleaning, alignment, and feature generation.
4. Train the initial XGBoost forecasting model.
5. Implement forecast logging and actual-value matching.
6. Implement rolling RMSE and evaluation metrics.
7. Implement no-retraining, fixed-schedule, and performance-triggered strategies.
8. Run historical backtesting and export results.
9. Build the monitoring dashboard or report interface.
10. Finalise documentation, diagrams, and reproducibility instructions.

## Possible Lightweight Cloud Components

- Amazon S3 for raw data, processed data, model artefacts, logs, and evaluation results.
- AWS Lambda for small scheduled ingestion or monitoring tasks.
- EventBridge for scheduled triggers.
- CloudWatch for basic logging.
- Terraform for reproducible cloud resource definitions.
