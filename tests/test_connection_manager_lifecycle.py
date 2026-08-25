import asyncio
import logging

import pytest

from predxt.base import VenueMessage
from predxt.kalshi.connection_manager import (
    KalshiSubscriptionConfig,
    KalshiWsConnectionManager,
)
from predxt.opinion.connection_manager import (
    OpinionSubscriptionConfig,
    OpinionWsConnectionManager,
)
from predxt.polymarket.connection_manager import (
    SubscriptionConfig,
    WsConnectionManager,
)


class IdleClient:
    def __init__(self) -> None:
        self.messages_started = asyncio.Event()
        self.messages_stopped = asyncio.Event()
        self._release_messages = asyncio.Event()
        self.closed = False
        self.close_calls = 0

    async def connect(self, *args, **kwargs) -> None:
        pass

    async def subscribe(self, channels, params) -> None:
        pass

    async def close(self) -> None:
        self.close_calls += 1
        self.closed = True

    async def messages(self):
        self.messages_started.set()
        try:
            await self._release_messages.wait()
            yield VenueMessage()
        finally:
            self.messages_stopped.set()


MANAGER_FACTORIES = [
    pytest.param(
        lambda client: WsConnectionManager(
            client=client,
            config=SubscriptionConfig(assets_ids={"asset-1"}),
        ),
        id="polymarket",
    ),
    pytest.param(
        lambda client: KalshiWsConnectionManager(
            client=client,
            config=KalshiSubscriptionConfig(market_tickers={"market-1"}),
        ),
        id="kalshi",
    ),
    pytest.param(
        lambda client: OpinionWsConnectionManager(
            client=client,
            config=OpinionSubscriptionConfig(market_ids={"market-1"}),
        ),
        id="opinion",
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("manager_factory", MANAGER_FACTORIES)
async def test_stop_completes_for_idle_stream(manager_factory, caplog):
    client = IdleClient()
    manager = manager_factory(client)

    await manager.start()
    await asyncio.wait_for(client.messages_started.wait(), timeout=0.1)

    with caplog.at_level(logging.ERROR):
        await asyncio.wait_for(manager.stop(), timeout=0.1)

    assert client.closed is True
    assert client.close_calls == 1
    assert client.messages_stopped.is_set()
    assert not caplog.records


@pytest.mark.asyncio
@pytest.mark.parametrize("manager_factory", MANAGER_FACTORIES)
async def test_stop_before_start_and_repeated_stop_are_safe(manager_factory):
    client = IdleClient()
    manager = manager_factory(client)

    await asyncio.wait_for(manager.stop(), timeout=0.1)
    await asyncio.wait_for(manager.stop(), timeout=0.1)

    assert client.closed is True
    assert not client.messages_started.is_set()


@pytest.mark.asyncio
@pytest.mark.parametrize("manager_factory", MANAGER_FACTORIES)
async def test_start_while_running_still_fails(manager_factory):
    client = IdleClient()
    manager = manager_factory(client)

    await manager.start()
    await asyncio.wait_for(client.messages_started.wait(), timeout=0.1)
    try:
        with pytest.raises(RuntimeError, match="already running"):
            await manager.start()
    finally:
        await asyncio.wait_for(manager.stop(), timeout=0.1)

    assert client.closed is True
    assert client.messages_stopped.is_set()
