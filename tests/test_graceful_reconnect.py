"""Offline lifecycle regressions; no venue credentials or network calls are used."""

import asyncio
import importlib
import json
from collections import deque
from unittest.mock import AsyncMock, Mock

import pytest
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
from websockets.frames import Close

from predxt.kalshi import KalshiWsClient
from predxt.kalshi.connection_manager import KalshiWsConnectionManager
from predxt.opinion import OpinionWsClient
from predxt.opinion.connection_manager import OpinionWsConnectionManager
from predxt.polymarket import PolymarketWsClient
from predxt.polymarket.connection_manager import WsConnectionManager


class Socket:
    def __init__(self, *payloads, idle=False, error=None):
        self.payloads = deque(json.dumps(p) for p in payloads)
        self.idle = idle
        self.error = error
        self.iterations = 0
        self.reading = asyncio.Event()
        self.closed = asyncio.Event()
        self.send = AsyncMock()
        self.close = AsyncMock(side_effect=self.closed.set)

    def __aiter__(self):
        self.iterations += 1
        # Fail synchronously on the old bug, even if it starves the event loop.
        assert self.iterations == 1, "exhausted socket iterated again (busy loop)"
        return self

    async def __anext__(self):
        self.reading.set()
        if self.payloads:
            return self.payloads.popleft()
        if self.idle:
            await self.closed.wait()
        if self.error is not None:
            raise self.error
        raise StopAsyncIteration


@pytest.fixture(params=["polymarket", "kalshi", "opinion"])
def venue(request, monkeypatch):
    name = request.param
    if name == "polymarket":
        client = PolymarketWsClient()
        auth = None
        channels, params = ["market"], {"assets_ids": ["test-asset"]}
        payload = {
            "event_type": "price_change",
            "asset_id": "test-asset",
            "price": "0.55",
            "hash": "test-hash",
        }
        manager = WsConnectionManager(client=client, initial_assets=["test-asset"])
    elif name == "kalshi":
        client = KalshiWsClient()
        # Stub signing itself; no precomputed signatures or credentials are needed.
        monkeypatch.setattr(client, "_build_auth_headers", lambda *a, **kw: {})
        auth = {"test_auth_marker": "preserved"}
        channels, params = ["orderbook_delta"], {"market_tickers": ["TEST-MARKET"]}
        payload = {
            "type": "orderbook_delta",
            "msg": {
                "market_ticker": "TEST-MARKET",
                "price": "0.55",
                "hash": "test-hash",
            },
        }
        manager = KalshiWsConnectionManager(
            client=client, initial_markets=["TEST-MARKET"]
        )
    else:
        client = OpinionWsClient(heartbeat_seconds=3600)
        monkeypatch.setattr(client, "_resolve_api_key", lambda: "offline-test-only")
        auth = {"test_auth_marker": "preserved"}
        channels, params = ["market.depth.diff"], {"market_ids": ["123"]}
        payload = {
            "msgType": "market.depth.diff",
            "marketId": 123,
            "price": "0.55",
            "size": "12",
        }
        manager = OpinionWsConnectionManager(client=client, initial_markets=["123"])
    return name, client, auth, channels, params, payload, manager


async def start_client(venue, monkeypatch, *sockets):
    name, client, auth, channels, params, _, _ = venue
    connect = AsyncMock(side_effect=sockets)
    monkeypatch.setattr("websockets.connect", connect)
    await client.connect(auth)
    await client.subscribe(channels, params)
    return connect


async def bounded(awaitable):
    return await asyncio.wait_for(awaitable, timeout=1)


@pytest.mark.parametrize("ending", ["eof", "oserror", "close_ok", "close_error"])
async def test_stream_end_backoff_reconnect_resubscribe(venue, monkeypatch, ending):
    name, client, auth, _, _, payload, _ = venue
    errors = {
        "eof": None,
        "oserror": OSError("offline disconnect"),
        "close_ok": ConnectionClosedOK(Close(1000, ""), Close(1000, ""), True),
        "close_error": ConnectionClosedError(Close(1011, ""), None, None),
    }
    first, second = Socket(error=errors[ending]), Socket(payload, idle=True)
    connect = await start_client(venue, monkeypatch, first, second)
    health = (
        client.health()
    )  # Hold the metrics object: no refresh may mask stale state.
    heartbeat = getattr(client, "_heartbeat_task", None)
    entered, release = asyncio.Event(), asyncio.Event()
    delays = []

    async def wait_backoff(backoff, closed):
        delays.append(backoff.next_delay())
        assert client._connected is False
        assert health.connected is False
        assert health.reconnect_count == 1
        if heartbeat is not None:
            assert heartbeat.done()
            assert client._heartbeat_task is None
        entered.set()
        await release.wait()

    module = importlib.import_module(f"predxt.{name}.client")
    monkeypatch.setattr(module, "_wait_for_backoff", wait_backoff, raising=False)
    stream = client.messages()
    reader = asyncio.create_task(anext(stream))
    try:
        await bounded(entered.wait())
        # Give other tasks turns; retry must remain suspended behind backoff.
        for _ in range(3):
            await asyncio.sleep(0)
        assert connect.await_count == 1
        assert first.iterations == 1
        assert not reader.done()
        release.set()
        message = await bounded(reader)
        assert len(delays) == 1 and delays[0] >= 1
        assert connect.await_count == 2
        assert second.iterations == 1
        assert first.send.await_count == second.send.await_count == 1
        sent_first = json.loads(first.send.call_args.args[0])
        sent_second = json.loads(second.send.call_args.args[0])
        if name == "kalshi":
            sent_first.pop("id")
            sent_second.pop("id")
        assert sent_first == sent_second
        assert health.connected is True and client._connected is True
        assert health.reconnect_count == 1
        assert health.messages_received == 1
        assert message.venue == name
        assert message.raw_data["price"] == "0.55"
        assert message.received_at_ms == message.timestamp_ms
        if name == "kalshi":
            assert message.raw_data["raw"] == payload
        if auth is not None:
            assert client._auth_params == auth
        if heartbeat is not None:
            assert client._heartbeat_task is not heartbeat
            assert not client._heartbeat_task.done()
    finally:
        reader.cancel()
        await asyncio.gather(reader, return_exceptions=True)
        await bounded(stream.aclose())
        await bounded(client.close())
    assert not health.connected
    assert connect.await_count == 2


@pytest.mark.parametrize("action", ["close", "cancel", "stop"])
@pytest.mark.parametrize("phase", ["idle", "backoff"])
async def test_shutdown_is_prompt_and_does_not_reconnect(
    venue, monkeypatch, phase, action
):
    name, client, auth, _, _, _, manager = venue
    socket = Socket(idle=phase == "idle")
    connect = AsyncMock(return_value=socket)
    monkeypatch.setattr("websockets.connect", connect)
    backoff_entered = asyncio.Event()

    def next_delay():
        backoff_entered.set()
        return 3600  # A real wait that must be interrupted, never slept through.

    monkeypatch.setattr(client._backoff, "next_delay", Mock(side_effect=next_delay))
    stream = None
    if action == "stop":
        if name == "polymarket":
            await manager.start()
        else:
            await manager.start(auth)
        reader = None
    else:
        await client.connect(auth)
        stream = client.messages()
        reader = asyncio.create_task(anext(stream))
    try:
        await bounded((socket.reading if phase == "idle" else backoff_entered).wait())
        if action == "stop":
            await bounded(manager.stop())
            await bounded(manager.stop())
        elif action == "close":
            await bounded(client.close())
            await bounded(client.close())
            with pytest.raises(StopAsyncIteration):
                await bounded(reader)
        else:
            reader.cancel()
            with pytest.raises(asyncio.CancelledError):
                await bounded(reader)
            await bounded(client.close())
            await bounded(client.close())
        assert not client._connected
        assert not client.health().connected
        assert client.health().reconnect_count == (1 if phase == "backoff" else 0)
        assert connect.await_count == 1
        assert socket.close.await_count == 1
        assert socket.iterations == 1
        assert getattr(client, "_heartbeat_task", None) is None
    finally:
        if reader is not None:
            reader.cancel()
            await asyncio.gather(reader, return_exceptions=True)
        if stream is not None:
            await stream.aclose()
        await client.close()


async def test_close_before_messages_and_explicit_restart(venue, monkeypatch):
    _, client, auth, _, _, payload, _ = venue
    socket = Socket(payload, idle=True)
    connect = AsyncMock(return_value=socket)
    monkeypatch.setattr("websockets.connect", connect)
    await bounded(client.close())
    await bounded(client.close())
    with pytest.raises(StopAsyncIteration):
        await bounded(anext(client.messages()))
    assert connect.await_count == 0
    await client.connect(auth)
    stream = client.messages()
    try:
        message = await bounded(anext(stream))
        assert message.raw_data["price"] == "0.55"
    finally:
        await stream.aclose()
    assert connect.await_count == 1
    assert not client.health().connected


async def test_close_during_connection_does_not_restore_health(venue, monkeypatch):
    _, client, auth, _, _, _, _ = venue
    entered, release = asyncio.Event(), asyncio.Event()
    socket = Socket()

    async def connect_socket(*args, **kwargs):
        entered.set()
        await release.wait()
        return socket

    connect = AsyncMock(side_effect=connect_socket)
    monkeypatch.setattr("websockets.connect", connect)
    task = asyncio.create_task(client.connect(auth))
    try:
        await bounded(entered.wait())
        await bounded(client.close())
        release.set()
        await bounded(task)
        assert not client.health().connected
        assert connect.await_count == socket.close.await_count == 1
        assert getattr(client, "_heartbeat_task", None) is None
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await client.close()
