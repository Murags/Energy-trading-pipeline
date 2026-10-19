# Calibration and the development/evaluation boundary

This document freezes the choices that the final three-strategy comparison will use, and records what was inspected before freezing them. It exists so that the final result can be read as a prediction the protocol made in advance, not as the best of several settings tried against the answer.

Status: **draft, pending approval.** Nothing here is final until the user approves the frozen settings below and the final evaluation is run once.

## Why a boundary is needed

The research question is whether performance-triggered retraining can reduce unnecessary retraining while holding accuracy comparable to weekly scheduled retraining. The rolling-RMSE threshold is a free parameter. Choosing it by trying values against the final evaluation period and keeping the best would make the comparison circular: the threshold would have been fitted to the very data used to judge it.

The threshold is therefore chosen on a **development period** that is disjoint from, and earlier than, the **final evaluation period**.

## Disclosure of prior inspection

Honesty about what was already seen matters more than a clean story.

- The one-hour-ahead notebook benchmark (`notebooks/03_model_training_validation.ipynb`) was executed on 2025 and its validation scores were inspected: RMSE 17.23, MAE 10.65, R² 0.784. That benchmark uses a **different feature set** (1-hour and 24-hour lags plus ERA5 weather) from the day-ahead protocol, and a different forecast horizon. It does not share the day-ahead model.
- The January 1–7, 2025 day-ahead smoke run was inspected (RMSE 33.86, MAE 29.35).
- An exploratory three-strategy run over January–March 2025 was executed with an **arbitrary, uncalibrated** threshold of 20.0 and inspected. It produced 0 / 12 / 82 refits. Those runs were deleted; they informed no setting in this document other than demonstrating that an uncalibrated threshold fires almost every day.

2025 Q1 day-ahead results have therefore been seen before calibration. This is disclosed rather than concealed. The threshold below is selected only from pre-2025 development data, and the final evaluation is run once with the frozen settings.

## Development period

Threshold selection uses **2024-01-01 to 2024-12-31** (8,784 hourly forecasts), with **2023-01-01 to 2023-12-31** as an independent sensitivity check. Both precede the final evaluation period and neither is used to report final results.

## What was held constant

Across every strategy and every development run, these are identical, so the only thing that varies is *when* a refit happens:

- Feature dataset: `data/features/day_ahead/feature_dataset.parquet`, built once under the availability contract in `docs/forecast_availability.md`.
- Predictors: the 16 columns in `backtest.feature_columns` (price/spread lags 48 and 168, 24-hour rolling mean/std shifted 48, local `hour`, `day_of_week`, `month`, `is_weekend`).
- Model parameters: `configs/model_params.yaml`, unchanged from earlier work and **not** tuned here.
- Issuance: 10:00 `Europe/Berlin` on the preceding local date, full local delivery day.
- Training window: 90 elapsed days ending at the validation start; validation 7 days ending at issuance.
- Rolling RMSE monitor: 7-day window, anchored one hour back per `actual_availability_lag_hours: 1`.
- Comparator: `fixed_schedule` at 7 days.

Model hyperparameters are explicitly **not** calibrated. Tuning them as well would change two things at once and confound the retraining comparison.

## Development results (2024)

| Setting | Refits | RMSE | MAE | RMSE vs weekly | Refits vs weekly |
|---|---|---|---|---|---|
| `no_retraining` | 0 | 36.874 | 21.813 | +0.499 | −52 |
| `fixed_schedule` weekly | 52 | 36.375 | 22.340 | 0.000 | 0 |
| triggered @ 25 | 253 | 36.147 | 22.689 | −0.228 | +201 |
| triggered @ 30 | 146 | 36.183 | 22.595 | −0.192 | +94 |
| triggered @ 35 | 82 | 36.772 | 23.142 | +0.397 | +30 |
| triggered @ 40 | 54 | 36.789 | 22.971 | +0.414 | +2 |
| triggered @ 45 | 35 | 36.216 | 23.175 | −0.159 | −17 |
| triggered @ 50 | 29 | 36.891 | 23.373 | +0.516 | −23 |
| triggered @ 60 | 15 | 37.303 | 22.762 | +0.929 | −37 |
| triggered @ 75 | 14 | 37.295 | 22.759 | +0.921 | −38 |

## Reading these results honestly

The most important observation is not which threshold won.

**Retraining has a small effect on this model.** Across settings ranging from 0 to 253 refits, RMSE spans 36.15 to 37.30 — a range of 1.16, about 3.2% of the mean. Never retraining costs about 0.5 RMSE against weekly retraining, while retraining five times as often as weekly buys about 0.2.

**The response is not monotonic.** Threshold 45 (35 refits) scores better than thresholds 35 and 40 (82 and 54 refits). If more retraining reliably helped, that could not happen. The ordering among nearby thresholds is therefore not trustworthy on its own, and a threshold chosen because it won by 0.16 RMSE is likely being fitted to noise.

**RMSE and MAE disagree.** `no_retraining` has the *best* MAE (21.81) of every setting while having one of the worse RMSEs. Retraining appears to help with large errors while slightly hurting typical ones. Any claim of "better accuracy" must say which metric it means.

A plausible explanation is the predictor set: only price history and calendar features, no weather or grid data. Much of what this model captures may be stable seasonal and daily structure that does not go stale within a year, so refreshing it changes little.

## Sensitivity check (2023)

<!-- PENDING: 2023 sweep results and whether the 2024 ranking holds. -->

## Frozen settings for the final evaluation

<!-- PENDING: filled in after the sensitivity check, then approved before the final run. -->

## Final evaluation protocol

Once the settings above are approved and frozen:

- Final evaluation period: **2025-01-01 to 2025-12-31**, disjoint from and later than both development periods.
- All three strategies run on identical data, predictors, model parameters, issuance times, and target timestamps.
- Each run is executed **once**. Re-running with a changed threshold after seeing 2025 results would void the boundary this document establishes and must be recorded as a new calibration round here.
- Saved outputs: forecasts, RMSE and MAE, completed retraining counts, runtime, configuration, and report exports.
