"""Single-writer filesystem registry for traceable fitted model artifacts."""

from collections.abc import Mapping
from datetime import datetime, timezone
import logging
import math
from pathlib import Path
import shutil
from tempfile import NamedTemporaryFile
from typing import Any

import yaml

from energy_trading_pipeline.models.xgboost_model import XGBoostSpreadModel

logger = logging.getLogger(__name__)


def save_model_artifacts(
    model: XGBoostSpreadModel,
    models_dir: Path,
    training_window: Mapping[str, Any],
    validation_metrics: Mapping[str, float],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Save a fitted model, YAML metadata, and its model-index entry.

    Returns the persisted metadata, including absolute artifact paths. Window
    metadata and held-out metrics come from the caller; the feature contract and
    parameters come from the fitted wrapper. Versions use UTC, and collisions
    fail rather than overwrite an existing model. Callers must serialize writes
    to the same registry. The index is replaced atomically only after saving.
    """
    if not model.is_fitted:
        raise ValueError("Model is not fitted; call fit() before registering it")
    if not isinstance(training_window, Mapping) or not training_window:
        raise ValueError("training_window must be a nonempty metadata mapping")
    if not isinstance(validation_metrics, Mapping) or not validation_metrics:
        raise ValueError("validation_metrics must be a nonempty metric mapping")
    for name, value in validation_metrics.items():
        if (
            not isinstance(name, str)
            or not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError("validation_metrics must contain finite nonnegative errors")

    created_at = now if now is not None else datetime.now(timezone.utc)
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    created_at = created_at.astimezone(timezone.utc)
    version = created_at.strftime("model_%Y%m%d_%H%M%S")
    models_dir = Path(models_dir).resolve()
    directory = models_dir / "artifacts" / version
    index_path = models_dir / "registry" / "models_index.yaml"
    index = {"models": {}}
    if index_path.exists():
        try:
            index = yaml.safe_load(index_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ValueError(f"Unreadable model index: {index_path}") from exc
        if not isinstance(index, dict) or not isinstance(index.get("models"), dict):
            raise ValueError(f"Invalid model index: {index_path}; expected models mapping")
    if version in index["models"] or directory.exists():
        raise FileExistsError(f"Model version already exists: {version}")

    metadata = {
        "model_version": version,
        "model_type": model.model_type,
        "created_at": created_at.isoformat(),
        "training_window": dict(training_window),
        "feature_columns": model.feature_columns,
        "target_column": model.target_column,
        "model_parameters": model.params,
        "validation_metrics": dict(validation_metrics),
        "artifact_paths": {
            "model": str(directory / "model.json"),
            "metadata": str(directory / "metadata.yaml"),
            "models_index": str(index_path),
        },
    }
    index["models"][version] = metadata
    # Serialize before creating files so invalid metadata cannot leave a partial model.
    metadata_yaml = yaml.safe_dump(metadata, sort_keys=False)
    index_yaml = yaml.safe_dump(index, sort_keys=False)
    directory.mkdir(parents=True, exist_ok=False)
    temporary_index = None
    try:
        model.save(directory / "model.json")
        (directory / "metadata.yaml").write_text(metadata_yaml, encoding="utf-8")
        index_path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=index_path.parent, delete=False
        ) as handle:
            temporary_index = Path(handle.name)
            handle.write(index_yaml)
        temporary_index.replace(index_path)
    except Exception:
        logger.exception("Failed to register model version %s", version)
        shutil.rmtree(directory)
        raise
    finally:
        if temporary_index is not None:
            temporary_index.unlink(missing_ok=True)
    logger.info("Model registered: version=%s index=%s", version, index_path)
    return metadata
