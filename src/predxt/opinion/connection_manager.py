from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Awaitable, Callable, Dict, Iterable, List, Optional, Set

from pydantic import BaseModel, Field, field_validator

from predxt.base import VenueMessage
from predxt.opinion.client import OpinionWsClient

logger = logging.getLogger(__name__)

MessageCallback = Callable[[VenueMessage], Awaitable[None]]


class OpinionSubscriptionConfig(BaseModel):
    market_ids: Set[str] = Field(default_factory=set)
    channels: List[str] = Field(default_factory=lambda: ["market.depth.diff"])

    @field_validator("channels")
    @classmethod
    def _channels_not_empty(cls, value: List[str]) -> List[str]:
        if not value:
            raise ValueError("channels must include at least one entry")
        return value

    def subscription_payload(self) -> Dict[str, object]:
        return {"market_ids": sorted(self.market_ids)}


class OpinionWsConnectionManager:
    def __init__(
        self,
        client: Optional[OpinionWsClient] = None,
        *,
        config: Optional[OpinionSubscriptionConfig] = None,
        initial_markets: Optional[Iterable[str]] = None,
        channels: Optional[List[str]] = None,
    ) -> None:
        market_ids = {
            str(item).strip() for item in (initial_markets or []) if str(item).strip()
        }
        if config:
            self._config = config.model_copy(deep=True)
        else:
            self._config = OpinionSubscriptionConfig(
                market_ids=market_ids,
                channels=channels or ["market.depth.diff"],
            )
        self._client = client or OpinionWsClient()
        self._global_callbacks: List[MessageCallback] = []
        self._market_callbacks: Dict[str, List[MessageCallback]] = defaultdict(list)
        self._messages_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._dispatch_complete = asyncio.Event()
        self._dispatch_complete.set()
        self._lock = asyncio.Lock()

    def add_market(self, market_id: str) -> None:
        self._config.market_ids.add(str(market_id))

    def remove_market(self, market_id: str) -> None:
        self._config.market_ids.discard(str(market_id))

    def on_message(
        self,
        callback: MessageCallback,
        *,
        market_id: Optional[str] = None,
    ) -> None:
        if market_id:
            self._market_callbacks[str(market_id)].append(callback)
        else:
            self._global_callbacks.append(callback)

    async def start(self, auth_params: Optional[dict] = None) -> None:
        if self._messages_task and not self._messages_task.done():
            raise RuntimeError("OpinionWsConnectionManager already running")
        await self._client.connect(auth_params=auth_params)
        await self._client.subscribe(
            self._config.channels,
            self._config.subscription_payload(),
        )
        self._stop_event.clear()
        self._messages_task = asyncio.create_task(self._message_loop())

    async def stop(self) -> None:
        self._stop_event.set()
        messages_task = self._messages_task
        if messages_task and not self._dispatch_complete.is_set():
            await self._dispatch_complete.wait()
        if messages_task and not messages_task.done():
            messages_task.cancel()
        if messages_task:
            await asyncio.gather(messages_task, return_exceptions=True)
        if self._messages_task is messages_task:
            self._messages_task = None
        await self._client.close()

    async def refresh_subscription(self) -> None:
        async with self._lock:
            await self._client.subscribe(
                self._config.channels,
                self._config.subscription_payload(),
            )

    def config(self) -> OpinionSubscriptionConfig:
        return self._config.model_copy(deep=True)

    async def _message_loop(self) -> None:
        try:
            async for msg in self._client.messages():
                self._dispatch_complete.clear()
                try:
                    await self._dispatch(msg)
                finally:
                    self._dispatch_complete.set()
                if self._stop_event.is_set():
                    break
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Error in OpinionWsConnectionManager message loop")
            raise

    async def _dispatch(self, msg: VenueMessage) -> None:
        callbacks = list(self._global_callbacks)
        market_id = self._market_id_from_message(msg)
        if market_id:
            callbacks.extend(self._market_callbacks.get(market_id, []))
        if callbacks:
            await asyncio.gather(*(cb(msg) for cb in callbacks), return_exceptions=True)

    @staticmethod
    def _market_id_from_message(msg: VenueMessage) -> Optional[str]:
        payload = msg.raw_data or {}
        value = payload.get("market_id") or payload.get("marketId")
        return str(value).strip() if value is not None else None
