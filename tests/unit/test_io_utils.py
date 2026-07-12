"""Unit tests for run artifact I/O helpers."""

import yaml

from energy_trading_pipeline.utils.io import create_run_directory, write_run_metadata


def test_create_run_directory_creates_nested_run_folder(tmp_path):
    runs_root = tmp_path / "logs" / "runs"

    run_dir = create_run_directory(runs_root, "run_20260712_210509")

    assert run_dir == runs_root / "run_20260712_210509"
    assert run_dir.is_dir()


def test_create_run_directory_is_idempotent(tmp_path):
    runs_root = tmp_path / "logs" / "runs"

    create_run_directory(runs_root, "run_20260712_210509")
    run_dir = create_run_directory(runs_root, "run_20260712_210509")

    assert run_dir.is_dir()


def test_write_run_metadata_writes_yaml_file(tmp_path):
    run_dir = tmp_path / "run_20260712_210509"
    run_dir.mkdir()
    metadata = {"run_id": "run_20260712_210509", "config_path": "configs/experiment.yaml"}

    metadata_path = write_run_metadata(run_dir, metadata)

    assert metadata_path == run_dir / "run_metadata.yaml"
    assert metadata_path.is_file()
    assert yaml.safe_load(metadata_path.read_text()) == metadata
