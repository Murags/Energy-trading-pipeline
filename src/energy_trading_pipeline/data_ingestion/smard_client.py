"""Fetch hourly SMARD chart series for a half-open UTC interval.

SMARD (Bundesnetzagentur) publishes each series as weekly JSON chunks listed by
an index. This client selects only the chunks overlapping the requested
interval, keeps every response's SHA-256 for provenance, and returns values
unchanged: unpublished hours stay missing rather than being filled.
"""

from collections.abc import Callable, Sequence
from datetime import datetime, timezone
import hashlib
import json
import logging
import time
import urllib.error
import urllib.request

import pandas as pd

LOGGER = logging.getLogger(__name__)

SMARD_BASE_URL = "https://www.smard.de/app/chart_data"
SMARD_REGION = "DE"
SMARD_RESOLUTION = "hour"
# Canonical column name -> SMARD filter id. Prices are day-ahead auction results;
# the forecasts are the TSOs' day-ahead generation forecasts under Regulation
# (EU) 543/2013 Art. 14(1)(c)/(d), published by 18:00 on the preceding day.
SMARD_SERIES = {
    "price_de": 4169,
    "price_fr": 254,
    "forecast_pv_wind_de": 5097,
    "forecast_generation_total_de": 122,
}
USER_AGENT = "academic-research"
# Bound for the final chunk, whose successor is not yet listed in the index.
_LAST_CHUNK_SPAN_MS = 8 * 24 * 3600 * 1000

Transport = Callable[[str], bytes]


def _http_get(url: str, *, timeout: float = 60.0) -> bytes:
    """Fetch one URL with an identifying User-Agent."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _utc(value: pd.Timestamp, name: str) -> pd.Timestamp:
    """Require an aware timestamp rather than assuming a timezone."""
    if not isinstance(value, pd.Timestamp) or pd.isna(value) or value.tzinfo is None:
        raise ValueError(f"{name} must be a timezone-aware pandas timestamp")
    return value.tz_convert("UTC")


class SmardClient:
    """Download SMARD series with retries, provenance, and no network in tests.

    ``transport`` performs the raw GET; tests inject a fake. ``raw_sink``
    receives each response's bytes under a stable file name so callers can
    archive raw data. ``manifest`` accumulates URL, SHA-256, size and retrieval
    time for every response fetched by this instance.
    """

    def __init__(
        self,
        transport: Transport | None = None,
        *,
        retries: int = 3,
        backoff_seconds: float = 2.0,
        request_delay_seconds: float = 0.15,
        raw_sink: Callable[[str, bytes], None] | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if isinstance(retries, bool) or not isinstance(retries, int) or retries < 0:
            raise ValueError("retries must be a non-negative integer")
        self._transport = transport or _http_get
        self._retries = retries
        self._backoff = backoff_seconds
        self._delay = request_delay_seconds
        self._raw_sink = raw_sink
        self._sleep = sleep
        self.manifest: list[dict[str, object]] = []

    def _get_json(self, url: str, name: str) -> object:
        """Fetch, record provenance, and parse one JSON document."""
        for attempt in range(self._retries + 1):
            try:
                payload = self._transport(url)
                break
            except (urllib.error.URLError, OSError, TimeoutError) as exc:
                if attempt == self._retries:
                    raise ConnectionError(f"SMARD request failed: {url}") from exc
                LOGGER.warning("SMARD request failed (attempt %d): %s", attempt + 1, url)
                self._sleep(self._backoff * (attempt + 1))
        self.manifest.append(
            {
                "url": url,
                "file": name,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "bytes": len(payload),
                "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        )
        if self._raw_sink is not None:
            self._raw_sink(name, payload)
        if self._delay:
            self._sleep(self._delay)
        return json.loads(payload)

    def fetch_series(
        self, column: str, start: pd.Timestamp, end: pd.Timestamp
    ) -> pd.DataFrame:
        """Return ``timestamp`` and ``column`` for hours in ``[start, end)``.

        Timestamps are UTC hour starts. Hours SMARD has not published are
        returned as missing values, not dropped and not filled.
        """
        if column not in SMARD_SERIES:
            raise ValueError(f"Unknown SMARD series: {column}")
        start, end = _utc(start, "start"), _utc(end, "end")
        if start >= end:
            raise ValueError("start must precede end")
        filter_id = SMARD_SERIES[column]
        prefix = f"{SMARD_BASE_URL}/{filter_id}/{SMARD_REGION}"
        index = self._get_json(
            f"{prefix}/index_{SMARD_RESOLUTION}.json",
            f"index_{filter_id}_{SMARD_REGION}_{SMARD_RESOLUTION}.json",
        )
        stamps = sorted(index["timestamps"])
        points: list[list[object]] = []
        for stamp in select_chunks(stamps, start, end):
            name = f"{filter_id}_{SMARD_REGION}_{SMARD_RESOLUTION}_{stamp}.json"
            points.extend(self._get_json(f"{prefix}/{name}", name)["series"])
        frame = pd.DataFrame(points, columns=["timestamp", column])
        frame["timestamp"] = pd.to_datetime(
            frame["timestamp"], unit="ms", utc=True
        ).dt.as_unit("ns")
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("float64")
        frame = frame.loc[(frame["timestamp"] >= start) & (frame["timestamp"] < end)]
        frame = frame.drop_duplicates("timestamp").sort_values("timestamp")
        return frame.reset_index(drop=True)

    def fetch_frame(
        self, columns: Sequence[str], start: pd.Timestamp, end: pd.Timestamp
    ) -> pd.DataFrame:
        """Fetch several series onto one complete hourly UTC index.

        Every hour in ``[start, end)`` appears exactly once; unpublished values
        stay missing so callers can decide whether the interval is usable.
        """
        if isinstance(columns, str) or not columns:
            raise ValueError("columns must be a nonempty sequence of series names")
        if len(set(columns)) != len(columns):
            raise ValueError("columns must be unique")
        start, end = _utc(start, "start"), _utc(end, "end")
        # One timestamp resolution throughout, matching the pipeline's ns UTC.
        result = pd.DataFrame(
            {
                "timestamp": pd.date_range(
                    start, end, freq="h", inclusive="left"
                ).as_unit("ns")
            }
        )
        for column in columns:
            series = self.fetch_series(column, start, end)
            result = result.merge(series, on="timestamp", how="left", validate="one_to_one")
        return result


def select_chunks(
    stamps: Sequence[int], start: pd.Timestamp, end: pd.Timestamp
) -> list[int]:
    """Return weekly chunk starts (ms) whose span overlaps ``[start, end)``."""
    start_ms = _utc(start, "start").value // 10**6
    end_ms = _utc(end, "end").value // 10**6
    ordered = sorted(stamps)
    selected = []
    for position, stamp in enumerate(ordered):
        following = (
            ordered[position + 1]
            if position + 1 < len(ordered)
            else stamp + _LAST_CHUNK_SPAN_MS
        )
        if stamp < end_ms and following > start_ms:
            selected.append(stamp)
    return selected


def missing_hours(frame: pd.DataFrame, columns: Sequence[str]) -> dict[str, int]:
    """Count hours with no published value, per column."""
    return {column: int(frame[column].isna().sum()) for column in columns}
