"""YAML configuration loading and merging into the experiment runtime config."""

from pathlib import Path
from typing import Any

import yaml

from energy_trading_pipeline.config.paths import (
    get_default_base_dir,
    resolve_paths_config,
)
from energy_trading_pipeline.config.schema import (
    ConfigValidationError,
    validate_experiment_config,
)


def load_yaml_file(config_path: Path) -> dict[str, Any]:
    """
    Load a single YAML file into a dict.

    Raises:
        FileNotFoundError: If `config_path` does not exist.
        ValueError: If the file's top-level content is not a YAML mapping.
    """
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        content = yaml.safe_load(handle)

    if content is None:
        return {}
    if not isinstance(content, dict):
        raise ValueError(
            f"Config file must contain a YAML mapping at the top level: {path}"
        )
    return content


def load_config(
    experiment_config_path: Path,
    local_paths_config_path: Path | None = None,
    model_params_config_path: Path | None = None,
    base_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Load and validate the experiment config, merging paths and model params.

    Reads the experiment YAML and validates its required top-level sections
    and date ordering. If provided, `local_paths_config_path` is resolved
    against `base_dir` and merged in under the `paths` key, and
    `model_params_config_path` is merged into `model.params`.

    Raises:
        ConfigValidationError: If the experiment config fails validation, or if
            its `model` section is not a mapping when merging model params.
        FileNotFoundError: If any provided config file does not exist.
        ValueError: If any provided config file's top-level content is not a
            YAML mapping.
    """
    config = load_yaml_file(experiment_config_path)
    validate_experiment_config(config)

    resolved_base_dir = (
        base_dir if base_dir is not None else get_default_base_dir()
    )

    if local_paths_config_path is not None:
        paths_config = load_yaml_file(local_paths_config_path)
        config["paths"] = resolve_paths_config(paths_config, resolved_base_dir)

    if model_params_config_path is not None:
        model_params = load_yaml_file(model_params_config_path)
        existing_model_config = config.get("model", {})
        if not isinstance(existing_model_config, dict):
            raise ConfigValidationError(
                "Config section 'model' must be a mapping to merge model params."
            )
        config["model"] = {**existing_model_config, "params": model_params}

    return config
