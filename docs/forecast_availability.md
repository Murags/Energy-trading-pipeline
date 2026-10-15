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
