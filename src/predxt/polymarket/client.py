from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, AsyncIterator, Iterable, Optional

import websockets

from predxt.base import BaseWsClient, HealthMetrics, VenueMessage
from predxt.utils.backoff import ExponentialBackoff

from .parser import parse_message

logger = logging.getLogger(__name__)


class PolymarketWsClient(BaseWsClient):
    WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    MAX_RECONNECT_ATTEMPTS = 10

    def __init__(self, max_reconnect_attempts: int = MAX_RECONNECT_ATTEMPTS):
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._connected = False
        self._backoff = ExponentialBackoff(base_seconds=1, max_seconds=60)
        self._health = HealthMetrics(connected=False)
        self._channels: list[str] = []
        self._params: dict[str, Any] = {}
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = max_reconnect_attempts
        self._connect_time: Optional[float] = None

    async def connect(self, auth_params: Optional[dict[str, Any]] = None) -> None:
        """Connect to Polymarket WS and update health metrics.

        Sets _connect_time, clears last_error on success and records last_error on failure.
        """
        if auth_params:
            logger.warning("Polymarket WS is public; auth_params ignored")

        while self._reconnect_attempts < self._max_reconnect_attempts:
            try:
                self._ws = await websockets.connect(self.WS_URL)
                self._connected = True
                # set connection timestamp used by health().
                self._connect_time = time.time()
                self._backoff.reset()
                self._reconnect_attempts = 0
                self._health.connected = True
                # clear any previously recorded error
                self._health.last_error = None
                self._health.last_error_timestamp_ms = None
                logger.info("Connected to Polymarket WS")
                return
            except Exception as e:
                self._reconnect_attempts += 1
                delay = self._backoff.next_delay()
                # record failure details for observability
                self._health.last_error = str(e)
                self._health.last_error_timestamp_ms = time.time() * 1000
                logger.warning(f"Connection failed, retry in {delay}s: {e}")
                await asyncio.sleep(delay)

        raise ConnectionError(
            f"Failed to connect after {self._max_reconnect_attempts} attempts"
        )

    async def subscribe(
        self, channels: list[str], params: Optional[dict[str, Any]] = None
    ) -> None:
        """Subscribe to Polymarket market feed.

        Supports params keys:
        - assets_ids: list[str] (filter by asset IDs)
        - initial_dump: bool (request full snapshot)
        - custom_feature_enabled: bool (experimental flag forwarded to server)
        """
        if not self._connected or not self._ws:
            raise RuntimeError("Not connected")

        self._channels = channels
        self._params = params or {}

        # Build subscription payload following Polymarket ws contract
        payload: dict[str, Any] = {"type": "market"}

        # Only include known parameters to avoid sending unexpected keys
        if "assets_ids" in self._params:
            payload["assets_ids"] = (
                list(self._params["assets_ids"])
                if self._params["assets_ids"] is not None
                else []
            )
        if "initial_dump" in self._params:
            payload["initial_dump"] = bool(self._params["initial_dump"])
        if "custom_feature_enabled" in self._params:
            payload["custom_feature_enabled"] = bool(
                self._params["custom_feature_enabled"]
            )

        # The server expects the channels array for subscription context
        if channels:
            payload["channels"] = channels

        await self._ws.send(json.dumps(payload))
        logger.info(f"Subscribed to {channels} with params={self._params}")

    async def unsubscribe(self, channels: list[str]) -> None:
        # Polymarket doesn't support per-channel unsubscribe; close and reconnect
        if self._ws:
            await self._ws.close()
            self._connected = False

    async def close(self) -> None:
        if self._ws:
            await self._ws.close()
            self._connected = False
            self._health.connected = False
            logger.info("Closed Polymarket WS")

    async def messages(self) -> AsyncIterator[VenueMessage]:
        """Stream parsed Polymarket messages with deduplication and health updates.

        Emits dicts returned by parse_message() wrapped into VenueMessage-like objects.
        """
        seen_hashes: set[str] = set()

        while True:
            try:
                if not self._connected:
                    await self.connect()
                    if self._channels:
                        await self.subscribe(self._channels, self._params)

                # websockets client returns an async iterator; support AsyncMock whose __aiter__ may be an async generator
                # Prefer iterating directly over the websocket object when possible.
                try:
                    # Prefer standard async iteration
                    async for raw_msg in self._ws:
                        async for vm in self._handle_raw_message(
                            raw_msg, seen_hashes=seen_hashes
                        ):
                            yield vm
                except TypeError:
                    # The websocket mock may expose __aiter__ as an async generator object
                    # that isn't directly iterable; attempt to call it and iterate the result.
                    try:
                        aiter_obj = self._ws.__aiter__()
                        # If __aiter__() returned a coroutine that yields an async generator, await it
                        if asyncio.iscoroutine(aiter_obj):
                            aiter_obj = await aiter_obj

                        async for raw_msg in aiter_obj:
                            async for vm in self._handle_raw_message(
                                raw_msg, seen_hashes=seen_hashes
                            ):
                                yield vm
                    except Exception as e:
                        logger.error(f"Failed iterating websocket mock: {e}")
                    # end of mock iterator handling
                except TypeError:
                    # Some test mocks provide __aiter__ as an async generator; support that case
                    if hasattr(self._ws, "__aiter__"):
                        async for raw_msg in self._ws.__aiter__():
                            async for vm in self._handle_raw_message(
                                raw_msg, seen_hashes=seen_hashes
                            ):
                                yield vm

            except (websockets.exceptions.ConnectionClosed, OSError) as e:
                self._connected = False
                self._health.connected = False
                self._health.reconnect_count += 1
                logger.warning(f"Connection lost: {e}, reconnecting...")
                await asyncio.sleep(self._backoff.next_delay())

                # On reconnect, preserve seen_hashes for a short time but don't let it grow unbounded
                if len(seen_hashes) > 10000:
                    seen_hashes.clear()

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise

    def health(self) -> HealthMetrics:
        self._health.connected = self._connected
        self._health.uptime_seconds = (
            time.time() - self._connect_time if self._connect_time else 0
        )
        return self._health

    async def _handle_raw_message(
        self, raw_msg: str, *, seen_hashes: set[str]
    ) -> AsyncIterator[VenueMessage]:
        try:
            if isinstance(raw_msg, (bytes, bytearray)):
                raw_msg = raw_msg.decode("utf-8", errors="ignore")
            if isinstance(raw_msg, str):
                raw_msg = raw_msg.strip()
                if not raw_msg or raw_msg.lower() in {"ping", "pong"}:
                    return
                if raw_msg[0] not in "{[":
                    logger.debug("Ignoring non-JSON Polymarket WS message: %r", raw_msg)
                    return
            data = json.loads(raw_msg)
            messages = data if isinstance(data, list) else [data]
            for decoded in messages:
                for parsed in self._iter_parsed_messages(decoded):
                    h = parsed.get("hash")
                    if h:
                        if h in seen_hashes:
                            logger.debug("Duplicate message skipped (hash)")
                            continue
                        seen_hashes.add(h)

                    vm = VenueMessage()
                    vm.venue = "polymarket"
                    vm.raw_data = parsed
                    vm.timestamp_ms = time.time() * 1000

                    self._health.messages_received += 1
                    self._health.last_message_timestamp_ms = vm.timestamp_ms
                    yield vm
        except Exception as e:
            logger.error(f"Failed to parse or handle message: {e}")

    @staticmethod
    def _iter_parsed_messages(decoded: Any) -> Iterable[dict[str, Any]]:
        parsed = parse_message(decoded)
        if not parsed:
            return []
        if isinstance(parsed, list):
            return parsed
        return [parsed]
