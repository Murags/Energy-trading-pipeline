"""Canonical German-French spread and processed hourly artifact persistence."""

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_complex_dtype, is_numeric_dtype
import yaml

from energy_trading_pipeline.preprocessing.validation import (
    summarize_records,
    validate_hourly_index,
)


def calculate_spread(df: pd.DataFrame) -> pd.DataFrame:
    """Return a sorted UTC copy with ``spread = price_de - price_fr``.

    Require nonempty, aligned hourly data with aware timestamps and finite real
    numeric prices. Negative prices are valid. Preserve optional columns and
    recompute any existing spread. Never fill missing hours or price values.
    """
    if not df.columns.is_unique:
        raise ValueError("Duplicate column names are not supported")
    missing = sorted({"timestamp", "price_de", "price_fr"} - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    summarize_records(df)
    result = df.copy()
    result["timestamp"] = result["timestamp"].dt.tz_convert("UTC")
    result = result.sort_values("timestamp").reset_index(drop=True)
    if not validate_hourly_index(result["timestamp"])["is_hourly"]:
        raise ValueError("Expected unique, contiguous hourly timestamps; align first")

    prices = {}
    for column in ("price_de", "price_fr"):
        values = result[column]
        if (
            not is_numeric_dtype(values.dtype)
            or is_bool_dtype(values.dtype)
            or is_complex_dtype(values.dtype)
            or values.isna().any()
        ):
            raise ValueError(f"{column} must contain finite real numeric prices")
        # Float arithmetic prevents unsigned subtraction and integer overflow.
        prices[column] = values.astype("float64")
        if not np.isfinite(prices[column]).all():
            raise ValueError(f"{column} must contain finite real numeric prices")
    with np.errstate(over="ignore", invalid="ignore"):
        result["spread"] = prices["price_de"] - prices["price_fr"]
    if not np.isfinite(result["spread"]).all():
        raise ValueError("spread calculation produced non-finite values")
    return result


def save_processed_data(
    df: pd.DataFrame,
    output_path: Path,
    *,
    source_files: dict[str, str | Path],
    alignment_metadata: dict[str, Any] | None = None,
) -> tuple[Path, Path]:
    """Calculate spread and write Parquet plus a ``.metadata.yaml`` sidecar.

    Pass the configured processed path and all contributing source paths keyed
    by source name (at least ``price_de`` and ``price_fr``). Provenance is caller
    supplied; raw files are not reopened. Optional alignment metadata is retained
    under ``alignment``. Existing processed artifacts at these paths are replaced.
    Return the Parquet and metadata paths; metadata bounds describe saved rows.
    """
    output_path = Path(output_path)
    if output_path.suffix.lower() != ".parquet":
        raise ValueError("Processed output_path must have a .parquet suffix")
    if not {"price_de", "price_fr"}.issubset(source_files) or any(
        not isinstance(path, (str, Path)) or not str(path).strip()
        for path in source_files.values()
    ):
        raise ValueError("source_files requires nonempty price_de and price_fr paths")
    result = calculate_spread(df)
    metadata_path = output_path.with_suffix(".metadata.yaml")
    metadata = {
        "stage": "preprocessing",
        "source_files": {name: str(path) for name, path in source_files.items()},
        "date_range": {
            "start": result["timestamp"].iloc[0].isoformat(),
            "end": result["timestamp"].iloc[-1].isoformat(),
        },
        "timezone": "UTC",
        "target_column": "spread",
        "spread_formula": "price_de - price_fr",
        "output_rows": len(result),
        "columns": result.columns.tolist(),
        "artifact_paths": {
            "processed_data": str(output_path),
            "metadata": str(metadata_path),
        },
        "alignment": alignment_metadata if alignment_metadata is not None else {},
    }
    metadata_text = yaml.safe_dump(metadata, sort_keys=False)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(output_path, index=False)
    metadata_path.write_text(metadata_text, encoding="utf-8")
    return output_path, metadata_path
