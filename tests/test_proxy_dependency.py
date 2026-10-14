"""Missing SOCKS support is a setup error, not a transient network outage."""

import asyncio
import importlib
import subprocess
import sys
import textwrap
from unittest.mock import AsyncMock, Mock

import pytest
import websockets

from predxt import SocksDependencyError
from predxt.cli import main
from predxt.kalshi import KalshiWsClient
from predxt.opinion import OpinionWsClient
from predxt.polymarket import PolymarketWsClient


MISSING_SOCKS = "connecting through a SOCKS proxy requires python-socks"


@pytest.fixture(params=["polymarket", "kalshi", "opinion"])
def client(request, monkeypatch):
    if request.param == "polymarket":
        instance = PolymarketWsClient()
    elif request.param == "kalshi":
        instance = KalshiWsClient()
        monkeypatch.setattr(instance, "_build_auth_headers", lambda *a, **kw: {})
    else:
        instance = OpinionWsClient()
        monkeypatch.setattr(instance, "_resolve_api_key", lambda: "offline-test-only")
    return instance


@pytest.mark.parametrize("entrypoint", ["connect", "messages"])
async def test_missing_socks_stops_before_backoff(client, monkeypatch, entrypoint):
    original = ImportError(MISSING_SOCKS)
    connect = AsyncMock(side_effect=original)
    monkeypatch.setattr("websockets.connect", connect)
    next_delay = Mock(side_effect=AssertionError("setup errors must not retry"))
    monkeypatch.setattr(client._backoff, "next_delay", next_delay)
    stream = client.messages() if entrypoint == "messages" else None
    try:
        with pytest.raises(SocksDependencyError) as caught:
            await asyncio.wait_for(
                anext(stream) if stream is not None else client.connect(), timeout=1
            )
        assert caught.value.__cause__ is original
        assert 'python -m pip install "python-socks[asyncio]"' in str(caught.value)
        assert "restart" in str(caught.value).lower()
        connect.assert_awaited_once()
        next_delay.assert_not_called()
        health = client.health()
        assert health.connected is False
        assert health.reconnect_count == 0
        assert health.last_error == str(caught.value)
        assert health.last_error_timestamp_ms is not None
        assert getattr(client, "_heartbeat_task", None) is None
    finally:
        if stream is not None:
            await stream.aclose()
        await client.close()


@pytest.mark.parametrize(
    "error",
    [
        OSError("offline network failure"),
        ImportError("unrelated optional dependency"),
        OSError(MISSING_SOCKS),  # Text alone must not classify a transport error.
    ],
)
async def test_other_errors_still_retry_and_recover(client, monkeypatch, error):
    socket = AsyncMock()
    connect = AsyncMock(side_effect=[error, socket])
    monkeypatch.setattr("websockets.connect", connect)
    module = importlib.import_module(type(client).__module__)
    wait = AsyncMock()
    monkeypatch.setattr(module, "_wait_for_backoff", wait)
    try:
        await asyncio.wait_for(client.connect(), timeout=1)
        assert connect.await_count == 2
        wait.assert_awaited_once()
        assert client.health().connected is True
        assert client.health().last_error is None
        assert client.health().last_error_timestamp_ms is None
    finally:
        await client.close()


def test_stream_cli_reports_missing_socks_on_stderr(monkeypatch, capsys):
    connect = AsyncMock(side_effect=ImportError(MISSING_SOCKS))
    monkeypatch.setattr("websockets.connect", connect)

    assert main(["stream", "polymarket", "--asset-id", "test-asset", "--jsonl"]) == 1

    output = capsys.readouterr()
    assert output.out == ""
    assert 'python -m pip install "python-socks[asyncio]"' in output.err
    assert "Traceback" not in output.err
    assert "retry" not in output.err.lower()
    connect.assert_awaited_once()


@pytest.mark.skipif(
    int(websockets.__version__.split(".")[0]) < 15,
    reason="automatic SOCKS proxy selection requires websockets 15+",
)
def test_real_websockets_missing_dependency_is_reported_before_network():
    # A fresh interpreter makes the absence deterministic even if the developer
    # installed python-socks. Exercise the real upstream diagnostic, not a mock
    # of websockets.connect, and prohibit network connection attempts.
    script = textwrap.dedent(
        '''
        import asyncio
        import importlib.abc
        import sys
        from unittest.mock import Mock

        class NoSocks(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname == "python_socks" or fullname.startswith("python_socks."):
                    raise ModuleNotFoundError("offline missing dependency", name=fullname)

        sys.meta_path.insert(0, NoSocks())
        import websockets.asyncio.client as transport
        from predxt.cli import main

        transport.get_proxy = lambda uri: "socks5h://127.0.0.1:9"
        network = Mock(side_effect=AssertionError("network must not be reached"))
        asyncio.BaseEventLoop.create_connection = network
        code = main(["stream", "polymarket", "--asset-id", "test-asset", "--jsonl"])
        network.assert_not_called()
        raise SystemExit(code)
        '''
    )
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, timeout=5
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert 'python -m pip install "python-socks[asyncio]"' in result.stderr
    assert "Traceback" not in result.stderr
    assert "retry" not in result.stderr.lower()
