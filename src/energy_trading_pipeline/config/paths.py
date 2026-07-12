"""Path resolution utilities for local-paths configuration."""

from pathlib import Path

# Fallback if no `pyproject.toml` is found above this file (e.g. installed package).
# config/paths.py -> config -> energy_trading_pipeline -> src -> repo root
_FALLBACK_REPO_ROOT = Path(__file__).resolve().parents[3]


def get_default_base_dir() -> Path:
    """
    Return the repository root used to resolve relative config paths.

    Walks up from this file's location looking for a directory containing
    `pyproject.toml`. Falls back to the conventional `src/` layout root if
    no `pyproject.toml` is found (e.g. when running from an installed package).
    """
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return _FALLBACK_REPO_ROOT


def resolve_path(base_dir: Path, relative_path: str | Path) -> Path:
    """Resolve a config-relative path against a base directory."""
    return (Path(base_dir) / relative_path).resolve()


def resolve_paths_config(
    paths_config: dict[str, str | Path], base_dir: Path
) -> dict[str, Path]:
    """Resolve every path value in a flat paths config mapping against base_dir."""
    return {
        name: resolve_path(base_dir, relative_path)
        for name, relative_path in paths_config.items()
    }


def resolve_raw_data_dir(
    paths_config: dict[str, str | Path], base_dir: Path
) -> Path:
    """Resolve the configured root directory for immutable raw artifacts."""
    try:
        raw_data_dir = Path(paths_config["data_raw_dir"])
    except KeyError as error:
        raise KeyError("Missing required path setting: data_raw_dir") from error
    if raw_data_dir.is_absolute():
        return raw_data_dir.resolve()
    return resolve_path(base_dir, raw_data_dir)
