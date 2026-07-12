"""Path and immutable-write helpers for the local raw artifact cache."""

from pathlib import Path

RAW_CACHE_LAYOUT = {
    "entsoe": ("prices", "load", "generation"),
    "open_meteo": ("weather",),
}


def create_raw_cache_layout(raw_data_dir: Path) -> dict[str, Path]:
    """Create and return all configured raw artifact category directories."""
    root = Path(raw_data_dir)
    directories = {
        f"{source}_{category}": root / source / category
        for source, categories in RAW_CACHE_LAYOUT.items()
        for category in categories
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)
    return directories


def resolve_raw_artifact_path(
    raw_data_dir: Path,
    source: str,
    category: str,
    filename: str,
) -> Path:
    """Resolve an allowed raw artifact path and create its parent directory."""
    if source not in RAW_CACHE_LAYOUT or category not in RAW_CACHE_LAYOUT[source]:
        raise ValueError(f"Unsupported raw artifact location: {source}/{category}")

    filename_path = Path(filename)
    if (
        not filename
        or filename in {".", ".."}
        or filename_path.name != filename
        or filename_path.is_absolute()
    ):
        raise ValueError("Raw artifact filename must be a non-empty file name")

    directory = Path(raw_data_dir) / source / category
    directory.mkdir(parents=True, exist_ok=True)
    return directory / filename


def write_raw_artifact(artifact_path: Path, content: bytes) -> Path:
    """Write a new raw artifact without replacing an existing cached file."""
    path = Path(artifact_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(content)
    except FileExistsError as error:
        message = f"Raw artifact already exists and is immutable: {path}"
        raise FileExistsError(error.errno, message, error.filename) from error
    return path
