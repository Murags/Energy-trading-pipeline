# Day-ahead forecast availability

The price/calendar experiment issues all hours of the next **Europe/Berlin delivery day at 10:00 local time on the preceding calendar day**. Instants are stored in UTC. Calendar-day arithmetic preserves the 23-hour spring and 25-hour autumn delivery days; ambiguous or nonexistent configured issue times are rejected. This is the approved scientific timing convention for the availability story.

A price is treated as usable only at the end of its delivery hour (`timestamp + 1 hour`). The same convention applies to predictor observations, training labels, and errors visible to policy hooks. Equality at issuance is allowed. This deliberately delays use of known market information; it does **not** reconstruct measured publication times. Acquired prices are historical snapshots and may contain later revisions. The research is therefore an experiment under a conservative usability assumption, not a reconstruction of historical publication vintages.

The initial predictors are price/spread lags of 48 and 168 elapsed hours, 24-hour mean and sample standard deviation shifted by 48 elapsed hours, and local hour/day-of-week/month/weekend indicators. For each target, `feature_available_at` is the latest usability instant among these dependencies; calendar values are deterministic. Each row is checked against its original `forecast_timestamp`, including rows later selected for training. ERA5 and grid predictors are excluded, with acquired datasets preserved.

The preparation command uses the cached paired price artifact, validates complete finite hourly prices, calculates `spread = price_de - price_fr`, and calls the existing feature builders. Only leading warmup is removed (168 rows for the supplied configuration). It saves separate Parquet and YAML metadata, including source and output SHA-256 hashes, the timing contract, predictor list, and disclosure above. Timestamp/provenance fields never enter model fitting. Unsupported predictors and mismatched artifact/config metadata fail clearly.

From the repository root:

```bash
uv run python -m energy_trading_pipeline.cli prepare-day-ahead \
  --config configs/experiment_day_ahead.yaml \
  --paths-config configs/local_paths_day_ahead.yaml

uv run python -m energy_trading_pipeline.cli backtest \
  --config configs/experiment_day_ahead.yaml \
  --paths-config configs/local_paths_day_ahead.yaml \
  --model-params-config configs/model_params.yaml
```

The checked-in path configuration points to the retained 2022–2025 paired price snapshot. Change that input path when using another acquisition. Preparation refuses to replace either output file; use a new feature path for a new preparation. Backtests reserve separate run/model directories and refuse to replace artifacts. Partial failed outputs are retained for diagnosis and must not be treated as complete runs.

The supplied January 1–7, 2025 interval is an **engineering smoke test**, not final evaluation or calibration. XGBoost trains once on 90 elapsed days ending at the start of a held-out seven-day validation window; that validation window ends at first issuance. Later delivery blocks use the same model. Evaluation requires every hour of each requested local delivery day. Logs store explicit issue times and eventual actuals for offline scoring; policy hooks see only prior forecast errors whose actuals are usable at that issuance.

The static run does not tune parameters, calculate the final strategy comparison, fix the rolling-RMSE trigger, or execute refits. Those are subsequent stories. Loaded models must match feature/target/parameter settings and carry a caller-attested upper history bound before first issuance. The older fixed-UTC forecast-window behavior remains available for existing configurations without `backtest.mode: day_ahead`.

Verification covers DST delivery counts, invalid issue times, source gaps/duplicates/nonfinite values, exact usability boundaries, output integrity/no-overwrite, and mutations of observations usable after issuance. Such mutations must leave the issued predictors and XGBoost predictions unchanged, while retrospective actuals may change.

## Rolling RMSE on the day-ahead decision schedule

`calculate_rolling_rmse` selects the elapsed interval `(anchor - window_days, anchor]`. The anchor defaults to the decision instant, which reserves a slot for the target hour at that instant. Under this protocol that hour's actual is usable only at `timestamp + 1 hour`, so the slot can never be filled: a dense seven-day history yields 167 observed errors against a default `min_periods` of 168, the metric stays `NaN`, and `performance_triggered` would remain in warm-up for the whole evaluation.

Pass `available_through`, the newest target whose actual is observable at the decision, to anchor the window on availability instead. `PerformanceTriggeredPolicy` derives it from `retraining.actual_availability_lag_hours`, which this experiment sets to `1` to match the usable-after rule. The default of `0` preserves the earlier contract for configurations without `backtest.mode: day_ahead`.

The anchor follows the decision schedule, never the newest observed row. Missing actuals therefore withhold the metric rather than sliding the window back onto older errors and reporting them as current. Verification reproduces the 167/168 starvation both as arithmetic and through a backtest-runner policy hook, and confirms the anchored metric equals the RMSE of exactly the errors usable at that issuance.

## Executing retraining

A positive policy decision now refits rather than aborting. The refit fits a fresh model on that window's training interval using the same configuration, predictor list, and availability rules as the initial fit, so the three strategies differ only in *when* they refit. Supplying a policy preflights every candidate training window before any artifact is written, so an unusable refit fails fast rather than part-way through a run.

Each refit is saved as `<model_version>_refit_NNN.json` beside the initial `model.json`, and later blocks are logged under that version, so `forecasts.parquet` carries model lineage. `model.json` always remains the initial fit identified by the run's `model_version`. Every run writes `retraining_events.parquet` with the canonical columns, empty when nothing refit, and records `model_versions` and `retraining_event_count` in run metadata.

Refit training windows end at or before the issuance that requested them, and are checked for predictor and label availability exactly as the initial window is. Verification confirms that mutating prices usable only after an issuance leaves that issuance's refit, predictors, and predictions unchanged.

A retraining *event* is a completed refit, not a request. Policy hooks may log requests separately; the runner's `refit_logger` fires only after a model has actually been fitted and saved.
