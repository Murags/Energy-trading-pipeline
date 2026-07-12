"""Unit tests for optional external API adapter interfaces."""

import logging

import pandas as pd
import pytest

from energy_trading_pipeline.data_ingestion.entsoe_client import EntsoeClient
from energy_trading_pipeline.data_ingestion.local_loader import load_local_data
from energy_trading_pipeline.data_ingestion.open_meteo_client import OpenMeteoClient


@pytest.mark.parametrize(
    ("client", "source_name"),
    [
        (EntsoeClient(), "ENTSO-E"),
        (OpenMeteoClient(), "Open-Meteo"),
    ],
)
def test_unconfigured_adapter_skips_fetch_with_local_cache_fallback(
    client, source_name, caplog
):
    with caplog.at_level(logging.WARNING):
        result = client.fetch()

    assert client.is_configured is False
    assert result is None
    assert source_name in caplog.text
    assert "not configured" in caplog.text
    assert "local cached file" in caplog.text


def test_missing_api_configuration_does_not_block_local_loading(tmp_path, monkeypatch):
    cached_path = tmp_path / "cached_prices.csv"
    cached_path.write_text(
        "timestamp,price_de,price_fr\n2026-01-01T00:00:00Z,50.0,48.0\n",
        encoding="utf-8",
    )

    def fail_if_network_is_used(*args, **kwargs):
        raise AssertionError("Network access is not allowed in local fallback tests")

    monkeypatch.setattr("socket.create_connection", fail_if_network_is_used)

    assert EntsoeClient(api_key="").fetch() is None
    assert OpenMeteoClient(enabled=False).fetch() is None

    result = load_local_data(cached_path)

    expected = pd.DataFrame(
        {
            "timestamp": ["2026-01-01T00:00:00Z"],
            "price_de": [50.0],
            "price_fr": [48.0],
        }
    )
    pd.testing.assert_frame_equal(result, expected)


def test_entsoe_client_treats_whitespace_api_key_as_unconfigured():
    client = EntsoeClient(api_key="   ")

    assert client.is_configured is False
    assert client.fetch() is None


@pytest.mark.parametrize(
    "client",
    [EntsoeClient(api_key="configured-placeholder"), OpenMeteoClient(enabled=True)],
)
def test_configured_adapter_does_not_attempt_unimplemented_fetch(client):
    with pytest.raises(NotImplementedError, match="not implemented"):
        client.fetch()
