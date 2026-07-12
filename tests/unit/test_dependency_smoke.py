"""Smoke test verifying the package imports after dependency installation."""

import importlib

import energy_trading_pipeline

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


def test_package_importable_after_dependency_installation():
    assert energy_trading_pipeline.__version__ == "0.1.0"


def test_core_dependencies_importable():
    for dependency in CORE_DEPENDENCIES:
        importlib.import_module(dependency)
