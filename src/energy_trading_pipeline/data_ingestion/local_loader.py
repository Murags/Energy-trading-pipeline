"""Local CSV and Parquet data loading utilities."""

import logging
from pathlib import Path

import pandas as pd


LOGGER = logging.getLogger(__name__)


def load_local_data(data_path: Path) -> pd.DataFrame:
    """
    Load a local CSV or Parquet dataset.

    Args:
        data_path: Path to a local CSV or Parquet file.

    Returns:
        The loaded dataset.

    Raises:
        FileNotFoundError: If the path does not point to a file.
        ValueError: If the file extension is not supported.
    """
    path = Path(data_path)
    if not path.is_file():
        raise FileNotFoundError(f"Local data file not found: {path}")

    if path.suffix.lower() == ".csv":
        dataframe = pd.read_csv(path)
    elif path.suffix.lower() == ".parquet":
        dataframe = pd.read_parquet(path)
    else:
        raise ValueError(
            "Unsupported local data format "
            f"'{path.suffix}'. Supported formats are: .csv, .parquet."
        )

    LOGGER.info("Loaded local data from %s (%d rows)", path, len(dataframe))
    return dataframe
