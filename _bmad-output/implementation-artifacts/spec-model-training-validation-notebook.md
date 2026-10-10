---
title: 'Add Model Training and Validation Notebook'
type: 'feature'
created: '2026-10-06'
status: 'in-review'
baseline_commit: '1f52d5b'
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/docs/CODING_STYLE.md'
  - '{project-root}/notebooks/README.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Baseline XGBoost training and held-out validation are only reachable through the `train` CLI command, which prints a run ID and writes RMSE/MAE to YAML. There is no presentation-ready view of the chronological split, the fitted model's behaviour on validation rows, its errors, or which features it relies on.

**Approach:** Add a third notebook that wraps the existing training API rather than reimplementing it. It builds a feature dataset from the cached 2022-2025 price and ERA5 weather artifacts with weather lagged by `features.lag_hours`, shows the chronological train/validation split selected by `TrainingWindow` and `select_training_window`, trains through `train_baseline` (the function behind `cli train`) into a temporary registry, reloads the saved artifact, reproduces the recorded metrics, and presents validation plots, residuals, persistence reference baselines, feature importance, and a read-only view of the saved model registry. Real data is the presentation default; fixture mode provides offline Run All verification.

## Boundaries & Constraints

**Always:** Train only through `train_baseline` so the notebook and CLI cannot diverge; keep training and validation chronological and end-inclusive as configured; use canonical column names (`timestamp`, `actual`, `prediction`, `error`, `squared_error`, `absolute_error`); write every notebook-produced model, registry entry, and run log to a temporary directory; write the real-mode feature dataset only to `data/features/feature_dataset_2022_2025.parquet`; use ERA5 weather only as lagged predictors; state that `train` validation uses 1-hour lags and is therefore one-step-ahead, not a day-ahead backtest.

**Ask First:** Writing to the canonical `models/` registry or `logs/`, tuning hyperparameters, adding cross-validation schemes, adding new metrics to the pipeline, or changing the feature set.

**Never:** Add another model family, generate features or fetch data in real mode, score a saved model on rows inside its own training window, place reusable logic only in the notebook, or present validation RMSE as a trading or day-ahead backtest result.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Real presentation | Cached 2022-2025 price and country-weather Parquet files exist; `configs/experiment_2022_2025.yaml` defines the split | Train once into a temp registry, reproduce recorded RMSE/MAE from the reloaded artifact, plot validation behaviour | Fail clearly when the feature file, dates, or params are missing |
| Automated fixture | Fixture mode selected | Build a feature dataset from repository fixtures into a temp dir and run the same stages offline | Same validation as real mode |
| Saved registry model | Canonical registry lists models | Show versions, windows, metrics; rescore only models whose training ends before the validation window and whose features exist | Skip ineligible models with the reason shown |
| Leaky input | Feature dataset contains `price_de`/`price_fr` | Do not train | `train_baseline` raises its leakage error |

</frozen-after-approval>

## Code Map

- `notebooks/03_model_training_validation.ipynb` -- presentation wrapper for configuration, feature dataset, split, training, reload verification, baselines, plots, feature importance, registry view, and limitations.
- `configs/experiment_2022_2025.yaml`, `configs/local_paths_2022_2025.yaml` -- 2022-2024 training / 2025 validation split, lagged-weather feature settings, and artifact paths.
- `notebooks/README.md` -- notebook purpose, prerequisites, modes, and Run All commands.
- `tests/integration/test_model_training_notebook.py` -- executes every code cell in fixture mode and checks split chronology, reproduced metrics, canonical validation columns, and no canonical registry writes.
- `src/energy_trading_pipeline/models/trainer.py` -- existing `TrainingWindow`, `select_training_window`, `train_baseline` used unchanged.
- `src/energy_trading_pipeline/models/xgboost_model.py` -- existing `XGBoostSpreadModel.load` used unchanged.

## Tasks & Acceptance

**Execution:**
- [x] `notebooks/03_model_training_validation.ipynb` -- add markdown and code stages listed in the Code Map.
- [x] `notebooks/README.md` -- document the notebook, prerequisites, and commands.
- [x] `tests/integration/test_model_training_notebook.py` -- fixture-mode Run All with invariant assertions.

**Acceptance Criteria:**
- Given the real feature dataset, when the notebook runs in default mode, then it trains via `train_baseline`, reloads the saved artifact, and reproduces the recorded validation RMSE and MAE.
- Given the split, when it is displayed, then every training timestamp precedes every validation timestamp and the row counts match the configured windows.
- Given any run, when it completes, then the canonical `models/registry/models_index.yaml` and `logs/` are unchanged.
- Given fixture mode and the normal test environment, when the integration test executes every code cell, then it completes without credentials, network access, or real datasets.
- Given an evaluator reads the final section, then the one-step-ahead limitation, the small configured window, and the boundary before backtesting are explicit.

## Verification

**Commands:**
- `uv run pytest tests/integration/test_model_training_notebook.py -q` -- expected: fixture Run All passes.
- `uv run --extra notebook jupyter nbconvert --to notebook --execute --output /tmp/03_model_training_validation.executed.ipynb notebooks/03_model_training_validation.ipynb` -- expected: real-data execution completes locally.
- `uv run pytest -q` -- expected: existing default suite remains green.

## Spec Change Log

- 2026-10-06: Real mode switched from the 7-day January 2023 sample to the cached full-year 2024 data at the user's request. Weather is included as 1h/24h lags of ERA5 per the leakage note in `docs/data_sources.md`; the lag warm-up hours are dropped so the optional-weather selector does not exclude the lagged columns.
- 2026-10-06: Extended to local-market years 2022-2025 at the user's request (new SMARD run `run_20261006_072807`, ERA5 run `run_20261006_073531`, documented in `docs/data_sources.md`). Training is 2022-2024, validation all of 2025; the 2024-only configs were replaced.
