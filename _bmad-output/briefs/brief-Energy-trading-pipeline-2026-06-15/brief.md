---
title: "Product Brief: German-French Day-Ahead Electricity Price Spread Forecasting Pipeline"
status: draft
created: 2026-06-15
updated: 2026-06-15
---

# Product Brief: German-French Day-Ahead Electricity Price Spread Forecasting Pipeline

## Executive Summary

This product is a lightweight DataOps pipeline and monitoring interface for forecasting the German-French day-ahead electricity price spread. It forecasts the hourly spread between German and French day-ahead electricity prices using an XGBoost regression model, then evaluates whether performance-triggered retraining can maintain forecast quality with fewer unnecessary retraining runs than a fixed schedule.

The product exists to support an academic research project, not commercial trading. Its core value is reproducible evidence: clean data, comparable retraining strategies, logged model behaviour, and visual outputs that can support a final dissertation or project report. The first version should prove whether a monitored retraining policy based on rolling RMSE is practical and defensible for electricity price spread forecasting.

## The Problem

Electricity price relationships between neighbouring markets can shift as demand, generation mix, weather, interconnection constraints, and market conditions change. A forecasting model trained once may degrade as these conditions drift. Retraining too often can waste compute and complicate model governance, while retraining too rarely can leave forecasts stale.

For this project, the researcher needs more than a single model accuracy score. They need a controlled way to compare three operational strategies: no retraining, fixed-schedule retraining, and retraining only when performance deteriorates. Without a reproducible pipeline, the results risk being difficult to audit, hard to explain, or vulnerable to look-ahead bias.

## The Solution

Build a reproducible forecasting and backtesting pipeline that ingests electricity market, grid, and weather data; prepares hourly model features; trains an XGBoost spread forecasting model; and compares retraining strategies over historical data.

The system will calculate the target as:

```text
German-French spread = German day-ahead electricity price - French day-ahead electricity price
```

It will monitor forecast errors using RMSE, MAE, and rolling RMSE. The performance-triggered strategy will retrain the model when rolling RMSE exceeds a configurable threshold. A simple dashboard or report interface will show forecasts, actual spreads, error metrics, retraining events, model versions, and strategy comparison outputs.

## Who This Serves

The primary user is a researcher or analyst evaluating model retraining strategies for electricity price spread forecasting. They need a system that automates ingestion and evaluation while making results easy to inspect and defend.

Success for this user means they can run the pipeline, reproduce the backtest, inspect when and why retraining happened, and export figures or tables suitable for academic reporting.

## What Makes This Different

The product is not trying to be a general-purpose energy trading platform. Its differentiation is focus: it isolates one clear forecasting target, one model family, and one operational question about retraining policy.

The key comparison is not just accuracy. It is the trade-off between forecast quality and retraining frequency. That makes the product useful as an academic DataOps prototype because it links model monitoring to operational model maintenance decisions.

## First-Version Scope

The first version will include:

- Data ingestion or loading for ENTSO-E electricity market data and Open-Meteo weather data.
- Hourly preprocessing, timestamp alignment, missing-value handling, and daylight-saving-time handling.
- Feature generation for lagged spreads, lagged prices, rolling averages, weather predictors, grid predictors, and calendar variables.
- XGBoost model training for hourly spread forecasts.
- Backtesting for no retraining, fixed-schedule retraining, and rolling-RMSE-triggered retraining.
- Logging of forecasts, actual values, errors, rolling RMSE, model versions, and retraining events.
- Evaluation outputs covering RMSE, MAE, retraining frequency, and optional directional accuracy.
- A lightweight dashboard, static report, or notebook dashboard for reviewing forecasts and strategy comparisons.

The first version will not include:

- Real-money trading simulation or profit-and-loss analysis.
- Intraday or balancing-market forecasting.
- Model architecture comparison beyond XGBoost.
- Formal uncertainty quantification.
- Bidding zones outside Germany and France.
- Enterprise-scale deployment using expensive managed services.

## Success Criteria

The product is successful if it can:

- Produce a cleaned, aligned hourly feature dataset from the required data sources or local cached files.
- Train an XGBoost model and generate hourly German-French spread forecasts.
- Run a historical backtest for all three retraining strategies without look-ahead bias.
- Log forecasts, actuals, errors, rolling RMSE, model versions, and retraining events.
- Export comparison metrics for RMSE, MAE, and retraining frequency.
- Display forecasts, actual spreads, rolling RMSE, retraining events, and strategy comparison results.
- Provide enough documentation for another reader to reproduce the core experiment.

## Product Principles

- Reproducibility over sophistication: every result should be traceable to data, configuration, model version, and backtest period.
- Comparable experiments over model novelty: all strategies should use the same feature set and model configuration after tuning.
- Cost-conscious implementation: local or notebook-based computation is acceptable; cloud services should be limited to storage, scheduling, logging, or demonstration needs.
- Academic defensibility: the pipeline should explicitly prevent look-ahead bias and document assumptions, missing data, thresholds, and evaluation windows.

## Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| ENTSO-E data gaps or API issues | Cache downloaded data, support local CSV or Parquet loading, and document missing periods. |
| Weather variable mismatch | Define a minimal required weather feature set and allow optional variables to be skipped. |
| Backtests are slow | Start with smaller date ranges, profile bottlenecks, and scale only after correctness is verified. |
| Retraining threshold is arbitrary | Make thresholds configurable and report sensitivity in the final analysis. |
| Cloud costs expand beyond project needs | Keep training and backtesting local; use AWS only where it improves reproducibility or demonstration. |
| Dashboard over-scope | Limit the dashboard to forecasts, actuals, rolling RMSE, retraining events, and strategy comparison. |

## Vision

If successful, this project becomes a reusable research prototype for monitored retraining in energy market forecasting. It could later be extended to other bidding-zone spreads, additional model families, stronger experiment tracking, uncertainty estimates, or economic evaluation. For the current project, the goal is narrower: produce a credible, reproducible demonstration that performance-triggered retraining can be evaluated against static and scheduled baselines in a realistic electricity-market forecasting workflow.
