"""Integration tests for the CLI entry point."""

from pathlib import Path

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
    exit_code = None
    try:
        main([])
    except SystemExit as exc:
        exit_code = exc.code

    assert exit_code != 0
