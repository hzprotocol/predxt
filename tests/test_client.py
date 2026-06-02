import json
from unittest.mock import AsyncMock

import pytest

from predxt.polymarket.client import PolymarketWsClient


@pytest.mark.asyncio
async def test_subscribe_payload_and_health(monkeypatch):
    mock_ws = AsyncMock()

    async def _fake_connect(*a, **kw):
        return mock_ws

    monkeypatch.setattr("websockets.connect", _fake_connect)

    client = PolymarketWsClient()
    await client.connect()

    await client.subscribe(
        ["market"],
        {"assets_ids": ["0x1"], "initial_dump": True, "custom_feature_enabled": False},
    )

    # Ensure the websocket send was called with JSON payload containing keys
    assert mock_ws.send.called
    sent = json.loads(mock_ws.send.call_args.args[0])
    assert sent["type"] == "market"
    # assets_ids should be forwarded as provided
    assert "assets_ids" in sent
    assert sent["assets_ids"] == ["0x1"]
    # channels must be included per protocol
    assert sent["channels"] == ["market"]

    # health should reflect connected
    h = client.health()
    assert h.connected is True


@pytest.mark.asyncio
async def test_health_error_tracking(monkeypatch):
    """Verify that connection errors are recorded in health metrics."""

    # Mock connect to raise an exception once, then succeed (or fail repeatedly)
    # Here we fail repeatedly to check error recording
    async def _fail_connect(*a, **kw):
        raise OSError("Network Unreachable")

    monkeypatch.setattr("websockets.connect", _fail_connect)

    # Speed up backoff for test
    client = PolymarketWsClient(max_reconnect_attempts=1)
    client._backoff.base = 0.01

    # Expect connect to fail
    with pytest.raises(ConnectionError):
        await client.connect()

    h = client.health()
    assert h.connected is False
    assert h.last_error == "Network Unreachable"
    assert h.last_error_timestamp_ms is not None


@pytest.mark.asyncio
async def test_handle_raw_message_expands_price_change_batches():
    client = PolymarketWsClient()
    raw_message = json.dumps(
        {
            "event_type": "price_change",
            "price_changes": [
                {
                    "asset_id": "asset-1",
                    "best_bid": "0.41",
                    "best_ask": "0.43",
                    "hash": "hash-1",
                },
                {
                    "asset_id": "asset-2",
                    "best_bid": "0.22",
                    "best_ask": "0.24",
                    "hash": "hash-2",
                },
            ],
        }
    )

    messages = [
        vm async for vm in client._handle_raw_message(raw_message, seen_hashes=set())
    ]

    assert len(messages) == 2
    assert [vm.raw_data["asset_id"] for vm in messages] == ["asset-1", "asset-2"]
    assert messages[0].venue == "polymarket"
    assert messages[0].event_type == "price_change"
    assert messages[0].asset_id == "asset-1"
    assert messages[0].received_at_ms == messages[0].timestamp_ms
    assert client.health().messages_received == 2


@pytest.mark.asyncio
async def test_handle_raw_message_ignores_non_json_keepalive():
    client = PolymarketWsClient()

    messages = [
        vm async for vm in client._handle_raw_message("PONG", seen_hashes=set())
    ]

    assert messages == []
    assert client.health().messages_received == 0
