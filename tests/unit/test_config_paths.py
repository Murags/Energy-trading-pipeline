"""Unit tests for config path resolution utilities."""

from pathlib import Path

from energy_trading_pipeline.config.paths import (
    get_default_base_dir,
    resolve_path,
    resolve_paths_config,
)


def test_resolve_path_joins_and_resolves_against_base_dir(tmp_path):
    result = resolve_path(tmp_path, "data/raw")

    assert result == (tmp_path / "data" / "raw").resolve()
    assert result.is_absolute()


def test_resolve_path_collapses_relative_segments(tmp_path):
    nested_base = tmp_path / "configs"
    nested_base.mkdir()

    result = resolve_path(nested_base, "../data/raw")

    assert result == (tmp_path / "data" / "raw").resolve()


def test_resolve_paths_config_resolves_every_entry(tmp_path):
    paths_config = {
        "data_raw_dir": "data/raw",
        "models_dir": "models",
    }

    resolved = resolve_paths_config(paths_config, tmp_path)

    assert resolved == {
        "data_raw_dir": (tmp_path / "data" / "raw").resolve(),
        "models_dir": (tmp_path / "models").resolve(),
    }
    assert all(isinstance(path, Path) for path in resolved.values())


def test_resolve_paths_config_returns_empty_dict_for_empty_config(tmp_path):
    assert resolve_paths_config({}, tmp_path) == {}


def test_get_default_base_dir_returns_repository_root():
    base_dir = get_default_base_dir()

    assert base_dir.is_absolute()
    assert (base_dir / "src" / "energy_trading_pipeline").is_dir()
    assert (base_dir / "pyproject.toml").is_file()
