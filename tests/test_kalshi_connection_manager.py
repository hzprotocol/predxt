import asyncio

import pytest

from predxt.base import VenueMessage
from predxt.kalshi.connection_manager import (
    KalshiSubscriptionConfig,
    KalshiWsConnectionManager,
)


class DummyKalshiClient:
    def __init__(self, messages):
        self._messages = messages
        self.connected = False
        self.subscriptions = []
        self.closed = False
        self.auth_params = None

    async def connect(self, auth_params=None, *_, **__):
        self.connected = True
        self.auth_params = auth_params

    async def subscribe(self, channels, params):
        self.subscriptions.append((tuple(channels), params))

    async def close(self):
        self.closed = True

    def messages(self):
        async def gen():
            for message in self._messages:
                yield message

        return gen()


def _message(market_ticker: str) -> VenueMessage:
    vm = VenueMessage()
    vm.venue = "kalshi"
    vm.raw_data = {"market_ticker": market_ticker, "type": "orderbook_snapshot"}
    vm.timestamp_ms = 1
    return vm


@pytest.mark.asyncio
async def test_kalshi_market_specific_callback():
    client = DummyKalshiClient([_message("EVT-1"), _message("EVT-2")])
    manager = KalshiWsConnectionManager(
        client=client,
        config=KalshiSubscriptionConfig(market_tickers={"EVT-1", "EVT-2"}),
    )

    seen = []

    async def _cb(msg):
        seen.append(msg.raw_data["market_ticker"])

    manager.on_message(_cb, market_ticker="EVT-2")
    await manager.start()
    await asyncio.sleep(0)
    await manager.stop()

    assert seen == ["EVT-2"]
    assert client.connected is True
    assert client.closed is True


@pytest.mark.asyncio
async def test_kalshi_connection_manager_supports_multiple_channels():
    client = DummyKalshiClient([_message("EVT-1")])
    manager = KalshiWsConnectionManager(
        client=client,
        config=KalshiSubscriptionConfig(
            market_tickers={"EVT-1"},
            channels=["orderbook_delta", "ticker", "trade"],
        ),
    )

    await manager.start()
    await asyncio.sleep(0)
    await manager.stop()

    channels, _params = client.subscriptions[0]
    assert channels == ("orderbook_delta", "ticker", "trade")


@pytest.mark.asyncio
async def test_kalshi_connection_manager_passes_auth_params():
    client = DummyKalshiClient([_message("EVT-1")])
    manager = KalshiWsConnectionManager(
        client=client,
        config=KalshiSubscriptionConfig(market_tickers={"EVT-1"}),
    )

    await manager.start(auth_params={"key_id": "k1"})
    await asyncio.sleep(0)
    await manager.stop()

    assert client.auth_params == {"key_id": "k1"}
