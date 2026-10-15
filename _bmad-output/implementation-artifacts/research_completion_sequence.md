# Research completion sequence

Approved by the user on 2026-10-10. Execute one story at a time, retaining XGBoost and the canonical three strategies. AWS planning follows the local research experiment.

1. **Forecast-time availability — specification drafted.** See `spec-day-ahead-availability.md`. Establish explicit issue time, delivery-day boundaries, and a reproducible conservative price/calendar information set.
2. **Rolling RMSE boundary — pending first story.** Align metric boundaries and readiness to the implemented decision schedule; reproduce the 167/168 defect and add runner-shaped integration coverage.
3. **Actual refitting — pending RMSE correction.** Execute policy decisions, persist completed refit events and model lineage, and orchestrate identical evaluation timelines for all three strategies.
4. **Calibration — pending executable comparison.** Separate earlier development/calibration from final evaluation, document prior inspection of 2025 diagnostics, and freeze model parameters, threshold, history, and monitoring choices before final results.
5. **Saved comparison — pending frozen protocol.** Run all strategies using identical data/features/model parameters and target timestamps; save forecasts, RMSE/MAE, completed retraining counts, runtime, configuration, and report exports.

Each subsequent story must be concretely specified and checked against the approved PRD and architecture before implementation. The short first-story smoke run is engineering verification, not the final research experiment.
