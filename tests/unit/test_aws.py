"""Credential-free tests for the optional S3 artifact mirror."""

import logging
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, call

import pytest

from energy_trading_pipeline.utils.aws import mirror_artifacts

pytestmark = pytest.mark.aws


class FakeBotoCoreError(Exception):
    """Mock SDK base error."""


class FakeClientError(Exception):
    """Mock AWS service error."""


class FakeNoCredentialsError(FakeBotoCoreError):
    """Mock absent credentials."""


class FakeS3UploadFailedError(Exception):
    """Mock managed-transfer failure."""


class FakePartialCredentialsError(FakeBotoCoreError):
    """Mock incomplete credentials."""


@pytest.fixture
def sdk(monkeypatch):
    boto3 = ModuleType("boto3")
    session = Mock()
    boto3.Session = Mock(return_value=session)
    errors = ModuleType("botocore.exceptions")
    errors.BotoCoreError = FakeBotoCoreError
    errors.ClientError = FakeClientError
    errors.NoCredentialsError = FakeNoCredentialsError
    errors.PartialCredentialsError = FakePartialCredentialsError
    transfer_errors = ModuleType("boto3.exceptions")
    transfer_errors.S3UploadFailedError = FakeS3UploadFailedError
    monkeypatch.setitem(sys.modules, "boto3", boto3)
    monkeypatch.setitem(sys.modules, "boto3.exceptions", transfer_errors)
    monkeypatch.setitem(sys.modules, "botocore.exceptions", errors)
    return boto3, session, session.client.return_value


@pytest.fixture
def aws_config():
    return {
        "enabled": True,
        "bucket_name": "research-artifacts",
        "region": "eu-central-1",
        "prefixes": {"models": "models/", "logs": "logs/", "reports": "reports/"},
    }


def make_artifact(root: Path, relative: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"local artifact")
    return path


@pytest.mark.parametrize("config", [None, {}, {"enabled": False}])
def test_disabled_mirror_skips_before_sdk_or_files(config, tmp_path, sdk, caplog):
    result = mirror_artifacts(["missing.parquet"], config, base_dir=tmp_path)
    assert result.uploaded_keys == ()
    assert result.skipped_reason
    assert "skipping" in caplog.text.lower()
    sdk[0].Session.assert_not_called()


def test_selected_artifacts_retain_nested_paths(tmp_path, sdk, aws_config):
    relative_paths = [
        "models/artifacts/model_20261010_120000/model.json",
        "logs/runs/run_20261010_120000/forecasts.parquet",
        "reports/dashboard_exports/metrics.parquet",
    ]
    paths = [make_artifact(tmp_path, name) for name in relative_paths]
    make_artifact(tmp_path, "reports/tables/unselected.csv")
    result = mirror_artifacts(paths, aws_config, base_dir=tmp_path)
    assert result.uploaded_keys == tuple(relative_paths)
    assert result.failed_keys == ()
    assert result.skipped_reason is None
    sdk[1].client.assert_called_once_with("s3", region_name="eu-central-1")
    assert sdk[2].upload_file.call_args_list == [
        call(str(path), "research-artifacts", key)
        for path, key in zip(paths, relative_paths)
    ]
    assert all(path.read_bytes() == b"local artifact" for path in paths)


def test_external_local_root_maps_to_configured_prefix(tmp_path, sdk, aws_config):
    root = tmp_path / "external_models"
    path = make_artifact(root, "artifacts/model_20261010_120000/metadata.yaml")
    aws_config["prefixes"] = {str(root): "demo/models/"}
    result = mirror_artifacts([path], aws_config, base_dir=tmp_path)
    assert result.uploaded_keys == (
        "demo/models/artifacts/model_20261010_120000/metadata.yaml",
    )


def test_relative_selection_is_resolved_against_base_dir(tmp_path, sdk, aws_config):
    make_artifact(tmp_path, "reports/tables/metrics.csv")
    result = mirror_artifacts(
        ["reports/tables/metrics.csv"], aws_config, base_dir=tmp_path
    )
    assert result.uploaded_keys == ("reports/tables/metrics.csv",)


def test_missing_sdk_skips(tmp_path, monkeypatch, aws_config, caplog):
    path = make_artifact(tmp_path, "reports/tables/metrics.csv")
    monkeypatch.setitem(sys.modules, "boto3", None)
    result = mirror_artifacts([path], aws_config, base_dir=tmp_path)
    assert "AWS extra" in result.skipped_reason
    assert "skipping" in caplog.text.lower()


@pytest.mark.parametrize("stage", ["lookup", "client", "upload"])
def test_missing_credentials_skip_clearly(stage, tmp_path, sdk, aws_config, caplog):
    path = make_artifact(tmp_path, "reports/tables/metrics.csv")
    if stage == "lookup":
        sdk[1].get_credentials.return_value = None
    elif stage == "client":
        sdk[1].client.side_effect = FakeNoCredentialsError()
    else:
        sdk[2].upload_file.side_effect = FakeNoCredentialsError()
    result = mirror_artifacts([path], aws_config, base_dir=tmp_path)
    assert "credentials" in result.skipped_reason.lower()
    assert "skipping" in caplog.text.lower()
    assert path.read_bytes() == b"local artifact"
    if stage != "upload":
        sdk[2].upload_file.assert_not_called()


@pytest.mark.parametrize(
    "error", [FakeBotoCoreError, FakeClientError, FakeS3UploadFailedError, OSError]
)
def test_upload_failure_is_reported_and_other_files_continue(
    error, tmp_path, sdk, aws_config, caplog
):
    paths = [make_artifact(tmp_path, f"reports/tables/{i}.csv") for i in range(2)]
    sdk[2].upload_file.side_effect = [error("sensitive SDK detail"), None]
    result = mirror_artifacts(paths, aws_config, base_dir=tmp_path)
    assert result.failed_keys == ("reports/tables/0.csv",)
    assert result.uploaded_keys == ("reports/tables/1.csv",)
    assert "failed" in caplog.text.lower()
    assert "sensitive SDK detail" not in caplog.text
    assert all(path.read_bytes() == b"local artifact" for path in paths)


def test_session_failure_skips_without_affecting_local_files(
    tmp_path, sdk, aws_config, caplog
):
    path = make_artifact(tmp_path, "reports/tables/metrics.csv")
    sdk[0].Session.side_effect = FakeBotoCoreError()
    result = mirror_artifacts([path], aws_config, base_dir=tmp_path)
    assert result.skipped_reason
    assert "skipping" in caplog.text.lower()
    assert path.exists()


def test_partial_credentials_skip_clearly(tmp_path, sdk, aws_config):
    path = make_artifact(tmp_path, "reports/tables/metrics.csv")
    sdk[1].get_credentials.side_effect = FakePartialCredentialsError()
    result = mirror_artifacts([path], aws_config, base_dir=tmp_path)
    assert "credentials" in result.skipped_reason
    sdk[2].upload_file.assert_not_called()


def test_lost_credentials_preserve_partial_results(tmp_path, sdk, aws_config):
    paths = [make_artifact(tmp_path, f"reports/tables/{i}.csv") for i in range(4)]
    sdk[2].upload_file.side_effect = [
        None, FakeClientError(), FakeNoCredentialsError(), None
    ]
    result = mirror_artifacts(paths, aws_config, base_dir=tmp_path)
    assert result.uploaded_keys == ("reports/tables/0.csv",)
    assert result.failed_keys == ("reports/tables/1.csv",)
    assert "credentials" in result.skipped_reason
    assert sdk[2].upload_file.call_count == 3


@pytest.mark.parametrize(
    "update",
    [
        {"enabled": "false"},
        {"bucket_name": ""},
        {"prefixes": {}},
        {"prefixes": {"reports": "../reports/"}},
        {"prefixes": {"reports": "/reports/"}},
        {"prefixes": {"reports": "s3://bucket/reports/"}},
        {"region": 123},
    ],
)
def test_invalid_config_fails_before_sdk(update, tmp_path, sdk, aws_config):
    aws_config.update(update)
    with pytest.raises(ValueError):
        mirror_artifacts([], aws_config, base_dir=tmp_path)
    sdk[0].Session.assert_not_called()


@pytest.mark.parametrize("selection", ["outside", "missing", "directory", "symlink"])
def test_invalid_selection_fails_before_any_upload(
    selection, tmp_path, sdk, aws_config
):
    valid = make_artifact(tmp_path, "reports/tables/valid.csv")
    if selection == "outside":
        invalid = make_artifact(tmp_path, "other/file.csv")
    elif selection == "missing":
        invalid = tmp_path / "reports/missing.csv"
    elif selection == "directory":
        invalid = tmp_path / "reports/tables"
    else:
        external = make_artifact(tmp_path, "outside/file.csv")
        invalid = tmp_path / "reports/link.csv"
        invalid.symlink_to(external)
    with pytest.raises((ValueError, FileNotFoundError)):
        mirror_artifacts([valid, invalid], aws_config, base_dir=tmp_path)
    sdk[0].Session.assert_not_called()


def test_ambiguous_mapping_fails_before_upload(tmp_path, sdk, aws_config):
    path = make_artifact(tmp_path, "reports/tables/metrics.csv")
    aws_config["prefixes"]["reports/tables"] = "tables/"
    with pytest.raises(ValueError, match="mapping"):
        mirror_artifacts([path], aws_config, base_dir=tmp_path)
    sdk[0].Session.assert_not_called()


def test_duplicate_destination_fails_before_upload(tmp_path, sdk, aws_config):
    paths = [make_artifact(tmp_path, f"{root}/file.csv") for root in ["logs", "reports"]]
    aws_config["prefixes"] = {"logs": "outputs/", "reports": "outputs/"}
    with pytest.raises(ValueError, match="Duplicate"):
        mirror_artifacts(paths, aws_config, base_dir=tmp_path)
    sdk[0].Session.assert_not_called()


def test_empty_selection_skips_without_sdk(tmp_path, sdk, aws_config, caplog):
    with caplog.at_level(logging.INFO):
        result = mirror_artifacts([], aws_config, base_dir=tmp_path)
    assert result.skipped_reason
    sdk[0].Session.assert_not_called()
