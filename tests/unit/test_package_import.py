"""Verify the energy_trading_pipeline package skeleton imports successfully."""

import importlib


def test_package_imports():
    module = importlib.import_module("energy_trading_pipeline")

    assert module.__version__ == "0.1.0"


def test_module_subpackages_import():
    subpackages = [
        "energy_trading_pipeline.config",
        "energy_trading_pipeline.data_ingestion",
        "energy_trading_pipeline.preprocessing",
        "energy_trading_pipeline.features",
        "energy_trading_pipeline.models",
        "energy_trading_pipeline.backtesting",
        "energy_trading_pipeline.monitoring",
        "energy_trading_pipeline.retraining",
        "energy_trading_pipeline.evaluation",
        "energy_trading_pipeline.dashboard",
        "energy_trading_pipeline.utils",
    ]

    for subpackage in subpackages:
        importlib.import_module(subpackage)
