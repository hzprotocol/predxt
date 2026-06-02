from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from urllib.parse import urlparse
from typing import Any, AsyncIterator, Optional

import websockets

from predxt.base import BaseWsClient, HealthMetrics, VenueMessage
from predxt.kalshi.auth import build_kalshi_auth_headers
from predxt.kalshi.parser import parse_message
from predxt.utils.backoff import ExponentialBackoff

logger = logging.getLogger(__name__)


class KalshiWsClient(BaseWsClient):
    WS_URL = "wss://api.elections.kalshi.com/trade-api/ws/v2"

    def __init__(
        self,
        *,
        ws_url: str = WS_URL,
        max_reconnect_attempts: int = 10,
    ) -> None:
        self._ws_url = ws_url
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._connected = False
        self._connect_time: Optional[float] = None
        self._channels: list[str] = []
        self._params: dict[str, Any] = {}
        self._auth_params: dict[str, Any] = {}
        self._health = HealthMetrics(connected=False)
        self._backoff = ExponentialBackoff(base_seconds=1, max_seconds=60)
        self._max_reconnect_attempts = max_reconnect_attempts

    async def connect(self, auth_params: Optional[dict[str, Any]] = None) -> None:
        if auth_params is not None:
            self._auth_params = auth_params
        ws_path = urlparse(self._ws_url).path or "/trade-api/ws/v2"
        headers = self._build_auth_headers(self._auth_params, ws_path=ws_path)
        attempts = 0

        while attempts < self._max_reconnect_attempts:
            try:
                self._ws = await websockets.connect(
                    self._ws_url, additional_headers=headers
                )
                self._connected = True
                self._connect_time = time.time()
                self._backoff.reset()
                self._health.connected = True
                self._health.last_error = None
                self._health.last_error_timestamp_ms = None
                return
            except Exception as exc:  # pragma: no cover - network failures in prod path
                attempts += 1
                self._health.last_error = str(exc)
                self._health.last_error_timestamp_ms = time.time() * 1000
                await asyncio.sleep(self._backoff.next_delay())

        raise ConnectionError(
            f"Failed to connect to Kalshi after {self._max_reconnect_attempts} attempts"
        )

    async def subscribe(
        self, channels: list[str], params: Optional[dict[str, Any]] = None
    ) -> None:
        if not self._connected or not self._ws:
            raise RuntimeError("Not connected")

        self._channels = channels
        self._params = params or {}

        payload = {
            "id": int(time.time() * 1000),
            "cmd": "subscribe",
            "params": {
                "channels": channels,
                "market_tickers": list(self._params.get("market_tickers", [])),
            },
        }
        await self._ws.send(json.dumps(payload))
        self._health.messages_sent += 1

    async def unsubscribe(self, channels: list[str]) -> None:
        if not self._connected or not self._ws:
            return
        payload = {
            "id": int(time.time() * 1000),
            "cmd": "unsubscribe",
            "params": {"channels": channels},
        }
        await self._ws.send(json.dumps(payload))
        self._health.messages_sent += 1

    async def close(self) -> None:
        if self._ws:
            await self._ws.close()
        self._connected = False
        self._health.connected = False

    async def messages(self) -> AsyncIterator[VenueMessage]:
        seen_hashes: set[str] = set()

        while True:
            try:
                if not self._connected:
                    await self.connect(self._auth_params)
                    if self._channels:
                        await self.subscribe(self._channels, self._params)

                async for raw_msg in self._ws:  # type: ignore[misc]
                    payload = json.loads(raw_msg)
                    parsed = parse_message(payload)
                    if not parsed:
                        continue

                    dedupe_hash = parsed.get("hash")
                    if not dedupe_hash:
                        dedupe_hash = hashlib.sha1(
                            json.dumps(parsed, sort_keys=True).encode("utf-8")
                        ).hexdigest()

                    if dedupe_hash in seen_hashes:
                        continue
                    seen_hashes.add(dedupe_hash)

                    vm = VenueMessage()
                    vm.venue = "kalshi"
                    vm.raw_data = parsed
                    vm.timestamp_ms = time.time() * 1000

                    self._health.messages_received += 1
                    self._health.last_message_timestamp_ms = vm.timestamp_ms
                    yield vm

            except (websockets.exceptions.ConnectionClosed, OSError):
                self._connected = False
                self._health.connected = False
                self._health.reconnect_count += 1
                await asyncio.sleep(self._backoff.next_delay())
            except Exception:
                logger.exception("Unexpected Kalshi websocket error")
                raise

            if len(seen_hashes) > 10000:
                seen_hashes.clear()

    def health(self) -> HealthMetrics:
        self._health.connected = self._connected
        self._health.uptime_seconds = (
            time.time() - self._connect_time if self._connect_time else 0
        )
        return self._health

    @staticmethod
    def _build_auth_headers(
        auth_params: dict[str, Any], *, ws_path: str = "/trade-api/ws/v2"
    ) -> dict[str, str]:
        return build_kalshi_auth_headers(auth_params, ws_path=ws_path)
