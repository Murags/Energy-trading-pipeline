"""Path resolution utilities for local-paths configuration."""

from pathlib import Path

# config/paths.py -> config -> energy_trading_pipeline -> src -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]


def get_default_base_dir() -> Path:
    """Return the repository root used to resolve relative config paths."""
    return _REPO_ROOT


def resolve_path(base_dir: Path, relative_path: str) -> Path:
    """Resolve a config-relative path against a base directory."""
    return (Path(base_dir) / relative_path).resolve()


def resolve_paths_config(
    paths_config: dict[str, str], base_dir: Path
) -> dict[str, Path]:
    """Resolve every path value in a flat paths config mapping against base_dir."""
    return {
        name: resolve_path(base_dir, relative_path)
        for name, relative_path in paths_config.items()
    }
