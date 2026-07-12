"""Run artifact I/O helpers."""

from pathlib import Path
from typing import Any

import yaml


def create_run_directory(runs_root: Path, run_id: str) -> Path:
    """Create (if needed) and return the run-specific artifact directory."""
    run_dir = Path(runs_root) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def write_run_metadata(run_dir: Path, metadata: dict[str, Any]) -> Path:
    """Write `metadata` as YAML to `run_dir/run_metadata.yaml` and return its path."""
    metadata_path = Path(run_dir) / "run_metadata.yaml"
    with metadata_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(metadata, handle, default_flow_style=False, sort_keys=False)
    return metadata_path
