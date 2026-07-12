"""CLI entry point for the energy trading pipeline."""

import argparse
import sys
from pathlib import Path

from energy_trading_pipeline.config.loader import load_config
from energy_trading_pipeline.config.paths import get_default_base_dir
from energy_trading_pipeline.utils.io import create_run_directory, write_run_metadata
from energy_trading_pipeline.utils.time import generate_run_id


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="energy-trading-pipeline",
        description="Run the energy trading pipeline CLI.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to the experiment YAML configuration file.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Load config, print resolved run settings, and prepare a run artifact folder."""
    args = parse_args(argv)

    config = load_config(args.config)

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
        "config": config,
    }
    metadata_path = write_run_metadata(run_dir, metadata)
    print(f"Run metadata written to: {metadata_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
