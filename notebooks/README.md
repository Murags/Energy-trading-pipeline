# Notebooks

Notebooks are presentation wrappers. Reusable pipeline logic remains under
`src/energy_trading_pipeline/` and is imported rather than reimplemented.

## Data Exploration And Preprocessing

`01_data_exploration.ipynb` presents the data preparation workflow from cached
inputs to the modelling handoff dataframe, `prepared_data`. It covers source
lineage, schema and coverage inspection, explicit cleanup audits, exact hourly
price/weather synchronization, spread calculation, descriptive exploration,
daylight-saving-time behavior, and limitations. It does not download data,
engineer forecast features, train a model, or export a new canonical dataset.

The default `real` mode requires these local, Git-ignored artifacts:

```text
data/processed/run_20260911_053845/prices_de_fr.parquet
data/processed/run_20260911_053845/metadata.json
data/processed/run_20260913_132539/weather_2024_locations.parquet
data/processed/run_20260913_132539/weather_2024_country_aggregates.parquet
data/processed/run_20260913_132539/metadata.json
```

Install the optional notebook environment and run all cells from the repository
root:

```bash
uv sync --extra notebook
uv run --extra notebook jupyter nbconvert \
  --to notebook --execute \
  --output /tmp/01_data_exploration.executed.ipynb \
  notebooks/01_data_exploration.ipynb
```

For an offline fixture execution that needs no credentials, network, or real
data, set the mode explicitly:

```bash
ETP_NOTEBOOK_MODE=fixture uv run --extra notebook jupyter nbconvert \
  --to notebook --execute \
  --output /tmp/01_data_exploration.fixture.executed.ipynb \
  notebooks/01_data_exploration.ipynb
```

## Data Preprocessing

`02_data_preprocessing.ipynb` presents the preprocessing transformations
themselves, stage by stage, printing the dataframe each one produced: raw
source records, the pre-clean quality scan that justifies the cleaning rules,
UTC timestamp normalization, `clean_records` duplicate and missing-value
policies (including the removed duplicate rows side by side), the join that
combines energy and weather into one hourly dataframe with per-column
provenance, the `spread` target, final validation, and a round-tripped
`save_processed_data` artifact. It writes its Parquet output to a temporary
directory, so running it never overwrites anything under `data/processed/`.

It reads the same `real` mode artifacts as notebook 01, minus the two
`metadata.json` files, and supports the same `fixture` mode:

```bash
uv run --extra notebook jupyter nbconvert \
  --to notebook --execute \
  --output /tmp/02_data_preprocessing.executed.ipynb \
  notebooks/02_data_preprocessing.ipynb

ETP_NOTEBOOK_MODE=fixture uv run --extra notebook jupyter nbconvert \
  --to notebook --execute \
  --output /tmp/02_data_preprocessing.fixture.executed.ipynb \
  notebooks/02_data_preprocessing.ipynb
```

Both notebooks print `rows x columns` plus the leading rows of every stage
dataframe. Set `ETP_NOTEBOOK_PREVIEW_ROWS` to change how many rows appear.

## Handoff

The next notebook may use `prepared_data` for leakage-safe feature engineering
and modelling. Same-hour ERA5 values shown in these notebooks are valid for
retrospective exploration only; they must be lagged or replaced with archived
forecast vintages before forecast evaluation.

## Model Training And Validation

`03_model_training_validation.ipynb` presents baseline XGBoost training on the
configured chronological split. It trains through `train_baseline`, the same
function as the `train` CLI command, reloads the saved artifact and reproduces
its recorded RMSE and MAE, then shows validation plots, residuals, persistence
reference baselines, gain feature importance, and a read-only view of the saved
model registry. The model, registry entry, and run log it produces go to a
temporary directory, and a final guard cell asserts that `models/` and
`logs/runs` are unchanged. Use the CLI for a recorded training run.

The default `real` mode uses the 2022-2025 artifacts listed in
`configs/local_paths_2022_2025.yaml` (prices from `run_20261006_072807`,
country weather from `run_20261006_073531`; see `docs/data_sources.md`) with
`configs/experiment_2022_2025.yaml`: training January 3, 2022 to December 31,
2024, validation on all of 2025. It builds the feature dataset and writes it to
`data/features/feature_dataset_2022_2025.parquet` plus a metadata sidecar,
replacing any previous copy, so the `train` CLI can reuse it with the same two
configs. ERA5 weather enters only as 1-hour and 24-hour lags, never at the
target hour. `fixture` mode runs the same stages on the repository fixtures and
writes only to a temporary directory:

```bash
uv run --extra notebook jupyter nbconvert \
  --to notebook --execute \
  --output /tmp/03_model_training_validation.executed.ipynb \
  notebooks/03_model_training_validation.ipynb

ETP_NOTEBOOK_MODE=fixture uv run --extra notebook jupyter nbconvert \
  --to notebook --execute \
  --output /tmp/03_model_training_validation.fixture.executed.ipynb \
  notebooks/03_model_training_validation.ipynb
```

Validation in this notebook is one-step-ahead because the feature set includes
1-hour lags. Day-ahead forecast accuracy and the retraining-strategy comparison
come from the `backtest` command.
