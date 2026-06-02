import asyncio

import pytest

from predxt.base import VenueMessage
from predxt.opinion.connection_manager import (
    OpinionSubscriptionConfig,
    OpinionWsConnectionManager,
)


class DummyClient:
    def __init__(self, messages):
        self._messages = messages
        self.connected = False
        self.subscriptions = []
        self.closed = False

    async def connect(self, *_, **__):
        self.connected = True

    async def subscribe(self, channels, params):
        self.subscriptions.append((tuple(channels), params))

    async def close(self):
        self.closed = True

    def messages(self):
        async def gen():
            for msg in self._messages:
                yield msg

        return gen()


def _venue_message(market_id: str) -> VenueMessage:
    vm = VenueMessage()
    vm.venue = "opinion"
    vm.raw_data = {"market_id": market_id, "type": "depth_diff"}
    vm.timestamp_ms = 0
    return vm


@pytest.mark.asyncio
async def test_opinion_market_callback_filters_messages():
    client = DummyClient([_venue_message("1"), _venue_message("2")])
    manager = OpinionWsConnectionManager(
        client=client,
        config=OpinionSubscriptionConfig(market_ids={"1", "2"}),
    )
    hits = []

    async def _market_cb(msg):
        hits.append(msg.raw_data["market_id"])

    manager.on_message(_market_cb, market_id="1")
    await manager.start(auth_params={"api_key": "key"})
    await asyncio.sleep(0)
    await manager.stop()

    assert hits == ["1"]
    assert client.subscriptions[0][1]["market_ids"] == ["1", "2"]
