## Coding Style Guide

### General Python Style

Agents must write clear, simple, maintainable Python code.

Use:

* Python 3.11+ syntax.
* `snake_case` for files, modules, functions, variables, and dataframe columns.
* `PascalCase` for classes.
* `UPPER_SNAKE_CASE` for constants.
* Type hints for public functions and important internal functions.
* Docstrings for modules, classes, and non-trivial functions.
* Small functions with one clear responsibility.
* Explicit inputs and outputs instead of hidden global state.

Avoid:

* Overly clever code.
* Large functions that mix multiple pipeline stages.
* Hard-coded paths, dates, thresholds, or model parameters.
* Silent failures.
* Broad `except Exception` blocks unless the error is logged and re-raised or handled clearly.
* Adding new dependencies without a clear need.

---

### Formatting

Code should be compatible with `black` formatting conventions.

Preferred defaults:

```text
line length: 88
indentation: 4 spaces
quote style: double quotes where practical
```

Imports should be grouped in this order:

```python
# Standard library imports
from pathlib import Path
from typing import Any

# Third-party imports
import pandas as pd
import numpy as np

# Local imports
from energy_trading_pipeline.config.loader import load_config
```

Do not use wildcard imports.

Avoid:

```python
from module import *
```

Prefer explicit imports:

```python
from energy_trading_pipeline.monitoring.metrics import calculate_rmse
```

---

### Function Design

Functions should do one thing clearly.

Prefer this:

```python
def calculate_spread(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate German-French electricity price spread."""
    result = df.copy()
    result["spread"] = result["price_de"] - result["price_fr"]
    return result
```

Avoid this:

```python
def process_everything():
    # loads data, cleans data, creates features, trains model, saves plots
    ...
```

Pipeline stages should be separated into different modules:

```text
data_ingestion → preprocessing → features → models → backtesting → retraining → evaluation
```

---

### Type Hints

Use type hints for function arguments and return values.

Preferred:

```python
from pathlib import Path

def load_yaml_config(config_path: Path) -> dict:
    """Load a YAML configuration file."""
    ...
```

For pandas-heavy code, use:

```python
def build_lag_features(df: pd.DataFrame, lags: list[int]) -> pd.DataFrame:
    ...
```

Do not overcomplicate typing if it reduces readability.

---

### Docstrings

Use short docstrings for public functions, classes, and modules.

Preferred:

```python
def calculate_rmse(actual: pd.Series, prediction: pd.Series) -> float:
    """Calculate root mean squared error between actual and predicted values."""
    ...
```

For more complex functions, include purpose, arguments, and return value:

```python
def generate_backtest_windows(
    start_date: str,
    end_date: str,
    train_window_days: int,
    forecast_horizon_hours: int,
) -> list[dict]:
    """
    Generate chronological backtest windows.

    Args:
        start_date: First evaluation date.
        end_date: Last evaluation date.
        train_window_days: Number of historical days used for training.
        forecast_horizon_hours: Forecast horizon in hours.

    Returns:
        A list of dictionaries describing training and forecast windows.
    """
    ...
```

---

### Path Handling

Use `pathlib.Path` for filesystem paths.

Preferred:

```python
from pathlib import Path

output_path = Path("data/features/feature_dataset.parquet")
output_path.parent.mkdir(parents=True, exist_ok=True)
```

Avoid string path concatenation:

```python
output_path = "data/" + folder + "/" + filename
```

All important paths should come from config or path resolver utilities.

---

### Dataframe Style

All dataframe columns must use `snake_case`.

Do not mutate input dataframes in place unless the function name and docstring make that clear.

Preferred:

```python
def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add calendar features without mutating the input dataframe."""
    result = df.copy()
    result["hour"] = result["timestamp"].dt.hour
    result["day_of_week"] = result["timestamp"].dt.dayofweek
    return result
```

Avoid chained assignment:

```python
df[df["price_de"] > 0]["spread"] = df["price_de"] - df["price_fr"]
```

Prefer explicit assignment:

```python
result = df.copy()
result["spread"] = result["price_de"] - result["price_fr"]
```

Always preserve chronological order when working with time series:

```python
df = df.sort_values("timestamp").reset_index(drop=True)
```

---

### Time and Timestamp Handling

Timestamp handling must be explicit.

Rules:

* Parse timestamps using pandas datetime utilities.
* Normalize modelling timestamps consistently, preferably to UTC.
* Preserve source timezone metadata where useful.
* Sort by `timestamp` before feature generation, splitting, backtesting, or rolling calculations.
* Never assume timestamps are already clean.
* Document daylight-saving-time handling in metadata or logs.

Preferred:

```python
df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
df = df.sort_values("timestamp").reset_index(drop=True)
```

---

### Leakage-Safe Feature Style

Lag and rolling features must be leakage-safe.

Lag features must shift before use:

```python
result["spread_lag_24"] = result["spread"].shift(24)
```

Rolling features should use shifted values when predicting the current timestamp:

```python
result["spread_rolling_mean_24"] = (
    result["spread"]
    .shift(1)
    .rolling(window=24)
    .mean()
)
```

Avoid:

```python
result["spread_rolling_mean_24"] = result["spread"].rolling(window=24).mean()
```

unless the feature is explicitly valid for the forecast horizon and documented.

---

### Error Handling

Fail clearly for required inputs.

Preferred:

```python
required_columns = {"timestamp", "price_de", "price_fr"}

missing_columns = required_columns - set(df.columns)
if missing_columns:
    raise ValueError(f"Missing required columns: {sorted(missing_columns)}")
```

For optional columns, warn and continue:

```python
if "temperature" not in df.columns:
    logger.warning("Optional weather column missing: temperature")
```

Do not silently drop important data.

---

### Logging Style

Use the project logging utility once available.

Logs should include:

* stage name
* run ID
* date range where relevant
* strategy where relevant
* model version where relevant
* error or warning details

Preferred style:

```python
logger.info(
    "feature_dataset_created",
    extra={
        "run_id": run_id,
        "rows": len(feature_df),
        "columns": list(feature_df.columns),
    },
)
```

If structured logging is not yet implemented, use clear plain logging messages and keep the call sites easy to upgrade later.

---

### Configuration Style

Do not hard-code experiment settings in code.

Avoid:

```python
rolling_window_days = 7
threshold = 12.5
```

Prefer:

```python
rolling_window_days = config["retraining"]["rolling_rmse_window_days"]
threshold = config["retraining"]["rolling_rmse_threshold"]
```

Reasonable defaults may exist in config files, not hidden inside implementation logic.

---

### Testing Style

Use `pytest`.

Every important module should have tests.

Tests should be small, deterministic, and fixture-based.

Test files should follow:

```text
test_<module_name>.py
```

Preferred test style:

```python
def test_calculate_spread_creates_expected_values(sample_price_df):
    result = calculate_spread(sample_price_df)

    assert "spread" in result.columns
    assert result.loc[0, "spread"] == result.loc[0, "price_de"] - result.loc[0, "price_fr"]
```

Tests should not require:

* ENTSO-E credentials
* AWS credentials
* network access
* full 2020-2025 data
* long-running backtests

Use pytest markers for:

```text
external_api
aws
slow
```

---

### CLI Style

CLI commands should be clear and reproducible.

Preferred pattern:

```bash
python -m energy_trading_pipeline.cli <command> --config configs/experiment.yaml
```

CLI commands should:

* accept a config path
* print or log the run ID
* write outputs to the configured artifact locations
* fail clearly when required files are missing
* not require API or AWS credentials unless the command explicitly performs API or AWS work

---

### Dependency Style

Do not add new dependencies unless they are necessary.

Before adding a dependency, consider whether the standard library or existing dependencies are sufficient.

Allowed core dependencies include:

```text
pandas
numpy
scikit-learn
xgboost
pyarrow
pyyaml
matplotlib
plotly
pytest
streamlit
```

Optional dependencies for AWS or development tooling should remain optional.

Do not introduce:

```text
sagemaker
airflow
kubernetes
spark
mlflow
great_expectations
pandera
```

unless explicitly approved later.

---

### Commit and Branch Style

Use story-based branches:

```text
feature/story-1-1-project-skeleton
feature/story-1-2-dependency-environment
feature/story-1-3-config-loader
```

Use concise commit messages:

```text
story-1.1: create project skeleton
story-1.2: add dependency and environment files
story-1.3: implement yaml config loader
```

Each pull request should link to one story where possible.

---

### Code Review Checklist

Before completing a story, confirm:

```text
Code follows project naming conventions.
Reusable logic is under src/.
No core logic exists only in notebooks.
Configurable values are not hard-coded.
Tests were added or updated.
Relevant tests pass.
No future story scope was implemented.
No secrets were committed.
No AWS/API dependency was introduced accidentally.
Time-series ordering and leakage-prevention rules were preserved.
Generated artifacts are written to the correct folders.
```
