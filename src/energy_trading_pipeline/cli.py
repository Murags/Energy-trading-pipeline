"""CLI entry point for the energy trading pipeline."""

import argparse
import sys
from pathlib import Path

import yaml

from energy_trading_pipeline.backtesting.backtest_runner import run_configured_backtest
from energy_trading_pipeline.config.loader import load_config
from energy_trading_pipeline.config.paths import get_default_base_dir, resolve_path
from energy_trading_pipeline.evaluation.exports import export_dashboard_artifacts
from energy_trading_pipeline.models.trainer import train_baseline
from energy_trading_pipeline.utils.io import create_run_directory, write_run_metadata
from energy_trading_pipeline.utils.time import generate_run_id


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="energy-trading-pipeline",
        description="Run the energy trading pipeline CLI.",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["train", "backtest", "export-dashboard"],
        help="Train, backtest, or export saved results; omit to inspect config.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to the experiment YAML configuration file.",
    )
    parser.add_argument(
        "--paths-config", type=Path, help="Path to the local paths YAML configuration."
    )
    parser.add_argument(
        "--model-params-config", type=Path, help="Path to the XGBoost parameters YAML."
    )
    for flag, help_text in [
        ("--forecasts", "Saved canonical forecast Parquet."),
        ("--metrics", "Saved strategy comparison Parquet."),
        ("--retraining-events", "Saved completed-retraining event Parquet."),
        ("--rolling-rmse", "Optional saved decision-time rolling RMSE Parquet."),
    ]:
        parser.add_argument(flag, type=Path, help=help_text)
    model_sources = parser.add_mutually_exclusive_group()
    model_sources.add_argument(
        "--model-index", type=Path, help="Saved model registry YAML index."
    )
    model_sources.add_argument(
        "--run-metadata", type=Path, action="append",
        help="Saved backtest run metadata YAML; repeat for all referenced versions.",
    )
    args = parser.parse_args(argv)
    if args.command == "export-dashboard":
        for name in ("forecasts", "metrics", "retraining_events"):
            if getattr(args, name) is None:
                parser.error(f"export-dashboard requires --{name.replace('_', '-')}")
        if args.model_index is None and not args.run_metadata:
            parser.error("export-dashboard requires --model-index or --run-metadata")
    elif any(
        getattr(args, name) is not None
        for name in (
            "forecasts", "metrics", "retraining_events", "rolling_rmse",
            "model_index", "run_metadata",
        )
    ):
        parser.error("Saved artifact flags require the export-dashboard command")
    return args


def main(argv: list[str] | None = None) -> int:
    """Run training, backtesting, saved exports, or config-only run bootstrap."""
    args = parse_args(argv)

    try:
        config = load_config(
            args.config,
            local_paths_config_path=args.paths_config,
            model_params_config_path=args.model_params_config,
        )
        if args.command == "export-dashboard":
            reports_dir = resolve_path(
                get_default_base_dir(), config["paths"]["reports_dir"]
            )
            paths = export_dashboard_artifacts(
                forecasts_path=args.forecasts,
                metrics_path=args.metrics,
                retraining_events_path=args.retraining_events,
                model_index_path=args.model_index,
                run_metadata_paths=args.run_metadata,
                monitoring_path=args.rolling_rmse,
                exports_dir=reports_dir / "dashboard_exports",
            )
            print(f"Dashboard exports written to: {reports_dir / 'dashboard_exports'}")
            for name, path in paths.items():
                print(f"  {name}: {path}")
            return 0
        if args.command == "train":
            metadata = train_baseline(config, config_file_path=args.config)
            print(f"Run ID: {metadata['run_id']}")
            print(f"Model version: {metadata['model_version']}")
            print(f"Model artifact: {metadata['artifact_paths']['model']}")
            print(f"Run metadata written to: {metadata['artifact_paths']['run_metadata']}")
            return 0
        if args.command == "backtest":
            metadata = run_configured_backtest(config, config_file_path=args.config)
            print(f"Run ID: {metadata['run_id']}")
            print(f"Model version: {metadata['model_version']}")
            print(f"Forecast log: {metadata['artifact_paths']['forecasts']}")
            print(f"Backtest log: {metadata['artifact_paths']['backtest_log']}")
            print(f"Run metadata written to: {metadata['artifact_paths']['run_metadata']}")
            return 0
    except (OSError, ValueError, KeyError, yaml.YAMLError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    run_id = generate_run_id()
    runs_root = get_default_base_dir() / "logs" / "runs"
    run_dir = create_run_directory(runs_root, run_id)

    print(f"Run ID: {run_id}")
    print(f"Config file: {args.config}")
    print("Resolved run settings:")
    for section, value in config.items():
        print(f"  {section}: {value}")

    metadata = {
        "run_id": run_id,
        "config_path": str(args.config),
        "config": {
            **config,
            **(
                {"paths": {key: str(value) for key, value in config["paths"].items()}}
                if "paths" in config
                else {}
            ),
        },
    }
    metadata_path = write_run_metadata(run_dir, metadata)
    print(f"Run metadata written to: {metadata_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
