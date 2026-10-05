"""Core forecast metrics with consistent observed-actual filtering."""

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_complex_dtype, is_numeric_dtype


def _forecast_errors(actual: pd.Series, prediction: pd.Series) -> pd.Series:
	if not isinstance(actual, pd.Series) or not isinstance(prediction, pd.Series):
		raise ValueError("actual and prediction must be pandas Series")
	if len(actual) != len(prediction):
		raise ValueError("actual and prediction must have the same length")
	validated = {}
	for column, values in (("actual", actual), ("prediction", prediction)):
		message = f"{column} must contain finite real numeric values"
		if column == "prediction" and values.isna().any():
			raise ValueError(message)
		if values.empty or (column == "actual" and values.isna().all()):
			numeric = pd.Series(np.nan, index=range(len(values)), dtype="float64")
		else:
			if (
				not is_numeric_dtype(values.dtype)
				or is_bool_dtype(values.dtype)
				or is_complex_dtype(values.dtype)
			):
				raise ValueError(message)
			numeric = values.astype("float64").reset_index(drop=True)
		if not np.isfinite(numeric.dropna()).all():
			raise ValueError(message)
		validated[column] = numeric
	observed = validated["actual"].notna()
	with np.errstate(over="ignore", invalid="ignore"):
		errors = validated["actual"][observed] - validated["prediction"][observed]
	if not np.isfinite(errors).all():
		raise ValueError("error calculation produced non-finite values")
	return errors


def calculate_rmse(actual: pd.Series, prediction: pd.Series) -> float:
	"""Return RMSE of positional pairs with observed actuals, or NaN if none.

	Series indexes are ignored. Predictions must all be finite real numbers;
	only actuals may be missing. Unequal lengths and invalid values fail clearly.
	Inputs are never mutated. Scaling avoids overflow when squaring errors.
	"""
	errors = _forecast_errors(actual, prediction)
	if errors.empty:
		return float("nan")
	scale = float(errors.abs().max())
	return scale * float(np.sqrt(((errors / scale) ** 2).mean())) if scale else 0.0


def calculate_mae(actual: pd.Series, prediction: pd.Series) -> float:
	"""Return MAE using the same positional pairs and validation as RMSE.

	Skip missing actuals, return NaN without observations, and never mutate inputs.
	"""
	errors = _forecast_errors(actual, prediction)
	if errors.empty:
		return float("nan")
	scale = float(errors.abs().max())
	return scale * float((errors.abs() / scale).mean()) if scale else 0.0
