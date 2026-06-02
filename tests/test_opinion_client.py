import json
import asyncio
from unittest.mock import AsyncMock

import pytest

from predxt.opinion.client import OpinionWsClient


@pytest.mark.asyncio
async def test_opinion_connect_subscribe_and_heartbeat(monkeypatch):
    mock_ws = AsyncMock()

    async def _fake_connect(url):
        assert url == "wss://ws.opinion.trade?apikey=key-1"
        return mock_ws

    monkeypatch.setattr("websockets.connect", _fake_connect)
    client = OpinionWsClient(api_key="key-1", heartbeat_seconds=0.01)

    await client.connect()
    await client.subscribe(["market.depth.diff"], {"market_ids": ["2764"]})

    sent = [json.loads(call.args[0]) for call in mock_ws.send.call_args_list]
    assert {
        "action": "SUBSCRIBE",
        "channel": "market.depth.diff",
        "marketId": 2764,
    } in sent

    await asyncio.sleep(0.02)
    sent = [json.loads(call.args[0]) for call in mock_ws.send.call_args_list]
    assert {"action": "HEARTBEAT"} in sent
    await client.close()


@pytest.mark.asyncio
async def test_opinion_handle_raw_message_parses_depth_diff():
    client = OpinionWsClient(api_key="key-1")
    raw_message = json.dumps(
        {
            "marketId": 2764,
            "tokenId": "yes-token",
            "outcomeSide": 1,
            "side": "asks",
            "price": "0.55",
            "size": "12",
            "msgType": "market.depth.diff",
        }
    )

    messages = [
        vm async for vm in client._handle_raw_message(raw_message, seen_hashes=set())
    ]

    assert len(messages) == 1
    assert messages[0].venue == "opinion"
    assert messages[0].event_type == "depth_diff"
    assert messages[0].raw_data["market_id"] == "2764"
    assert messages[0].market_id == "2764"
