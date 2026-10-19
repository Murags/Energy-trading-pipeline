# Proposal alignment and model training assessment

## Hand-off Brief

The repository has a substantial tested local pipeline, but its central three-strategy research experiment is incomplete. The training notebook implements a documented one-hour-ahead benchmark, and the backtest stops when a policy requests refitting. Resolve forecast-time information availability and complete actual retraining before drawing research conclusions or sizing an AWS deployment.

## Case Info

- Date opened: 2026-10-10
- Status: Concluded
- Reference: `project_agent_context.tex`
- Baseline: commit `921976f`; the proposal file was untracked before this investigation.
- Scope: proposal alignment, training correctness, feature availability, backtesting, retraining, and evidence supporting research conclusions.

## Problem Statement

The user asks whether the current project, especially model training, correctly implements the proposal, before considering minimal-cost AWS deployment.

## Evidence Inventory

| Source | Status | Notes |
| --- | --- | --- |
| Proposal and approved project documents | Available | Compared proposal, PRD, architecture, stories, and implementation |
| Source code and tests | Available | Reviewed training, features, backtesting, policies, and reporting |
| Notebook implementation | Available | Documents a one-hour-ahead benchmark |
| Notebook numerical outputs | Missing | Current notebook has empty outputs and null execution counts |
| Persisted experiment artifacts | Partial | Real datasets and a small saved development model exist; no saved three-strategy comparison found in reports |
| Fixture test results | Available | `uv run pytest -q`: 1,221 passed, 31 deselected in 39.07 seconds |

## Investigation Backlog

1. Done: compare proposal with approved scope and implemented stages.
2. Done: trace training and forecast-time feature availability.
3. Done: check backtest integration and saved research results.
4. Done: run default fixture tests and summarize evidence limits.
5. Future implementation: define issuance protocol, prepare availability-aware artifacts, and implement actual refitting.
6. Future experiment: freeze calibration choices and persist the controlled comparison.

## Hypothesized Paths

### Hypothesis 1

- Status: Refuted for the currently available evidence
- Theory: the present training results substantiate the proposal's day-ahead forecasting and retraining claims.
- Would confirm: matching forecast issue times and information sets plus a persisted controlled three-strategy comparison.
- Would refute: different forecast horizon or missing comparison evidence.
- Resolution: the notebook explicitly describes one-hour-ahead accuracy, the runner does not execute requested retraining, and full comparative results are absent.

## Confirmed Findings

### 1. Model fitting has useful safeguards, but the notebook evaluates a different horizon

Chronological training and validation, positive lags, shifted rolling features, exclusion of contemporaneous price columns, and model feature-order persistence are implemented. The notebook also provides previous-hour and previous-day persistence comparisons. These are sound building blocks.

However, `configs/experiment_2022_2025.yaml:20` selects lag 1 and lag 24, and `notebooks/03_model_training_validation.ipynb:746` explicitly describes one-hour-ahead evaluation using observed previous-hour values. Such features cannot simply be reused for every row of a next-day forecast issued together: their availability must be assessed at the common forecast issue time. The notebook already acknowledges the limitation; presenting its scores as completed day-ahead validation would be unsupported.

### 2. Retraining decisions are implemented separately from retraining execution

`src/energy_trading_pipeline/backtesting/backtest_runner.py:69` restricts the CLI to `no_retraining`. At line 324, a positive policy decision raises `NotImplementedError`. `README.md:290` documents this explicitly. Therefore the central question in `project_agent_context.tex:30` cannot yet be answered by the runnable pipeline.

### 3. Real feature artifacts do not yet satisfy the backtest contract

The runner requires explicit predictor selection and availability provenance. `README.md:198` documents `feature_available_at` and `actual_available_at`, and line 204 states that current generated feature artifacts still need these annotations. `configs/experiment_2022_2025.yaml:66` contains no `backtest.feature_columns` and selects `fixed_schedule` at line 74, which the CLI rejects. Adding fabricated availability timestamps would not solve the problem: the predictors must actually have been available at the chosen issue time.

The runner correctly rejects forecast blocks containing unavailable predictors (`backtest_runner.py:287`) and filters policy history by actual availability (`backtest_runner.py:318`). These checks are strengths, not errors to bypass.

### 4. Weather safeguards are inconsistent across entry points

`src/energy_trading_pipeline/features/weather_features.py:29` describes pass-through selection, while `notebooks/03_model_training_validation.ipynb:305` performs weather lagging separately. Calling the package builder directly with the raw weather columns in the experiment configuration does not apply that notebook transformation. Availability handling should be centralized in reusable package code.

`docs/data_sources.md:93` identifies ERA5 as historical reanalysis, not archived day-ahead forecasts. A one-hour shift establishes observation ordering but does not itself establish historical publication availability. This is a methodological evidence gap; exact release latency was not independently verified in this assessment.

### 5. Available numerical evidence is too limited to judge full model quality

The current notebook has no saved numerical outputs (`notebooks/03_model_training_validation.ipynb:500`). The saved model metadata records training on January 2–6, 2023 and validation on January 7–8, with RMSE 0.42598 and MAE 0.20204 (`models/artifacts/model_20260911_153514/metadata.yaml:4`, line 38). These figures are not results from the configured 2022–2025 experiment.

No persisted three-strategy comparison was found in the inspected report directories; they contain placeholders. There is insufficient evidence to quantify overfitting, demonstrate that weather improves accuracy, or establish superiority over persistence or scheduled retraining.

### 6. Calibration and final evaluation need separate roles

`configs/experiment_2022_2025.yaml:15` configures training from January 3, 2022 through December 31, 2024 and validation in 2025. Lines 68–77 also configure backtest evaluation in 2025 and an RMSE threshold of 10.0. This overlap is a design risk if validation results are used to tune parameters or thresholds. No actual test-set tuning was established. The notebook explicitly performs a fixed-parameter single split (`notebooks/03_model_training_validation.ipynb:764`). Freeze settings using a separate earlier calibration period before the final comparison.

### 7. Data and supporting components are ahead of the completed experiment

Real 2022–2025 paired prices and weather exist: each verification artifact records 35,064 hourly rows (`data/processed/run_20261006_072807/verification.json:7`, `data/processed/run_20261006_073531/verification.json:6`). The approved PRD permits a shorter usable range with documentation (`_bmad-output/prds/prd-Energy-trading-pipeline-2026-06-15/prd.md:233`). Grid features are absent from the current configuration (`configs/experiment_2022_2025.yaml:62`). The methodology should state these differences from the proposal.

Evaluation, plotting, dashboard export, dashboard loading, CI, Docker support, optional S3 mirroring, and Terraform scaffolding exist. Their existence does not establish that the research experiment has run. The approved architecture remains local-first with optional AWS (`_bmad-output/architecture.md:75`), whereas the proposal describes a stronger serverless emphasis. Resolve that scope explicitly during the later deployment discussion.

### 8. Default rolling RMSE can suppress every performance trigger at runner decision times

The monitor selects `(decision - 168 hours, decision]` and requires 168 errors by default (`src/energy_trading_pipeline/monitoring/rolling_rmse.py:56`, line 86, line 112). The runner invokes its policy before forecasting the current block, so previous hourly targets end at `decision - 1 hour` (`src/energy_trading_pipeline/backtesting/backtest_runner.py:315`). Even complete history contributes at most 167 targets to that interval. The resulting `NaN` does not exceed the threshold, so the default performance policy cannot trigger under this integration pattern.

A read-only Python reproduction used 336 consecutive hourly errors, each equal to 100, ending at 2025-01-14 23:00 UTC, and a decision at 2025-01-15 00:00 UTC. The default monitor returned `NaN` and the policy returned `False` for threshold 10. Explicitly allowing 167 observations returned RMSE 100, confirming the boundary mechanism. This override was diagnostic, not an implemented fix. Existing tests evaluate at the last observed target (`tests/unit/test_rolling_rmse.py:29`), which differs from the runner's decision timing.

Define the interval consistently with issuance, such as `[decision - window, decision)`, retain actual-availability filtering, and add a test using the runner's history shape. Observation delays and missing actuals must still be handled explicitly.

## Deduced Conclusions

- Training is mechanically reasonable for a historical one-step diagnostic; operational day-ahead validity remains unestablished.
- A 24-hour forecast block alone does not define a day-ahead forecasting protocol. The runner currently uses the first target timestamp as issuance (`backtest_runner.py:316`); the research needs an explicit issue time, information cutoff, delivery-day convention, and DST treatment.
- The current multi-year notebook training window and the configured 90-day backtest window are different experiments. Their metrics should not be treated as directly interchangeable.
- Strong fixture coverage supports implementation reliability within tested contracts. It does not establish predictor publication timing or research effectiveness.

## Missing Evidence

| Gap | Consequence | Next evidence needed |
| --- | --- | --- |
| Issue-time and publication protocol | Day-ahead leakage safety unverified | Explicit issue time and predictor/label availability rules |
| Completed real-data training outputs | Accuracy and overfitting unquantified | Persist train/validation/baseline scores on identical valid timestamps |
| Completed three-strategy run | Research hypothesis untested | Forecasts, metrics, model lineage, completed refit events, and runtimes |
| Threshold calibration rationale | Trigger efficiency cannot be interpreted | Earlier calibration period and frozen threshold/window settings |

## Source Code Trace

Processed observations → notebook weather transformation → feature builder → chronological training window → XGBoost fit → observed-history validation predictions.

Feature Parquet plus availability provenance → backtest preflight → initial model fit/load → available-error policy history → policy decision → either prediction or currently unimplemented refitting.

## Verification

- Executed `uv run pytest -q`: **1,221 passed, 31 deselected, 39.07 seconds**.
- Executed a focused read-only reproduction confirming the rolling-RMSE boundary defect described in Finding 8.
- Default markers exclude slow, external API, and AWS tests.
- No full historical backtest, external data download, or AWS operation was performed.
- No implementation code or configuration was changed. This report is the sole added assessment artifact; the user-provided proposal remains untouched.
- System Python lacked the skill resolver's required Python version; project Python resolved it. uv required approved cache access outside the sandbox.

## Recommended Next Steps

1. Define the actual day-ahead forecast issue time and permissible information set; align price lags, rolling features, and weather to it.
2. Correct and integration-test the rolling-RMSE decision boundary; produce an availability-aware real-data artifact and complete one reproducible static backtest.
3. Implement requested refitting, model promotion/version lineage, and common-timeline execution for all three strategies, one approved story at a time.
4. Freeze model, threshold, rolling window, and training-window choices using an earlier chronological calibration segment.
5. Run the controlled comparison; report RMSE, MAE, completed refit counts, and measured runtime, with valid persistence baselines.
6. Then assess minimal-cost AWS options using measured runtime and artifact volume, retaining the approved local reproducibility path.

## Conclusion

**Confidence: High** for the implementation and artifact gaps; **unverified** for full historical predictive quality. The project is a substantial tested software prototype, but its central forecasting and retraining experiment is not yet complete. The highest-value next work is forecast-time correctness and actual retraining integration, before interpreting model quality or planning cloud execution.

## Follow-up: 2026-10-10

### Acquired data relevance and suitability

The acquired price data is directly relevant to the target. The main research dataset contains 35,064 hourly paired DE-LU and France prices in EUR/MWh covering local calendar years 2022–2025. Germany means the Germany/Luxembourg bidding zone. SMARD is the acquisition provider, with ENTSO-E identified as upstream source; this should be reported accurately rather than claiming direct ENTSO-E API acquisition (`docs/data_sources.md:158`). The target is derived as `price_de - price_fr`; its absence from raw prices is expected.

Independent checks in this follow-up loaded the actual price Parquet and confirmed sorted UTC timestamps, zero missing hours, missing values, or duplicates, and finite prices. All 1,461 local days are covered, including four 23-hour days and four 25-hour days. All 432 raw-response and four export checksums passed; all 70,128 market-price values matched the retained raw JSON exactly. These checks establish faithful acquisition and structural completeness, not independent verification of the upstream market values or historical publication vintages.

The weather artifacts contain four variables at eight locations: temperature, wind at 10 m and 100 m, and shortwave radiation. They yield 32 location variables and eight country aggregates. Independent Parquet inspection confirmed 35,064 unique, complete hourly weather rows, exactly aligned to prices. These are relevant candidate explanatory variables; their incremental predictive benefit has not been measured.

The critical limitation is publication timing. [Open-Meteo's Historical Weather documentation](https://open-meteo.com/en/docs/historical-weather-api) identifies ERA5 as reanalysis and currently documents a five-day update delay. The current one-hour and 24-hour shifts cannot establish availability of this ERA5 product at the historical forecast issue time. Contemporary documentation does not reconstruct every historical data release or revision, so merely choosing a five-day shift would also need a justified availability assumption. Retain ERA5 for exploratory analysis or an explicitly labeled retrospective benchmark; use properly issued weather forecasts, or demonstrably available delayed observations, for the operational day-ahead experiment.

[Open-Meteo's Historical Forecast documentation](https://open-meteo.com/en/docs/historical-forecast-api) warns that its continuous archive stitches the first few hours of successive runs. A dataset named historical forecast is therefore not automatically a day-ahead information set. Any replacement must preserve run/issue time and target time and verify archive coverage before acquisition.

The aggregation is an approximation: four points per country, unweighted temperature means, and selected-region wind/solar weights. In particular, end-2024 German capacity and realized 2024 French generation weights are reused for every year (`data/processed/run_20261006_073531/metadata.json:156`, line 173). Earlier-year point-in-time claims would use later information. For a strict study, use weights available before evaluation begins, time-appropriate weights, or a documented fixed/equal-weight sensitivity check. This affects aggregate predictors; the preserved location-level data remains reusable. Radiation is a preceding-hour mean, while price timestamps mark interval starts, requiring explicit temporal alignment.

Grid/load/generation time series are not in the acquired research inputs, and `configs/experiment_2022_2025.yaml:62` selects no grid columns. Annual regional generation weights are not an hourly grid predictor. This is a gap relative to the proposal's broader feature description, but the retraining-policy question can still be evaluated on a documented common price/calendar feature set. Add grid/weather predictors only with reliable issue-time provenance and identical treatment across strategies.

The period is 2022–2025, not 2020–2025; the proposal and PRD allow availability-driven scope with explicit documentation. From October 2025 the retained hourly series represents aggregated quarter-hour prices, so describe the research target as an hourly spread throughout. [SMARD confirms the October 1, 2025 switch to 15-minute day-ahead products](https://www.smard.de/en/15-minute-wholesale-prices-available-218078); the repository's aggregation check covers the first two weeks after the switch (`docs/data_sources.md:44`), not every late-2025 quarter-hour record.

### Updated conclusion

Keep the acquired prices and raw weather snapshots. Price data supplies the necessary target and history for the research; weather is relevant but not ready for the proposed operational forecast use as currently transformed. Prioritize a defensible information-availability contract over acquiring more variables or more years. No new datasets were downloaded and no pipeline implementation was changed in this follow-up.
