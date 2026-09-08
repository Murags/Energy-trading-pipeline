"""Optional weather predictor selection for the feature dataset."""

from collections.abc import Sequence
from typing import Any

import pandas as pd

from energy_trading_pipeline.features.optional_features import (
    select_optional_features,
)

WEATHER_STAGE = "features.weather"
# The Open-Meteo variables the ingestion layer caches, in canonical form.
DEFAULT_WEATHER_COLUMNS: tuple[str, ...] = (
    "temperature_2m_c",
    "wind_speed_10m_m_s",
    "shortwave_radiation_w_m2",
)


def build_weather_features(
    df: pd.DataFrame,
    *,
    columns: Sequence[str] = DEFAULT_WEATHER_COLUMNS,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Select the configured weather predictors and report unavailable ones.

    Weather variables are passed through from the aligned processed dataset,
    which already excludes optional columns with missing hourly values, so this
    decides which of the configured columns are usable and casts them to
    ``float64``. Unavailable columns warn and are excluded from
    ``selected_columns`` instead of failing the run; ``columns=[]`` requests no
    weather predictors at all. See
    :func:`energy_trading_pipeline.features.optional_features.select_optional_features`
    for the usability rules and metadata contents.
    """
    return select_optional_features(
        df, columns, group="weather", stage=WEATHER_STAGE
    )
