"""Integration tests for the CLI entry point."""

import sys
from pathlib import Path

import pytest
import yaml

from energy_trading_pipeline.cli import main

FIXTURE_CONFIG_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "sample_config.yaml"


def test_cli_creates_run_directory_and_metadata_without_data_files(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(
        "energy_trading_pipeline.cli.get_default_base_dir", lambda: tmp_path
    )

    exit_code = main(["--config", str(FIXTURE_CONFIG_PATH)])

    assert exit_code == 0

    runs_root = tmp_path / "logs" / "runs"
    run_dirs = list(runs_root.iterdir())
    assert len(run_dirs) == 1

    run_dir = run_dirs[0]
    assert run_dir.name.startswith("run_")

    metadata_path = run_dir / "run_metadata.yaml"
    assert metadata_path.is_file()

    metadata = yaml.safe_load(metadata_path.read_text())
    assert metadata["run_id"] == run_dir.name
    assert metadata["config_path"] == str(FIXTURE_CONFIG_PATH)
    assert metadata["config"]["retraining"]["strategy"] == "fixed_schedule"

    captured = capsys.readouterr()
    assert "Run ID" in captured.out
    assert "Resolved run settings" in captured.out


def test_cli_requires_config_argument():
    with pytest.raises(SystemExit) as exc_info:
        main([])

    assert exc_info.value.code != 0


def test_local_cli_ignores_enabled_aws_without_sdk(tmp_path, monkeypatch):
    """Even enabled mirroring config must not make local execution import AWS."""
    config = yaml.safe_load(FIXTURE_CONFIG_PATH.read_text())
    config["aws"] = {
        "enabled": True,
        "bucket_name": "research-artifacts",
        "prefixes": {"reports": "reports/"},
    }
    config_path = tmp_path / "experiment.yaml"
    config_path.write_text(yaml.safe_dump(config))
    monkeypatch.setattr(
        "energy_trading_pipeline.cli.get_default_base_dir", lambda: tmp_path
    )
    monkeypatch.setitem(sys.modules, "boto3", None)
    monkeypatch.setitem(sys.modules, "botocore", None)

    assert main(["--config", str(config_path)]) == 0
    metadata_paths = list((tmp_path / "logs/runs").glob("*/run_metadata.yaml"))
    assert len(metadata_paths) == 1
    metadata = yaml.safe_load(metadata_paths[0].read_text())
    assert metadata["config"]["aws"] == config["aws"]
