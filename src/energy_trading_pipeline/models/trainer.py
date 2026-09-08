"""Chronological training window selection for model fitting."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
import logging
from typing import Any

import pandas as pd


logger = logging.getLogger(__name__)

TARGET_COLUMN = "spread"
TIMESTAMP_COLUMN = "timestamp"
# The four window bounds are read from the `dates` section of the experiment
# config so every strategy trains and validates on the same declared ranges.
REQUIRED_WINDOW_CONFIG_KEYS: tuple[str, ...] = (
    "train_start_date",
    "train_end_date",
    "validation_start_date",
    "validation_end_date",
)
# The dataset carries hourly timestamps but the window is declared in whole
# days, so each bound covers its full calendar day in UTC.
DATE_FORMAT = "%Y-%m-%d"


@dataclass(frozen=True)
class TrainingWindow:
    """A reusable chronological train/validation window declared in whole days.

    Both ranges are inclusive of their end date, so a window ending
    `2023-01-06` covers every hourly row through `2023-01-06T23:00`. The
    training range must end strictly before the validation range begins, which
    is what keeps a fitted model from ever seeing a row it is later scored on.

    Construct from the `dates` section of the experiment config with
    `from_config`, or directly with explicit bounds when a caller derives its
    own windows, as backtesting and retraining do when they walk forward.
    """

    train_start_date: date
    train_end_date: date
    validation_start_date: date
    validation_end_date: date

    def __post_init__(self) -> None:
        """Normalize each bound to a `date` and reject a non-chronological window.

        Raises:
            ValueError: If a bound is not a valid `YYYY-MM-DD` date, if either
                range ends before it starts, or if the ranges overlap.
        """
        for field_name in REQUIRED_WINDOW_CONFIG_KEYS:
            object.__setattr__(
                self,
                field_name,
                _parse_date(getattr(self, field_name), field_name),
            )
        self._validate_chronology()

    @classmethod
    def from_config(cls, dates_config: Mapping[str, Any]) -> "TrainingWindow":
        """
        Build a window from the `dates` section of the experiment config.

        All four window keys are required. They are not defaulted from
        `dates.start_date` and `dates.end_date`, because an implied split point
        would silently decide which rows a model is scored on.

        Raises:
            ValueError: If `dates_config` is not a mapping, if a window key is
                missing, or if the resulting window is not chronological.
        """
        if not isinstance(dates_config, Mapping):
            raise ValueError(
                "dates_config must be the 'dates' mapping of the experiment config"
            )

        missing = [key for key in REQUIRED_WINDOW_CONFIG_KEYS if key not in dates_config]
        if missing:
            raise ValueError(
                f"Missing required training window key(s) in the 'dates' config "
                f"section: {missing}. Required: {list(REQUIRED_WINDOW_CONFIG_KEYS)}"
            )

        window = cls(**{key: dates_config[key] for key in REQUIRED_WINDOW_CONFIG_KEYS})
        window._warn_if_outside_configured_range(dates_config)
        return window

    def as_metadata(self) -> dict[str, str]:
        """Serializable window bounds for run and model registry metadata."""
        return {
            field_name: getattr(self, field_name).strftime(DATE_FORMAT)
            for field_name in REQUIRED_WINDOW_CONFIG_KEYS
        }

    def _validate_chronology(self) -> None:
        """Fail when either range is inverted or the two ranges overlap."""
        if self.train_end_date < self.train_start_date:
            raise ValueError(
                f"train_end_date ({_format(self.train_end_date)}) must not precede "
                f"train_start_date ({_format(self.train_start_date)})"
            )
        if self.validation_end_date < self.validation_start_date:
            raise ValueError(
                f"validation_end_date ({_format(self.validation_end_date)}) must not "
                f"precede validation_start_date "
                f"({_format(self.validation_start_date)})"
            )
        # Equal dates are an overlap too: both ranges are end-inclusive, so a
        # shared boundary day would put the same hourly rows on both sides.
        if self.train_end_date >= self.validation_start_date:
            raise ValueError(
                f"Training and validation ranges overlap: train_end_date "
                f"({_format(self.train_end_date)}) must be strictly before "
                f"validation_start_date ({_format(self.validation_start_date)}). "
                "Training rows must precede validation rows so the model is never "
                "fitted on a row it is scored on."
            )

    def _warn_if_outside_configured_range(
        self, dates_config: Mapping[str, Any]
    ) -> None:
        """Warn when the window reaches outside the configured data range.

        Not an error: the window is still chronological, and the selection
        itself reports the rows it actually found.
        """
        bounds = {
            key: _parse_date(dates_config[key], f"dates.{key}")
            for key in ("start_date", "end_date")
            if key in dates_config
        }
        if "start_date" in bounds and self.train_start_date < bounds["start_date"]:
            logger.warning(
                "train_start_date (%s) precedes dates.start_date (%s); the training "
                "range reaches outside the configured data range",
                _format(self.train_start_date),
                _format(bounds["start_date"]),
            )
        if "end_date" in bounds and self.validation_end_date > bounds["end_date"]:
            logger.warning(
                "validation_end_date (%s) follows dates.end_date (%s); the "
                "validation range reaches outside the configured data range",
                _format(self.validation_end_date),
                _format(bounds["end_date"]),
            )


@dataclass(frozen=True)
class TrainingSplit:
    """Feature and target arrays for one chronological train/validation window.

    Both sides carry the same feature columns in the same order, so the arrays
    can be handed to `XGBoostSpreadModel.fit` and `predict` without further
    alignment. Timestamps are returned alongside because the feature frames
    exclude them, and forecast logging needs the row identity back.
    """

    train_features: pd.DataFrame
    train_target: pd.Series
    validation_features: pd.DataFrame
    validation_target: pd.Series
    train_timestamps: pd.Series
    validation_timestamps: pd.Series
    feature_columns: list[str]
    target_column: str
    window: TrainingWindow
    metadata: dict[str, Any] = field(default_factory=dict)


def select_training_window(
    df: pd.DataFrame,
    window: TrainingWindow,
    *,
    target_column: str = TARGET_COLUMN,
    feature_columns: Sequence[str] | None = None,
) -> TrainingSplit:
    """
    Select the training and validation rows of a feature dataset by date range.

    Rows are matched on `timestamp` against the window's end-inclusive calendar
    days and returned in chronological order. Every training row precedes every
    validation row, which is verified against the selected rows rather than
    assumed from the declared bounds.

    `feature_columns` defaults to every column of `df` except `timestamp` and
    the target, in frame order. Passing it explicitly pins the feature contract,
    which is what a retraining run needs to keep matching an existing model. The
    input frame is not mutated.

    Raises:
        ValueError: If `df` is not a feature dataset with a `timestamp` and
            target column, if `window` is not a `TrainingWindow`, if a requested
            feature column is missing or reserved, if there is no feature
            column, or if either range selects no rows.
    """
    if not isinstance(window, TrainingWindow):
        raise ValueError(
            "window must be a TrainingWindow; build one with "
            "TrainingWindow.from_config(config['dates'])"
        )
    if not isinstance(df, pd.DataFrame):
        raise ValueError("df must be a pandas DataFrame feature dataset")

    target_column = _validate_target_column(target_column)
    missing_columns = [
        column for column in (TIMESTAMP_COLUMN, target_column) if column not in df.columns
    ]
    if missing_columns:
        raise ValueError(
            f"Feature dataset is missing required column(s): {missing_columns}"
        )

    feature_columns = _resolve_feature_columns(df, feature_columns, target_column)
    # Sorting defensively keeps the returned arrays chronological even if an
    # upstream artifact was written out of order.
    ordered = df.sort_values(TIMESTAMP_COLUMN, kind="stable")
    timestamps = _as_timestamps(ordered[TIMESTAMP_COLUMN])

    train = _select_range(
        ordered,
        timestamps,
        window.train_start_date,
        window.train_end_date,
        range_name="training",
    )
    validation = _select_range(
        ordered,
        timestamps,
        window.validation_start_date,
        window.validation_end_date,
        range_name="validation",
    )
    _verify_chronological_selection(timestamps, train, validation)

    split = TrainingSplit(
        train_features=_features_of(ordered, train, feature_columns),
        train_target=_target_of(ordered, train, target_column),
        validation_features=_features_of(ordered, validation, feature_columns),
        validation_target=_target_of(ordered, validation, target_column),
        train_timestamps=_timestamps_of(timestamps, train),
        validation_timestamps=_timestamps_of(timestamps, validation),
        feature_columns=list(feature_columns),
        target_column=target_column,
        window=window,
        metadata={
            "stage": "models.training_window",
            "target_column": target_column,
            "feature_columns": list(feature_columns),
            "window": window.as_metadata(),
            "train_rows": int(train.sum()),
            "validation_rows": int(validation.sum()),
            "train_range": _selected_range(timestamps, train),
            "validation_range": _selected_range(timestamps, validation),
            "timezone": "UTC",
        },
    )
    logger.info(
        "Training window selected: train_rows=%d (%s to %s), validation_rows=%d "
        "(%s to %s), features=%d",
        split.metadata["train_rows"],
        split.metadata["train_range"]["start"],
        split.metadata["train_range"]["end"],
        split.metadata["validation_rows"],
        split.metadata["validation_range"]["start"],
        split.metadata["validation_range"]["end"],
        len(feature_columns),
    )
    return split


def _select_range(
    df: pd.DataFrame,
    timestamps: pd.Series,
    start_date: date,
    end_date: date,
    *,
    range_name: str,
) -> pd.Series:
    """Return the boolean mask of rows falling inside an end-inclusive range."""
    lower = _bound(start_date, timestamps)
    # Half-open at the top so the end date covers its whole calendar day
    # regardless of the dataset's resolution.
    upper = _bound(end_date + timedelta(days=1), timestamps)
    mask = (timestamps >= lower) & (timestamps < upper)

    if not mask.any():
        available = _selected_range(timestamps, pd.Series(True, index=timestamps.index))
        raise ValueError(
            f"The {range_name} range {_format(start_date)} to {_format(end_date)} "
            f"selects no rows; the feature dataset covers {available['start']} to "
            f"{available['end']}"
        )
    return mask


def _verify_chronological_selection(
    timestamps: pd.Series, train: pd.Series, validation: pd.Series
) -> None:
    """Fail if any selected training row is not strictly before validation.

    The window bounds already forbid an overlap, so this guards the selection
    itself against a duplicated or misparsed timestamp reaching a fitted model.
    """
    last_train = timestamps[train].max()
    first_validation = timestamps[validation].min()
    if last_train >= first_validation:
        raise ValueError(
            f"Selected training rows do not precede validation rows: last training "
            f"timestamp {last_train} is not before first validation timestamp "
            f"{first_validation}"
        )


def _resolve_feature_columns(
    df: pd.DataFrame, feature_columns: Sequence[str] | None, target_column: str
) -> list[str]:
    """Return the predictor columns, defaulting to everything but the reserved ones."""
    reserved = (TIMESTAMP_COLUMN, target_column)
    if feature_columns is None:
        resolved = [column for column in df.columns if column not in reserved]
    else:
        if isinstance(feature_columns, str) or not isinstance(feature_columns, Sequence):
            raise ValueError("feature_columns must be a sequence of column names")
        resolved = list(feature_columns)
        held_back = [column for column in resolved if column in reserved]
        if held_back:
            raise ValueError(
                f"feature_columns must hold predictors only, but names {held_back}; "
                "the timestamp and the target are never predictors"
            )
        missing = [column for column in resolved if column not in df.columns]
        if missing:
            raise ValueError(f"Feature dataset is missing feature column(s): {missing}")

    if not resolved:
        raise ValueError(
            "Feature dataset has no feature column besides "
            f"{list(reserved)}; training requires at least one predictor"
        )
    return resolved


def _features_of(
    df: pd.DataFrame, mask: pd.Series, feature_columns: Sequence[str]
) -> pd.DataFrame:
    """Return the selected predictor rows in the shared feature column order."""
    return df.loc[mask, list(feature_columns)].reset_index(drop=True)


def _target_of(df: pd.DataFrame, mask: pd.Series, target_column: str) -> pd.Series:
    """Return the selected target values as a Series named for the target."""
    return df.loc[mask, target_column].reset_index(drop=True).rename(target_column)


def _timestamps_of(timestamps: pd.Series, mask: pd.Series) -> pd.Series:
    """Return the selected timestamps aligned to the feature and target rows."""
    return timestamps[mask].reset_index(drop=True).rename(TIMESTAMP_COLUMN)


def _selected_range(timestamps: pd.Series, mask: pd.Series) -> dict[str, str]:
    """Return the serializable first and last timestamp of a selection."""
    selected = timestamps[mask]
    return {
        "start": selected.min().isoformat(),
        "end": selected.max().isoformat(),
    }


def _as_timestamps(column: pd.Series) -> pd.Series:
    """Return the timestamp column as datetimes, failing on an unparsable value."""
    try:
        timestamps = pd.to_datetime(column)
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"Column {TIMESTAMP_COLUMN!r} must hold datetimes to select a "
            f"training window: {exc}"
        ) from exc
    if timestamps.isna().any():
        raise ValueError(
            f"Column {TIMESTAMP_COLUMN!r} holds a missing timestamp, so rows "
            "cannot be assigned to a training or validation range"
        )
    return timestamps


def _bound(bound_date: date, timestamps: pd.Series) -> pd.Timestamp:
    """Return a window bound comparable with the dataset's timestamp column."""
    bound = pd.Timestamp(bound_date)
    # Feature datasets are stored as UTC-aware; a naive frame compares as-is.
    timezone = getattr(timestamps.dtype, "tz", None)
    return bound.tz_localize(timezone) if timezone is not None else bound


def _parse_date(value: Any, field_name: str) -> date:
    """Return a `date` for a window bound given as a date, datetime, or string."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value.strip(), DATE_FORMAT).date()
        except ValueError as exc:
            raise ValueError(
                f"Invalid {field_name}: {value!r} is not a valid YYYY-MM-DD date"
            ) from exc
    raise ValueError(
        f"Invalid {field_name}: {value!r} is not a valid YYYY-MM-DD date"
    )


def _validate_target_column(target_column: Any) -> str:
    """Return a nonempty target column name."""
    if not isinstance(target_column, str) or not target_column.strip():
        raise ValueError("target_column must be a nonempty column name")
    return target_column


def _format(value: date) -> str:
    """Return a window bound in the canonical `YYYY-MM-DD` form."""
    return value.strftime(DATE_FORMAT)
