---
title: 'Add Data Exploration and Preprocessing Notebook'
type: 'feature'
created: '2026-09-13'
status: 'in-review'
baseline_commit: '5dadcd3bd91e33ee8e010044e00b152a5d0b8c73'
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/docs/CODING_STYLE.md'
  - '{project-root}/docs/data_sources.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The repository has validated 2024 German/French electricity prices and regional weather artifacts, but there is no presentation-ready notebook showing how those sources are inspected, cleaned, synchronized, and prepared before feature engineering or model training.

**Approach:** Add one linear data-exploration notebook that uses existing pipeline APIs to load and normalize cached data, demonstrates explicit quality and cleanup decisions, aligns prices with weather, calculates the German-French spread, visualizes the resulting dataset, and leaves a clearly identified prepared dataframe for later modelling. Real data is the presentation default, while fixture mode provides offline automated Run All verification.

## Boundaries & Constraints

**Always:** Keep reusable cleanup and preprocessing logic under `src/`; preserve UTC chronology and `spread = price_de - price_fr`; show input provenance, schemas, timestamp coverage, duplicates, missingness, descriptive statistics, negative prices, outliers, DST behavior, alignment evidence, and retained/excluded columns; preserve valid negative and extreme electricity prices; distinguish location-level weather from country aggregates; make every code cell executable in order from the repository root.

**Ask First:** Adding imputation, clipping or deleting price outliers, changing the eight selected weather locations or their aggregation weights, exporting a new canonical processed artifact, or expanding into feature engineering and model training.

**Never:** Download data during notebook execution, require credentials/network/AWS, manufacture missing real observations, silently discard records or columns, place reusable transformations only in the notebook, use target-hour ERA5 values as claimed forecast-time predictors, or present exploratory associations as causal/model results.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Real presentation | Cached 2024 price, location-weather, and aggregate-weather Parquet files exist | Validate 8,784 matching timestamps and produce one prepared hourly dataframe containing prices, spread, and country weather | Fail clearly with the missing path, column, coverage, or mismatch details |
| Automated fixture | Fixture mode is selected | Run the same exploration/preprocessing sequence offline on small repository fixtures | Apply configured duplicate/missing policies and display their audit summaries |
| Optional weather issue | A weather column is absent or incomplete | Report the issue explicitly; do not affect required price validation | Exclude only through the repository's documented optional-column policy |
| Price quality issue | Required price is missing, nonnumeric, duplicated, or temporally incomplete | Do not calculate or present a misleading spread | Stop with the relevant validation/cleanup error |

</frozen-after-approval>

## Code Map

- `notebooks/01_data_exploration.ipynb` -- presentation wrapper for provenance, cleanup, alignment, spread preparation, EDA, and handoff dataframe.
- `notebooks/README.md` -- notebook purpose, real/fixture modes, execution commands, and modelling handoff boundary.
- `pyproject.toml` / `uv.lock` -- minimal optional notebook execution dependencies; core/test installs remain unchanged.
- `tests/integration/test_data_exploration_notebook.py` -- validates notebook structure and executes pure-Python cells in fixture mode.
- `src/energy_trading_pipeline/data_ingestion/local_loader.py` -- existing CSV/Parquet loader used by the notebook.
- `src/energy_trading_pipeline/preprocessing/` -- existing normalization, cleaning, validation, alignment, and spread functions used rather than reimplemented.

## Tasks & Acceptance

**Execution:**
- [x] `notebooks/01_data_exploration.ipynb` -- add markdown and code sections for research question/data lineage, mode configuration, loading, schema inspection, timestamp normalization, quality summaries, cleanup reports, exact hourly alignment, spread calculation, descriptive analysis, price/spread plots, missingness and distribution plots, weather summaries/correlations, DST explanation, final dataframe audit, and limitations.
- [x] `notebooks/README.md` -- document the single current notebook, local real-data prerequisites, fixture mode, Run All commands, and that modelling follows in a later notebook.
- [x] `pyproject.toml`, `uv.lock` -- add `nbconvert` and `ipykernel` as an optional `notebook` dependency group so kernel execution is reproducible without expanding the core environment.
- [x] `tests/integration/test_data_exploration_notebook.py` -- parse the notebook and execute all pure-Python code cells sequentially in fixture mode with a headless plotting backend; assert the prepared dataframe has chronological unique timestamps, a correct spread, expected weather coverage, and no missing required values.

**Acceptance Criteria:**
- Given the cached real artifacts, when the notebook runs in default mode, then it accounts for all 8,784 hourly price records and shows exact weather timestamp agreement before joining.
- Given valid negative or extreme electricity prices, when cleanup runs, then those observations remain present and the notebook explains why they are not treated as missing data or automatically removed.
- Given the aligned sources, when preprocessing completes, then `prepared_data` has unique chronological UTC timestamps, finite `price_de`, `price_fr`, and `spread`, no missing retained weather values, and verifies the spread formula numerically.
- Given fixture mode and the normal test environment, when the integration test executes every code cell, then it completes without credentials, network access, or real datasets and validates the same preprocessing invariants.
- Given an evaluator reads the notebook, when reaching the final section, then the cleanup decisions, DST treatment, weather geography/aggregation, ERA5 reanalysis limitation, and boundary before modelling are explicit.

## Design Notes

The full-year price artifact represents the 2024 German/French local market calendar in UTC, from `2023-12-31T23:00:00Z` through `2024-12-31T22:00:00Z`. It is not a complete UTC calendar year, so the real-data path must validate direct one-to-one timestamp equality rather than call the date-only `align_hourly_data` API with UTC dates. Fixture mode should exercise `normalize_timestamps`, `clean_records`, `align_hourly_data`, and `calculate_spread`; real mode should reuse the already validated artifacts, rerun quality checks, and make the exact merge assertion visible. Same-hour weather is valid for retrospective EDA but must be labeled as unavailable to a historical day-ahead forecast unless lagged or replaced by forecast vintages.

## Verification

**Commands:**
- `uv lock --check` -- expected: lockfile matches `pyproject.toml`.
- `uv run pytest tests/integration/test_data_exploration_notebook.py -q` -- expected: structure and offline fixture Run All pass.
- `uv run --extra notebook jupyter nbconvert --to notebook --execute --output /tmp/01_data_exploration.executed.ipynb notebooks/01_data_exploration.ipynb` -- expected: default real-data execution completes locally.
- `uv run pytest -q` -- expected: existing default test suite remains green.

## Spec Change Log
