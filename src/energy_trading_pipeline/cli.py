"""CLI entry point for the energy trading pipeline."""

import argparse
import sys
from pathlib import Path

import yaml

from energy_trading_pipeline.config.loader import load_config
from energy_trading_pipeline.config.paths import get_default_base_dir
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
        choices=["train"],
        help="Train a baseline model; omit to only inspect config and prepare a run.",
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Train a baseline or preserve the config-only run bootstrap command."""
    args = parse_args(argv)

    try:
        config = load_config(
            args.config,
            local_paths_config_path=args.paths_config,
            model_params_config_path=args.model_params_config,
        )
        if args.command == "train":
            metadata = train_baseline(config, config_file_path=args.config)
            print(f"Run ID: {metadata['run_id']}")
            print(f"Model version: {metadata['model_version']}")
            print(f"Model artifact: {metadata['artifact_paths']['model']}")
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
