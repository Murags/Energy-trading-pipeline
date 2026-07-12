"""Smoke test verifying core third-party dependencies import after installation."""

import importlib

import pytest

CORE_DEPENDENCIES = [
    "pandas",
    "numpy",
    "sklearn",
    "xgboost",
    "pyarrow",
    "matplotlib",
    "plotly",
    "yaml",
]


@pytest.mark.parametrize("dependency", CORE_DEPENDENCIES)
def test_core_dependency_importable(dependency):
    importlib.import_module(dependency)
