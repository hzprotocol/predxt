import asyncio

import pytest

from predxt.base import VenueMessage
from predxt.polymarket.connection_manager import (
    SubscriptionConfig,
    WsConnectionManager,
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


def _venue_message(asset_id: str, msg_type: str = "book") -> VenueMessage:
    vm = VenueMessage()
    vm.venue = "polymarket"
    vm.raw_data = {"asset_id": asset_id, "type": msg_type}
    vm.timestamp_ms = 0
    return vm


@pytest.mark.asyncio
async def test_global_and_asset_callbacks_invoked():
    vm1 = _venue_message("asset-1")
    client = DummyClient([vm1])

    manager = WsConnectionManager(
        client=client,
        config=SubscriptionConfig(assets_ids={"asset-1"}),
    )

    global_called = asyncio.Event()
    asset_called = asyncio.Event()

    async def _global_cb(msg):
        assert msg.raw_data["asset_id"] == "asset-1"
        global_called.set()

    async def _asset_cb(msg):
        assert msg.raw_data["asset_id"] == "asset-1"
        asset_called.set()

    manager.on_message(_global_cb)
    manager.on_message(_asset_cb, asset_id="asset-1")

    await manager.start()
    await asyncio.wait_for(global_called.wait(), timeout=1)
    await asyncio.wait_for(asset_called.wait(), timeout=1)
    await manager.stop()

    assert client.connected is True
    assert client.closed is True


@pytest.mark.asyncio
async def test_asset_specific_callback_filters_messages():
    vm1 = _venue_message("asset-1")
    vm2 = _venue_message("asset-2")
    client = DummyClient([vm1, vm2])

    manager = WsConnectionManager(
        client=client,
        config=SubscriptionConfig(assets_ids={"asset-1", "asset-2"}),
    )

    hits = []

    async def _asset1_cb(msg):
        hits.append(msg.raw_data["asset_id"])

    manager.on_message(_asset1_cb, asset_id="asset-1")

    await manager.start()
    await asyncio.sleep(0)
    await manager.stop()

    assert hits == ["asset-1"]


@pytest.mark.asyncio
async def test_refresh_subscription_updates_params():
    vm = _venue_message("asset-1")
    client = DummyClient([vm])
    manager = WsConnectionManager(
        client=client,
        config=SubscriptionConfig(assets_ids={"asset-1"}),
    )

    await manager.start()
    manager.add_asset("asset-2")
    await manager.refresh_subscription()
    await manager.stop()

    # Expect two subscribe calls (start + refresh)
    assert len(client.subscriptions) == 2
    _, params_after_refresh = client.subscriptions[-1]
    assert params_after_refresh["assets_ids"] == ["asset-1", "asset-2"]
