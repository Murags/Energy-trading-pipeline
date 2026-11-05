"""Credential-free checks for the dashboard's persisted live artifact view."""

from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest
import yaml

from energy_trading_pipeline.dashboard.data_loader import (
    DashboardArtifactError,
    LIVE_STRATEGIES,
    load_live_artifacts,
)


class MissingObject(Exception):
    """Minimal botocore-shaped not-found error."""

    def __init__(self, key: str) -> None:
        self.response = {"Error": {"Code": "NoSuchKey", "Message": key}}
        super().__init__(key)


class FakeS3Client:
    """Read objects from memory and fail if dashboard code attempts a write."""

    def __init__(self, objects: dict[str, bytes]) -> None:
        self.objects = objects
        self.reads: list[str] = []
        self.writes: list[str] = []

    def head_object(self, *, Bucket: str, Key: str) -> dict:
        if Key not in self.objects:
            raise MissingObject(Key)
        return {}

    def get_object(self, *, Bucket: str, Key: str) -> dict:
        if Key not in self.objects:
            raise MissingObject(Key)
        self.reads.append(Key)
        return {"Body": BytesIO(self.objects[Key])}

    def put_object(self, **kwargs) -> None:
        self.writes.append(kwargs["Key"])
        raise AssertionError("The dashboard must never write live artifacts")


def parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    frame.to_parquet(buffer, index=False)
    return buffer.getvalue()


@pytest.fixture
def live_objects() -> dict[str, bytes]:
    timestamps = pd.date_range("2026-11-04", periods=2, freq="h", tz="UTC")
    objects: dict[str, bytes] = {}
    for position, strategy in enumerate(LIVE_STRATEGIES):
        base = f"demo/live/{strategy}"
        forecasts = pd.DataFrame(
            {
                "timestamp": timestamps[::-1],
                "forecast_timestamp": pd.Timestamp("2026-11-03T17:00:00Z"),
                "delivery_date": "2026-11-04",
                "prediction": [float(position + 1), float(position)],
                "actual": [pd.NA, 1.5],
                "strategy": strategy,
                "model_version": f"model_{position}",
            }
        )
        events = pd.DataFrame(
            {
                "timestamp": pd.to_datetime([], utc=True),
                "strategy": pd.Series(dtype="string"),
                "trigger_reason": pd.Series(dtype="string"),
                "threshold": pd.Series(dtype="float64"),
                "rolling_rmse": pd.Series(dtype="float64"),
                "training_window_start": pd.to_datetime([], utc=True),
                "training_window_end": pd.to_datetime([], utc=True),
                "model_version": pd.Series(dtype="string"),
            }
        )
        state = {
            "strategy": strategy,
            "model_version": f"model_{position}",
            "last_issuance": "2026-11-03T17:00:00+00:00",
            "last_delivery_date": "2026-11-04",
            "retraining_count": position,
            "updated_at": "2026-11-03T18:15:00+00:00",
        }
        objects[f"{base}/forecasts.parquet"] = parquet_bytes(forecasts)
        objects[f"{base}/retraining_events.parquet"] = parquet_bytes(events)
        objects[f"{base}/state.yaml"] = yaml.safe_dump(state).encode()

    latest = {
        "ran_at": "2026-11-03T18:15:00+00:00",
        "issuance": "2026-11-03T17:00:00+00:00",
        "delivery_date": "2026-11-04",
        "market_rows": 100,
        "market_through": "2026-11-04T23:00:00+00:00",
        "strategies": [
            {
                "strategy": strategy,
                "delivery_date": "2026-11-04",
                "issuance": "2026-11-03T17:00:00+00:00",
                "hours": 2,
                "model_version": f"model_{position}",
                "retrained": position > 0,
                "reissued": False,
                "retraining_count": position,
            }
            for position, strategy in enumerate(LIVE_STRATEGIES)
        ],
    }
    objects["demo/live/latest_run.yaml"] = yaml.safe_dump(latest).encode()
    return objects


def test_load_live_artifacts_from_s3_prefix_is_read_only(live_objects):
    client = FakeS3Client(live_objects)

    loaded = load_live_artifacts("s3://artifact-bucket/demo", client=client)

    assert set(loaded) == {"forecasts", "retraining_events", "states", "latest_run"}
    assert len(loaded["forecasts"]) == 6
    assert loaded["forecasts"]["timestamp"].is_monotonic_increasing
    assert set(loaded["states"]["strategy"]) == set(LIVE_STRATEGIES)
    assert loaded["latest_run"]["delivery_date"] == "2026-11-04"
    assert len(client.reads) == 11
    assert not client.writes


def test_missing_strategy_artifact_names_the_required_key(live_objects):
    key = "demo/live/fixed_schedule/forecasts.parquet"
    del live_objects[key]

    with pytest.raises(
        DashboardArtifactError,
        match="live/fixed_schedule/forecasts.parquet",
    ):
        load_live_artifacts(
            "s3://artifact-bucket/demo", client=FakeS3Client(live_objects)
        )


def test_live_state_strategy_mismatch_is_rejected(live_objects):
    key = "demo/live/no_retraining/state.yaml"
    state = yaml.safe_load(live_objects[key])
    state["strategy"] = "fixed_schedule"
    live_objects[key] = yaml.safe_dump(state).encode()

    with pytest.raises(DashboardArtifactError, match="expected 'no_retraining'"):
        load_live_artifacts(
            "s3://artifact-bucket/demo", client=FakeS3Client(live_objects)
        )


def test_forecast_strategy_mismatch_is_rejected(live_objects):
    key = "demo/live/no_retraining/forecasts.parquet"
    frame = pd.read_parquet(BytesIO(live_objects[key]))
    frame["strategy"] = "fixed_schedule"
    live_objects[key] = parquet_bytes(frame)

    with pytest.raises(DashboardArtifactError, match="expected only 'no_retraining'"):
        load_live_artifacts(
            "s3://artifact-bucket/demo", client=FakeS3Client(live_objects)
        )


def test_incomplete_latest_run_is_rejected(live_objects):
    key = "demo/live/latest_run.yaml"
    latest = yaml.safe_load(live_objects[key])
    latest["strategies"] = latest["strategies"][:-1]
    live_objects[key] = yaml.safe_dump(latest).encode()

    with pytest.raises(DashboardArtifactError, match="three canonical strategies"):
        load_live_artifacts(
            "s3://artifact-bucket/demo", client=FakeS3Client(live_objects)
        )


@pytest.mark.parametrize("destination", ["", "s3://"])
def test_invalid_live_store_fails_clearly(destination):
    with pytest.raises(DashboardArtifactError, match="live artifact store"):
        load_live_artifacts(destination, client=FakeS3Client({}))


def test_streamlit_live_tab_reads_configured_store(tmp_path, live_objects, monkeypatch):
    testing = pytest.importorskip("streamlit.testing.v1")
    store = tmp_path / "live_store"
    for key, payload in live_objects.items():
        path = store / key.removeprefix("demo/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    monkeypatch.setenv("ETP_STORE", str(store))
    app_path = (
        Path(__file__).resolve().parents[2]
        / "src/energy_trading_pipeline/dashboard/app.py"
    )

    app = testing.AppTest.from_file(str(app_path)).run(timeout=15)

    assert not app.exception
    assert "Live" in [tab.label for tab in app.tabs]
    assert any("Last run:" in caption.value for caption in app.caption)
    assert len(app.get("plotly_chart")) >= 1
    assert any("strategy" in table.value for table in app.dataframe)
