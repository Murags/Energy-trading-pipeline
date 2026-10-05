"""Known-value and validation checks for core forecast metrics."""

import numpy as np
import pandas as pd
import pytest

from energy_trading_pipeline.monitoring.metrics import calculate_mae, calculate_rmse


@pytest.mark.parametrize("metric", [calculate_rmse, calculate_mae])
def test_perfect_predictions(metric):
    assert metric(pd.Series([1.0, -2.0]), pd.Series([1.0, -2.0])) == 0.0


def test_known_errors():
    actual = pd.Series([1.0, 2.0, 3.0])
    prediction = pd.Series([0.0, 4.0, 0.0])
    assert calculate_rmse(actual, prediction) == pytest.approx(np.sqrt(14 / 3))
    assert calculate_mae(actual, prediction) == pytest.approx(2.0)


@pytest.mark.parametrize("metric", [calculate_rmse, calculate_mae])
def test_missing_actuals_use_only_observed_pairs(metric):
    actual = pd.Series([1.0, np.nan, 3.0])
    prediction = pd.Series([0.0, 1000.0, 2.0])
    assert metric(actual, prediction) == 1.0


@pytest.mark.parametrize("metric", [calculate_rmse, calculate_mae])
@pytest.mark.parametrize(
    "actual",
    [
        pd.Series([], dtype=float),
        pd.Series([np.nan]),
        pd.Series([pd.NA], dtype=object),
        pd.Series([pd.NA], dtype="string"),
    ],
)
def test_no_observed_actuals_returns_nan(metric, actual):
    assert np.isnan(metric(actual, pd.Series([0.0] * len(actual), dtype=float)))


@pytest.mark.parametrize("metric", [calculate_rmse, calculate_mae])
def test_nullable_actuals_and_positional_pairing_without_mutation(metric):
    actual = pd.Series([1.0, pd.NA, 3.0], index=[9, 8, 7], dtype="Float64")
    prediction = pd.Series([0, 100, 2], index=[0, 1, 2])
    original_actual = actual.copy(deep=True)
    original_prediction = prediction.copy(deep=True)
    assert metric(actual, prediction) == 1.0
    pd.testing.assert_series_equal(actual, original_actual)
    pd.testing.assert_series_equal(prediction, original_prediction)


@pytest.mark.parametrize("metric", [calculate_rmse, calculate_mae])
def test_mismatched_lengths_fail(metric):
    with pytest.raises(ValueError, match="same length"):
        metric(pd.Series([1.0]), pd.Series([1.0, 2.0]))


@pytest.mark.parametrize("metric", [calculate_rmse, calculate_mae])
@pytest.mark.parametrize("column", ["actual", "prediction"])
@pytest.mark.parametrize("invalid", [[np.inf], [-np.inf], [True], [1j], ["1"]])
def test_invalid_numeric_values_fail(metric, column, invalid):
    values = {"actual": pd.Series([1.0]), "prediction": pd.Series([0.0])}
    values[column] = pd.Series(invalid)
    with pytest.raises(ValueError, match=f"{column}.*finite real numeric"):
        metric(**values)


@pytest.mark.parametrize("metric", [calculate_rmse, calculate_mae])
def test_missing_predictions_fail_even_when_actual_is_missing(metric):
    with pytest.raises(ValueError, match="prediction.*finite real numeric"):
        metric(pd.Series([np.nan]), pd.Series([np.nan]))


@pytest.mark.parametrize("metric", [calculate_rmse, calculate_mae])
def test_large_finite_errors_do_not_overflow_metric(metric):
    assert metric(pd.Series([1e200, -1e200]), pd.Series([0.0, 0.0])) == 1e200


@pytest.mark.parametrize("metric", [calculate_rmse, calculate_mae])
def test_subtraction_overflow_fails(metric):
    with pytest.raises(ValueError, match="error.*non-finite"):
        metric(pd.Series([1e308]), pd.Series([-1e308]))


@pytest.mark.parametrize("metric", [calculate_rmse, calculate_mae])
@pytest.mark.parametrize("column", ["actual", "prediction"])
@pytest.mark.parametrize("invalid", [[1.0], pd.DataFrame({"value": [1.0]})])
def test_non_series_inputs_fail(metric, column, invalid):
    values = {"actual": pd.Series([1.0]), "prediction": pd.Series([0.0])}
    values[column] = invalid
    with pytest.raises(ValueError, match="pandas Series"):
        metric(**values)


@pytest.mark.parametrize("metric", [calculate_rmse, calculate_mae])
def test_integer_errors_do_not_wrap(metric):
    actual = pd.Series([-2**63], dtype="int64")
    prediction = pd.Series([2**63 - 1], dtype="int64")
    assert metric(actual, prediction) == pytest.approx(float(2**64 - 1))