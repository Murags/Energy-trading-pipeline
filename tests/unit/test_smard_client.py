"""SMARD client chunk selection, interval handling and provenance, offline."""

import hashlib
import json
import urllib.error

import numpy as np
import pandas as pd
import pytest

from energy_trading_pipeline.data_ingestion.smard_client import (
    SMARD_BASE_URL,
    SMARD_SERIES,
    SmardClient,
    missing_hours,
    select_chunks,
)

WEEK = pd.Timedelta(days=7)
T0 = pd.Timestamp("2024-01-01 00:00", tz="UTC")
STAMPS = [int((T0 + n * WEEK).value // 10**6) for n in range(3)]


def _series_payload(start, hours, value=lambda i: float(i), gaps=()):
    stamps = pd.date_range(start, periods=hours, freq="h")
    return json.dumps(
        {
            "series": [
                [int(t.value // 10**6), None if i in gaps else value(i)]
                for i, t in enumerate(stamps)
            ]
        }
    ).encode()


class FakeSmard:
    """Serve an index and weekly chunks for one or more filters."""

    def __init__(self, gaps=None, chunk_weeks=3):
        self.requests = []
        self.pages = {}
        for column, filter_id in SMARD_SERIES.items():
            prefix = f"{SMARD_BASE_URL}/{filter_id}/DE"
            stamps = STAMPS[:chunk_weeks]
            self.pages[f"{prefix}/index_hour.json"] = json.dumps(
                {"timestamps": stamps}
            ).encode()
            for week, stamp in enumerate(stamps):
                start = pd.Timestamp(stamp, unit="ms", tz="UTC")
                self.pages[f"{prefix}/{filter_id}_DE_hour_{stamp}.json"] = (
                    _series_payload(
                        start,
                        168,
                        value=lambda i, w=week: float(w * 1000 + i),
                        gaps=(gaps or {}).get(column, ()) if week == 0 else (),
                    )
                )

    def __call__(self, url):
        self.requests.append(url)
        return self.pages[url]


def client(fake, **kwargs):
    return SmardClient(fake, request_delay_seconds=0, sleep=lambda _: None, **kwargs)


def test_fetch_series_returns_half_open_utc_hours():
    frame = client(FakeSmard()).fetch_series(
        "price_de", T0 + pd.Timedelta(hours=24), T0 + pd.Timedelta(hours=48)
    )

    assert len(frame) == 24
    assert frame["timestamp"].iloc[0] == T0 + pd.Timedelta(hours=24)
    assert frame["timestamp"].iloc[-1] == T0 + pd.Timedelta(hours=47)
    assert str(frame["timestamp"].dtype) == "datetime64[ns, UTC]"
    assert frame.columns.tolist() == ["timestamp", "price_de"]


def test_only_overlapping_weekly_chunks_are_requested():
    fake = FakeSmard()
    client(fake).fetch_series("price_de", T0 + WEEK, T0 + WEEK + pd.Timedelta(hours=5))

    chunk_requests = [url for url in fake.requests if "index" not in url]
    assert chunk_requests == [
        f"{SMARD_BASE_URL}/4169/DE/4169_DE_hour_{STAMPS[1]}.json"
    ]


def test_interval_spanning_a_chunk_boundary_reads_both_chunks():
    fake = FakeSmard()
    frame = client(fake).fetch_series(
        "price_de", T0 + WEEK - pd.Timedelta(hours=2), T0 + WEEK + pd.Timedelta(hours=2)
    )

    assert len(frame) == 4
    # Last two hours of week 0, then the first two of week 1.
    assert frame["price_de"].tolist() == [166.0, 167.0, 1000.0, 1001.0]
    assert sum("index" not in url for url in fake.requests) == 2


def test_unpublished_values_stay_missing_and_are_not_dropped():
    fake = FakeSmard(gaps={"price_de": (3, 4)})
    frame = client(fake).fetch_series("price_de", T0, T0 + pd.Timedelta(hours=6))

    assert len(frame) == 6
    assert frame["price_de"].isna().tolist() == [False, False, False, True, True, False]


def test_fetch_frame_builds_a_complete_hourly_index_with_gaps_kept():
    # Only one week published, but two weeks requested.
    fake = FakeSmard(chunk_weeks=1)
    start, end = T0 + WEEK - pd.Timedelta(hours=2), T0 + WEEK + pd.Timedelta(hours=2)

    frame = client(fake).fetch_frame(["price_de", "forecast_pv_wind_de"], start, end)

    assert frame["timestamp"].tolist() == list(
        pd.date_range(start, end, freq="h", inclusive="left")
    )
    assert str(frame["timestamp"].dtype) == "datetime64[ns, UTC]"
    assert missing_hours(frame, ["price_de", "forecast_pv_wind_de"]) == {
        "price_de": 2,
        "forecast_pv_wind_de": 2,
    }


def test_select_chunks_bounds_the_final_unfinished_week():
    late = T0 + 2 * WEEK + pd.Timedelta(days=3)
    assert select_chunks(STAMPS, late, late + pd.Timedelta(hours=1)) == [STAMPS[2]]
    assert select_chunks(STAMPS, T0 - WEEK, T0 - pd.Timedelta(hours=1)) == []


@pytest.mark.parametrize(
    "start,end,message",
    [
        (pd.Timestamp("2024-01-01"), T0, "timezone-aware"),
        (T0, T0, "precede"),
        (T0 + pd.Timedelta(hours=1), T0, "precede"),
    ],
)
def test_invalid_intervals_fail_clearly(start, end, message):
    with pytest.raises(ValueError, match=message):
        client(FakeSmard()).fetch_series("price_de", start, end)


def test_unknown_series_fails_clearly():
    with pytest.raises(ValueError, match="Unknown SMARD series"):
        client(FakeSmard()).fetch_series("load_fr", T0, T0 + pd.Timedelta(hours=1))


def test_transient_failures_are_retried():
    fake = FakeSmard()
    failures = {"left": 2}

    def flaky(url):
        if failures["left"]:
            failures["left"] -= 1
            raise urllib.error.URLError("temporary")
        return fake(url)

    frame = client(flaky, retries=3).fetch_series(
        "price_de", T0, T0 + pd.Timedelta(hours=2)
    )
    assert len(frame) == 2


def test_persistent_failure_raises_after_retries():
    def down(url):
        raise urllib.error.URLError("down")

    with pytest.raises(ConnectionError, match="SMARD request failed"):
        client(down, retries=2).fetch_series("price_de", T0, T0 + pd.Timedelta(hours=1))


def test_every_response_is_recorded_with_its_sha256():
    fake = FakeSmard()
    archived = {}
    smard = client(fake, raw_sink=lambda name, payload: archived.setdefault(name, payload))

    smard.fetch_series("price_de", T0, T0 + pd.Timedelta(hours=1))

    assert len(smard.manifest) == len(fake.requests) == 2
    for entry in smard.manifest:
        payload = fake.pages[entry["url"]]
        assert entry["sha256"] == hashlib.sha256(payload).hexdigest()
        assert archived[entry["file"]] == payload


@pytest.mark.external_api
def test_live_smard_returns_recent_day_ahead_prices():
    end = pd.Timestamp.now(tz="UTC").floor("h") - pd.Timedelta(days=1)
    start = end - pd.Timedelta(days=2)
    frame = SmardClient().fetch_frame(["price_de", "price_fr"], start, end)

    assert len(frame) == 48
    assert np.isfinite(frame[["price_de", "price_fr"]].to_numpy()).all()
