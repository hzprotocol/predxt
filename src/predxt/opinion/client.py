from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, AsyncIterator, Iterable, Optional
from urllib.parse import urlencode

import websockets

from predxt.base import (
    BaseWsClient,
    HealthMetrics,
    VenueMessage,
    build_venue_message,
)
from predxt.opinion.parser import parse_message
from predxt.utils.backoff import ExponentialBackoff

logger = logging.getLogger(__name__)


class OpinionWsClient(BaseWsClient):
    WS_URL = "wss://ws.opinion.trade"

    def __init__(
        self,
        *,
        ws_url: str = WS_URL,
        api_key: str | None = None,
        heartbeat_seconds: float = 30.0,
        max_reconnect_attempts: int = 10,
    ) -> None:
        self._ws_url = ws_url
        self._api_key = api_key
        self._heartbeat_seconds = heartbeat_seconds
        self._max_reconnect_attempts = max_reconnect_attempts
        self._ws: Any | None = None
        self._connected = False
        self._connect_time: Optional[float] = None
        self._channels: list[str] = []
        self._params: dict[str, Any] = {}
        self._auth_params: dict[str, Any] = {}
        self._health = HealthMetrics(connected=False)
        self._backoff = ExponentialBackoff(base_seconds=1, max_seconds=60)
        self._heartbeat_task: asyncio.Task | None = None

    async def connect(self, auth_params: Optional[dict[str, Any]] = None) -> None:
        if auth_params is not None:
            self._auth_params = auth_params
        api_key = self._resolve_api_key()
        if not api_key:
            raise ValueError("Opinion websocket requires an API key")

        attempts = 0
        while attempts < self._max_reconnect_attempts:
            try:
                self._ws = await websockets.connect(self._authenticated_url(api_key))
                self._connected = True
                self._connect_time = time.time()
                self._backoff.reset()
                self._health.connected = True
                self._health.last_error = None
                self._health.last_error_timestamp_ms = None
                self._start_heartbeat()
                return
            except Exception as exc:  # pragma: no cover - network failures in prod path
                attempts += 1
                self._health.last_error = str(exc)
                self._health.last_error_timestamp_ms = time.time() * 1000
                await asyncio.sleep(self._backoff.next_delay())

        raise ConnectionError(
            f"Failed to connect to Opinion after {self._max_reconnect_attempts} attempts"
        )

    async def subscribe(
        self, channels: list[str], params: Optional[dict[str, Any]] = None
    ) -> None:
        if not self._connected or not self._ws:
            raise RuntimeError("Not connected")
        self._channels = channels
        self._params = params or {}
        for payload in self._subscription_payloads("SUBSCRIBE", channels, self._params):
            await self._ws.send(json.dumps(payload))
            self._health.messages_sent += 1

    async def unsubscribe(self, channels: list[str]) -> None:
        if not self._connected or not self._ws:
            return
        for payload in self._subscription_payloads(
            "UNSUBSCRIBE", channels, self._params
        ):
            await self._ws.send(json.dumps(payload))
            self._health.messages_sent += 1

    async def close(self) -> None:
        await self._stop_heartbeat()
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

                if self._ws is None:
                    continue
                async for raw_msg in self._ws:
                    async for vm in self._handle_raw_message(
                        raw_msg,
                        seen_hashes=seen_hashes,
                    ):
                        yield vm
            except (websockets.exceptions.ConnectionClosed, OSError):
                self._connected = False
                self._health.connected = False
                self._health.reconnect_count += 1
                await self._stop_heartbeat()
                await asyncio.sleep(self._backoff.next_delay())
            except Exception:
                logger.exception("Unexpected Opinion websocket error")
                raise

            if len(seen_hashes) > 10000:
                seen_hashes.clear()

    def health(self) -> HealthMetrics:
        self._health.connected = self._connected
        self._health.uptime_seconds = (
            time.time() - self._connect_time if self._connect_time else 0
        )
        return self._health

    async def _handle_raw_message(
        self,
        raw_msg: str | bytes,
        *,
        seen_hashes: set[str],
    ) -> AsyncIterator[VenueMessage]:
        try:
            if isinstance(raw_msg, (bytes, bytearray)):
                raw_msg = raw_msg.decode("utf-8", errors="ignore")
            raw_msg = str(raw_msg).strip()
            if not raw_msg or raw_msg.lower() in {"ping", "pong"}:
                return
            if raw_msg[0] not in "{[":
                return
            data = json.loads(raw_msg)
            messages = data if isinstance(data, list) else [data]
            for decoded in messages:
                for parsed in self._iter_parsed_messages(decoded):
                    dedupe_hash = parsed.get("hash")
                    if dedupe_hash:
                        if dedupe_hash in seen_hashes:
                            continue
                        seen_hashes.add(dedupe_hash)

                    vm = build_venue_message(
                        venue="opinion",
                        raw_data=parsed,
                        timestamp_ms=time.time() * 1000,
                    )
                    self._health.messages_received += 1
                    self._health.last_message_timestamp_ms = vm.timestamp_ms
                    yield vm
        except Exception as exc:
            logger.warning("Failed to parse Opinion WS message: %s", exc)

    @staticmethod
    def _iter_parsed_messages(decoded: Any) -> Iterable[dict[str, Any]]:
        if not isinstance(decoded, dict):
            return []
        parsed = parse_message(decoded)
        if not parsed:
            return []
        if isinstance(parsed, list):
            return parsed
        return [parsed]

    def _resolve_api_key(self) -> str:
        return str(
            self._auth_params.get("api_key")
            or self._auth_params.get("apikey")
            or self._api_key
            or ""
        ).strip()

    def _authenticated_url(self, api_key: str) -> str:
        separator = "&" if "?" in self._ws_url else "?"
        return f"{self._ws_url}{separator}{urlencode({'apikey': api_key})}"

    def _start_heartbeat(self) -> None:
        if self._heartbeat_task and not self._heartbeat_task.done():
            return
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _stop_heartbeat(self) -> None:
        task = self._heartbeat_task
        self._heartbeat_task = None
        if task and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def _heartbeat_loop(self) -> None:
        try:
            while self._connected and self._ws:
                await asyncio.sleep(self._heartbeat_seconds)
                if not self._connected or not self._ws:
                    return
                await self._ws.send(json.dumps({"action": "HEARTBEAT"}))
                self._health.messages_sent += 1
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._health.last_error = str(exc)
            self._health.last_error_timestamp_ms = time.time() * 1000

    @staticmethod
    def _subscription_payloads(
        action: str,
        channels: list[str],
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        market_ids = [
            str(item).strip()
            for item in params.get("market_ids", [])
            if str(item).strip()
        ]
        root_market_ids = [
            str(item).strip()
            for item in params.get("root_market_ids", [])
            if str(item).strip()
        ]
        payloads: list[dict[str, Any]] = []
        for channel in channels:
            for market_id in market_ids:
                payloads.append(
                    {
                        "action": action,
                        "channel": channel,
                        "marketId": int(market_id)
                        if market_id.isdigit()
                        else market_id,
                    }
                )
            for root_market_id in root_market_ids:
                payloads.append(
                    {
                        "action": action,
                        "channel": channel,
                        "rootMarketId": (
                            int(root_market_id)
                            if root_market_id.isdigit()
                            else root_market_id
                        ),
                    }
                )
        return payloads
