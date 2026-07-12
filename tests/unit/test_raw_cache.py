"""Unit tests for the raw artifact cache layout."""

from pathlib import Path

import pytest

from energy_trading_pipeline.config.paths import resolve_raw_data_dir
from energy_trading_pipeline.data_ingestion.cache import (
    create_raw_cache_layout,
    resolve_raw_artifact_path,
    write_raw_artifact,
)


def test_resolve_raw_data_dir_uses_configured_path(tmp_path):
    paths_config = {"data_raw_dir": "custom/raw"}

    raw_data_dir = resolve_raw_data_dir(paths_config, tmp_path)

    assert raw_data_dir == (tmp_path / "custom" / "raw").resolve()


def test_resolve_raw_data_dir_accepts_resolved_runtime_path(tmp_path):
    configured_path = (tmp_path / "custom" / "raw").resolve()

    raw_data_dir = resolve_raw_data_dir(
        {"data_raw_dir": configured_path}, tmp_path / "unused"
    )

    assert raw_data_dir == configured_path


def test_resolve_raw_data_dir_requires_configured_path(tmp_path):
    with pytest.raises(KeyError, match="data_raw_dir"):
        resolve_raw_data_dir({}, tmp_path)


def test_create_raw_cache_layout_creates_expected_directories(tmp_path):
    raw_data_dir = tmp_path / "data" / "raw"

    directories = create_raw_cache_layout(raw_data_dir)

    assert directories == {
        "entsoe_prices": raw_data_dir / "entsoe" / "prices",
        "entsoe_load": raw_data_dir / "entsoe" / "load",
        "entsoe_generation": raw_data_dir / "entsoe" / "generation",
        "open_meteo_weather": raw_data_dir / "open_meteo" / "weather",
    }
    assert all(directory.is_dir() for directory in directories.values())


def test_resolve_raw_artifact_path_creates_parent_directory(tmp_path):
    artifact_path = resolve_raw_artifact_path(
        tmp_path / "raw", "entsoe", "prices", "de_2026-01.csv"
    )

    assert artifact_path == tmp_path / "raw" / "entsoe" / "prices" / "de_2026-01.csv"
    assert artifact_path.parent.is_dir()


@pytest.mark.parametrize(
    ("source", "category"),
    [("entsoe", "weather"), ("open_meteo", "prices"), ("unknown", "prices")],
)
def test_resolve_raw_artifact_path_rejects_unknown_layout_entries(
    tmp_path, source, category
):
    with pytest.raises(ValueError, match="Unsupported raw artifact location"):
        resolve_raw_artifact_path(tmp_path, source, category, "artifact.csv")


@pytest.mark.parametrize(
    "filename", ["", ".", "..", "../artifact.csv", "nested/artifact.csv"]
)
def test_resolve_raw_artifact_path_rejects_invalid_filename(tmp_path, filename):
    with pytest.raises(ValueError, match="filename"):
        resolve_raw_artifact_path(tmp_path, "entsoe", "prices", filename)


def test_write_raw_artifact_creates_file_once(tmp_path):
    artifact_path = tmp_path / "raw" / "entsoe" / "prices" / "prices.csv"

    result = write_raw_artifact(artifact_path, b"timestamp,price\n")

    assert result == artifact_path
    assert artifact_path.read_bytes() == b"timestamp,price\n"


def test_write_raw_artifact_does_not_overwrite_cached_file(tmp_path):
    artifact_path = tmp_path / "prices.csv"
    artifact_path.write_bytes(b"original")

    with pytest.raises(FileExistsError, match="already exists") as exc_info:
        write_raw_artifact(artifact_path, b"replacement")

    assert artifact_path.read_bytes() == b"original"
    assert exc_info.value.errno is not None
    assert Path(exc_info.value.filename) == artifact_path
