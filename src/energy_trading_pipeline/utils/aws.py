"""Explicit, optional S3 mirroring of selected local artifacts."""

import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class MirrorResult:
    """Report uploaded/failed S3 keys and why an optional mirror was skipped."""

    uploaded_keys: tuple[str, ...] = ()
    failed_keys: tuple[str, ...] = ()
    skipped_reason: str | None = None


def _skip(
    reason: str,
    uploaded_keys: tuple[str, ...] = (),
    failed_keys: tuple[str, ...] = (),
) -> MirrorResult:
    LOGGER.warning("S3 artifact mirror: skipping; %s", reason)
    return MirrorResult(uploaded_keys, failed_keys, reason)


def _plan_uploads(
    artifact_paths: Iterable[str | Path],
    prefixes: Mapping[str, str],
    base_dir: Path,
) -> list[tuple[Path, str]]:
    """Validate every mapping/selection before any external interaction."""
    roots = []
    for local_root, prefix in prefixes.items():
        if not isinstance(local_root, str) or not local_root.strip():
            raise ValueError("AWS prefixes require non-empty local directory keys.")
        if (
            not isinstance(prefix, str)
            or not prefix.strip()
            or prefix.startswith("/")
            or "\\" in prefix
            or ":" in prefix
            or any(part in {"", ".", ".."} for part in prefix.rstrip("/").split("/"))
        ):
            raise ValueError("AWS prefixes must be relative S3 directory prefixes.")
        root = Path(local_root)
        root = (root if root.is_absolute() else base_dir / root).resolve()
        roots.append((root, prefix.rstrip("/")))

    uploads = []
    keys: set[str] = set()
    for artifact_path in artifact_paths:
        path = Path(artifact_path)
        path = (path if path.is_absolute() else base_dir / path).resolve()
        matches = [(root, prefix) for root, prefix in roots if path.is_relative_to(root)]
        if len(matches) != 1:
            raise ValueError(f"Artifact must match exactly one AWS prefix mapping: {path}")
        if not path.is_file():
            raise FileNotFoundError(f"Selected artifact is not an existing file: {path}")
        root, prefix = matches[0]
        key = f"{prefix}/{path.relative_to(root).as_posix()}"
        if key in keys:
            raise ValueError(f"Duplicate S3 destination key: {key}")
        keys.add(key)
        uploads.append((path, key))
    return uploads


def mirror_artifacts(
    artifact_paths: Iterable[str | Path],
    aws_config: Mapping[str, Any] | None = None,
    *,
    base_dir: Path,
) -> MirrorResult:
    """Copy selected files to S3 only with explicit enabled AWS configuration.

    ``aws_config`` is the optional experiment ``aws`` section: ``enabled``,
    ``bucket_name``, optional ``region``, and ``prefixes`` mapping local directory
    roots to S3 prefixes. Relative roots and file selections resolve against
    ``base_dir``. Files must belong to exactly one mapping; directories are not
    recursively uploaded. Invalid inputs fail before contacting AWS. Missing SDK,
    credentials, and AWS/transport failures are logged and returned, leaving local
    artifacts untouched. Uses boto3's normal credential chain; never accepts keys.
    """
    if aws_config is None:
        return _skip("AWS configuration is absent.")
    if not isinstance(aws_config, Mapping):
        raise ValueError("AWS configuration must be a mapping.")
    enabled = aws_config.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ValueError("AWS enabled must be a boolean.")
    if not enabled:
        return _skip("AWS mirroring is disabled.")
    bucket = aws_config.get("bucket_name")
    if not isinstance(bucket, str) or not bucket.strip():
        raise ValueError("Enabled AWS mirroring requires bucket_name.")
    prefixes = aws_config.get("prefixes")
    if not isinstance(prefixes, Mapping) or not prefixes:
        raise ValueError("Enabled AWS mirroring requires a non-empty prefixes mapping.")
    region = aws_config.get("region")
    if region is not None and (not isinstance(region, str) or not region.strip()):
        raise ValueError("AWS region must be a non-empty string when supplied.")
    uploads = _plan_uploads(artifact_paths, prefixes, Path(base_dir).resolve())
    if not uploads:
        return _skip("No artifact files were selected.")

    # The optional SDK must never be imported by disabled/local runs.
    try:
        import boto3
        from boto3.exceptions import S3UploadFailedError
        from botocore.exceptions import (
            BotoCoreError,
            ClientError,
            NoCredentialsError,
            PartialCredentialsError,
        )
    except ImportError:
        return _skip("Install the optional AWS extra with uv sync --extra aws.")

    try:
        session = boto3.Session()
        if session.get_credentials() is None:
            return _skip("AWS credentials are unavailable.")
        client = session.client("s3", region_name=region)
    except (NoCredentialsError, PartialCredentialsError):
        return _skip("AWS credentials are unavailable or incomplete.")
    except (BotoCoreError, ClientError, OSError) as exc:
        return _skip(f"AWS initialization failed ({type(exc).__name__}).")

    uploaded: list[str] = []
    failed: list[str] = []
    for path, key in uploads:
        try:
            client.upload_file(str(path), bucket, key)
        except (NoCredentialsError, PartialCredentialsError):
            return _skip(
                "AWS credentials are unavailable or incomplete.",
                tuple(uploaded),
                tuple(failed),
            )
        except (BotoCoreError, ClientError, S3UploadFailedError, OSError) as exc:
            LOGGER.warning(
                "S3 artifact mirror: upload failed for %s (%s).",
                key,
                type(exc).__name__,
            )
            failed.append(key)
        else:
            LOGGER.info("S3 artifact mirrored: s3://%s/%s", bucket, key)
            uploaded.append(key)
    return MirrorResult(tuple(uploaded), tuple(failed))
