"""Optional grid predictor selection for the feature dataset."""

from collections.abc import Sequence
from typing import Any

import pandas as pd

from energy_trading_pipeline.features.optional_features import (
    select_optional_features,
)

GRID_STAGE = "features.grid"
# Load and generation are the optional ENTSO-E grid series; ingesting them is
# not required for a local run, so an empty selection is normal.
DEFAULT_GRID_COLUMNS: tuple[str, ...] = (
    "load_de",
    "load_fr",
    "generation_de",
    "generation_fr",
)


def build_grid_features(
    df: pd.DataFrame,
    *,
    columns: Sequence[str] = DEFAULT_GRID_COLUMNS,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Select the configured grid predictors and report unavailable ones.

    Load and generation series are passed through from the aligned processed
    dataset and cast to ``float64``. Grid ingestion is optional, so requested
    columns that were never ingested warn and are excluded from
    ``selected_columns`` instead of failing the run; ``columns=[]`` requests no
    grid predictors at all. See
    :func:`energy_trading_pipeline.features.optional_features.select_optional_features`
    for the usability rules and metadata contents.
    """
    return select_optional_features(df, columns, group="grid", stage=GRID_STAGE)
