import json
from unittest.mock import AsyncMock

import pytest

from predxt.kalshi.client import KalshiWsClient


@pytest.mark.asyncio
async def test_kalshi_subscribe_payload(monkeypatch):
    mock_ws = AsyncMock()

    async def _fake_connect(*_a, **_kw):
        return mock_ws

    monkeypatch.setattr("websockets.connect", _fake_connect)

    client = KalshiWsClient()
    await client.connect(
        {
            "key_id": "key-1",
            "signature": "sig-1",
            "timestamp": "1700000",
        }
    )
    await client.subscribe(["orderbook_snapshot"], {"market_tickers": ["EVT-1"]})

    assert mock_ws.send.called
    payload = json.loads(mock_ws.send.call_args.args[0])
    assert payload["cmd"] == "subscribe"
    assert payload["params"]["channels"] == ["orderbook_snapshot"]
    assert payload["params"]["market_tickers"] == ["EVT-1"]


def test_kalshi_build_auth_headers():
    headers = KalshiWsClient._build_auth_headers(
        {"key_id": "a", "signature": "b", "timestamp": "c"}
    )
    assert headers == {
        "KALSHI-ACCESS-KEY": "a",
        "KALSHI-ACCESS-SIGNATURE": "b",
        "KALSHI-ACCESS-TIMESTAMP": "c",
    }
