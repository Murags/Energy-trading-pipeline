"""Artifact store for live forecasting, over a local directory or an S3 prefix.

The daily job runs as a fresh process, locally or in Lambda, so all continuity
lives in stored artifacts rather than process memory. Both backends expose the
same small interface, which keeps the local run and the deployed run identical
apart from where bytes land.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
import io

import pandas as pd
import yaml


class ArtifactStore(ABC):
    """Read and write named artifacts without exposing the backend."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Return whether an artifact is present."""

    @abstractmethod
    def read_bytes(self, key: str) -> bytes:
        """Return the raw artifact, raising KeyError when absent."""

    @abstractmethod
    def write_bytes(self, key: str, payload: bytes) -> None:
        """Write or replace an artifact."""

    @abstractmethod
    def list_keys(self, prefix: str) -> list[str]:
        """Return stored keys under a prefix, sorted."""

    def read_frame(self, key: str) -> pd.DataFrame:
        """Read a Parquet artifact."""
        return pd.read_parquet(io.BytesIO(self.read_bytes(key)))

    def write_frame(self, key: str, frame: pd.DataFrame) -> None:
        """Write a Parquet artifact without an index column."""
        buffer = io.BytesIO()
        frame.to_parquet(buffer, index=False)
        self.write_bytes(key, buffer.getvalue())

    def read_yaml(self, key: str) -> dict[str, Any]:
        """Read a YAML artifact."""
        return yaml.safe_load(self.read_bytes(key).decode("utf-8")) or {}

    def write_yaml(self, key: str, payload: Mapping[str, Any]) -> None:
        """Write a YAML artifact in a stable, human-readable order."""
        text = yaml.safe_dump(dict(payload), sort_keys=False)
        self.write_bytes(key, text.encode("utf-8"))


class LocalArtifactStore(ArtifactStore):
    """Store artifacts beneath a local directory.

    Keys are relative POSIX paths; absolute keys and parent traversal are
    rejected so a key can never escape the configured root.
    """

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def _resolve(self, key: str) -> Path:
        candidate = Path(key)
        if not key or candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError(f"Artifact key must stay within the store: {key!r}")
        return self.root / candidate

    def exists(self, key: str) -> bool:
        return self._resolve(key).is_file()

    def read_bytes(self, key: str) -> bytes:
        path = self._resolve(key)
        if not path.is_file():
            raise KeyError(f"Missing artifact: {key}")
        return path.read_bytes()

    def write_bytes(self, key: str, payload: bytes) -> None:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write then replace, so a reader never observes a partial artifact.
        staged = path.with_name(f".{path.name}.partial")
        staged.write_bytes(payload)
        staged.replace(path)

    def list_keys(self, prefix: str) -> list[str]:
        base = self.root / prefix if prefix else self.root
        if not base.exists():
            return []
        return sorted(
            str(path.relative_to(self.root).as_posix())
            for path in base.rglob("*")
            if path.is_file() and not path.name.startswith(".")
        )


class S3ArtifactStore(ArtifactStore):
    """Store artifacts under an S3 bucket and optional key prefix.

    boto3 is imported lazily so the optional AWS dependency is never required
    for local runs or for the default test suite.
    """

    def __init__(
        self, bucket: str, prefix: str = "", *, client: Any = None
    ) -> None:
        if not isinstance(bucket, str) or not bucket.strip():
            raise ValueError("bucket must be a nonempty string")
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self._client = client

    @property
    def client(self) -> Any:
        """Return the S3 client, creating a default one on first use."""
        if self._client is None:
            import boto3

            self._client = boto3.client("s3")
        return self._client

    def _key(self, key: str) -> str:
        candidate = Path(key)
        if not key or candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError(f"Artifact key must stay within the store: {key!r}")
        return f"{self.prefix}/{key}" if self.prefix else key

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=self._key(key))
        except Exception as exc:  # botocore raises ClientError for 404
            if _is_missing(exc):
                return False
            raise
        return True

    def read_bytes(self, key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=self._key(key))
        except Exception as exc:
            if _is_missing(exc):
                raise KeyError(f"Missing artifact: {key}") from exc
            raise
        return response["Body"].read()

    def write_bytes(self, key: str, payload: bytes) -> None:
        self.client.put_object(
            Bucket=self.bucket, Key=self._key(key), Body=payload
        )

    def list_keys(self, prefix: str) -> list[str]:
        full = self._key(prefix) if prefix else self.prefix
        paginator = self.client.get_paginator("list_objects_v2")
        keys = []
        for page in paginator.paginate(Bucket=self.bucket, Prefix=full):
            for item in page.get("Contents", []):
                stored = item["Key"]
                if self.prefix:
                    stored = stored[len(self.prefix) + 1 :]
                keys.append(stored)
        return sorted(keys)


def _is_missing(exc: Exception) -> bool:
    """Recognise an S3 not-found without importing botocore eagerly."""
    code = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
    return code in {"404", "NoSuchKey", "NotFound"} or exc.__class__.__name__ in {
        "NoSuchKey",
        "404",
    }


def build_store(
    destination: str | Path, *, client: Any = None
) -> ArtifactStore:
    """Return a store for ``s3://bucket/prefix`` or a local directory path."""
    text = str(destination)
    if text.startswith("s3://"):
        remainder = text[len("s3://") :]
        bucket, _, prefix = remainder.partition("/")
        if not bucket:
            raise ValueError(f"Invalid S3 destination: {destination}")
        return S3ArtifactStore(bucket, prefix, client=client)
    return LocalArtifactStore(text)


def strategy_keys(strategy: str) -> dict[str, str]:
    """Return the artifact keys a strategy owns in the live store."""
    if not isinstance(strategy, str) or not strategy.strip():
        raise ValueError("strategy must be a nonempty string")
    base = f"live/{strategy}"
    return {
        "state": f"{base}/state.yaml",
        "forecasts": f"{base}/forecasts.parquet",
        "events": f"{base}/retraining_events.parquet",
        "models": f"{base}/models",
    }


def model_key(strategy: str, version: str) -> str:
    """Return the key of one saved model version."""
    return f"{strategy_keys(strategy)['models']}/{version}.json"


MARKET_DATA_KEY = "market/smard_hourly.parquet"


def sorted_unique(frame: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    """Sort and de-duplicate, keeping the last write for a repeated key."""
    return (
        frame.sort_values(list(columns), kind="stable")
        .drop_duplicates(list(columns), keep="last")
        .reset_index(drop=True)
    )
