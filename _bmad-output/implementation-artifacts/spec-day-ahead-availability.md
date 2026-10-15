---
title: 'Define and enforce day-ahead forecast availability'
type: 'feature'
created: '2026-10-10'
status: 'in-review'
baseline_commit: '921976f631ca19946eafb12fe8d24d4ea2d0e609'
context:
  - 'AGENTS.md'
  - 'docs/CODING_STYLE.md'
  - '_bmad-output/implementation-artifacts/investigations/proposal-training-assessment-investigation.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The backtest equates issuance with delivery start; current features do not establish day-ahead availability.

**Approach:** Implement explicit issuance and price/calendar preparation, verified by a static backtest. This is the availability story; RMSE, refitting, calibration, and comparison follow separately.

## Boundaries & Constraints

**Always:** Keep XGBoost, `spread = price_de - price_fr`, canonical strategies, and local execution. Issue at configured 10:00 `Europe/Berlin` on the preceding local date for the full delivery day (23/24/25 hours). Store UTC instants. Require whole-hour issue times; reject ambiguous/nonexistent times.

Price **usable-after** is delivery end (`timestamp + 1 hour`), consistently for predictors, labels, and errors. This conservative restriction is not measured publication provenance; metadata must disclose historical-snapshot revisions and deliberately delayed information use.

Configure price/spread lags `[48, 168]` elapsed hours, 24-hour rolling mean/std shifted 48 hours, and local `hour`, `day_of_week`, `month`, `is_weekend`. Exclude ERA5/grid until availability is established; preserve acquired data.

**Ask First:** Changes to the scientific timing convention or external predictors.

**Never:** Fabricate publication times, model provenance columns, overwrite existing artifacts, or implement subsequent stories here.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Daily issuance | Delivery January 15 | Forecast issued January 14 at 10:00 local | None |
| DST | Spring/autumn transition delivery day | 23/25 distinct UTC target hours, one common issuance | Reject invalid local issue times |
| Price provenance | Target hour and configured source lags | Actual usable time is target end; feature usable time is latest source usable time | Reject feature usable time after issuance |
| Insufficient history | Leading lag/rolling warmup | Drop and count warmup only | Fail on evaluation gaps, duplicates, nonfinite prices |
| Future mutation | Modify prices usable after an issuance | Predictors and predictions for that issuance remain identical | Test fails on leakage |
| Unsupported input | Weather/grid selection or metadata predictor | No silent inclusion | Clear validation error |

</frozen-after-approval>

## Code Map

- `backtesting/splitter.py`: immutable windows and current fixed-hour UTC schedule.
- `backtesting/backtest_runner.py`: issuance checks, policy history, prediction logging, run metadata.
- `features/dataset_builder.py`, `rolling_features.py`, `calendar_features.py`: reusable features and metadata.
- `models/trainer.py`: predictor inference currently excludes only target and timestamp.
- `cli.py`: existing local commands.

Package paths below are relative to `src/energy_trading_pipeline/`. Basis: Epics 4/6 and PRD FR-021/030/032.

## Tasks & Acceptance

**Execution:**
- [x] `backtesting/splitter.py` — add issuance/local-day generation; end validation at issuance, training at validation start; preserve legacy behavior.
- [x] `features/rolling_features.py`, `features/calendar_features.py`, `features/dataset_builder.py` — configurable shift/timezone with legacy defaults and metadata.
- [x] `features/availability.py` — derive `actual_available_at` and latest dependency `feature_available_at`; validate against original issuance; reuse builders, reject unsupported inputs.
- [x] `models/trainer.py` — exclude availability/issuance fields from predictors, including explicit selections.
- [x] `backtesting/backtest_runner.py` — explicit issuance for preflight, loaded-model bounds, hooks, logs, metadata; validate artifact/config consistency.
- [x] `cli.py` — price preparation command using existing loaders/spread calculation; save separate Parquet/metadata.
- [x] Repository `configs/experiment_day_ahead.yaml`, `configs/local_paths_day_ahead.yaml` — timing, features, static strategy, separate paths, existing model parameters, January 2025 smoke interval (not final evaluation).
- [x] Repository `docs/forecast_availability.md`, `README.md` — protocol, limitations, commands.
- [x] Repository `tests/unit/test_forecast_availability.py`, existing splitter/rolling/calendar/trainer tests, `tests/integration/test_day_ahead_backtest.py` — matrix, invalid configuration, metadata, legacy behavior, CLI integration.

**Acceptance Criteria:**
- Given complete fixtures, when preparation/backtesting run, then daily issuance, coverage, XGBoost predictions, and metadata match the protocol.
- Given selected predictors, when dependencies are checked, then all are usable by issuance and provenance never enters XGBoost.
- Given post-issuance mutations, when forecasts regenerate, then that issuance's features/predictions remain identical.
- Given existing callers, when regression tests run, then legacy contracts and artifacts remain intact.

## Spec Change Log

Initial draft based on the user's approved sequence and the October 10 investigation.

## Design Notes

48-hour lags sacrifice recency; validate dependencies rather than trusting lag length. Rolling warmup is `shift + window - 1`. Use local date arithmetic across DST. History durations remain configured elapsed days before issuance. Distinguish assumed usability from observed publication.

## Verification

- `uv run pytest` for targeted tests, then default suite; `git diff --check`.
- Run the short static smoke against cached prices; inspect timestamps/provenance and preserve separate artifacts. This is engineering verification, not final model evaluation.
