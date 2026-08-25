from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Awaitable, Callable, Dict, Iterable, List, Optional, Set

from pydantic import BaseModel, Field, field_validator

from predxt.base import VenueMessage
from predxt.polymarket.client import PolymarketWsClient

logger = logging.getLogger(__name__)

MessageCallback = Callable[[VenueMessage], Awaitable[None]]


class SubscriptionConfig(BaseModel):
    assets_ids: Set[str] = Field(default_factory=set)
    initial_dump: bool = True
    custom_feature_enabled: Optional[bool] = None
    channels: List[str] = Field(default_factory=lambda: ["market"])

    @field_validator("channels")
    @classmethod
    def _channels_not_empty(cls, value: List[str]) -> List[str]:
        if not value:
            raise ValueError("channels must include at least one entry")
        return value

    @field_validator("assets_ids")
    @classmethod
    def _assets_not_empty(cls, value: Set[str]) -> Set[str]:
        if not value:
            raise ValueError("assets_ids must include at least one asset")
        return value

    def subscription_payload(self) -> Dict[str, object]:
        payload: Dict[str, object] = {
            "assets_ids": sorted(self.assets_ids),
            "initial_dump": self.initial_dump,
        }
        if self.custom_feature_enabled is not None:
            payload["custom_feature_enabled"] = self.custom_feature_enabled
        return payload


class WsConnectionManager:
    """High-level orchestration around a single Polymarket websocket session."""

    def __init__(
        self,
        client: Optional[PolymarketWsClient] = None,
        *,
        config: Optional[SubscriptionConfig] = None,
        initial_assets: Optional[Iterable[str]] = None,
        initial_dump: bool = True,
        custom_feature_enabled: Optional[bool] = None,
        channels: Optional[List[str]] = None,
    ) -> None:
        assets = set(initial_assets or [])
        if config:
            self._config = config.model_copy(deep=True)
        else:
            self._config = SubscriptionConfig(
                assets_ids=assets,
                initial_dump=initial_dump,
                custom_feature_enabled=custom_feature_enabled,
                channels=channels or ["market"],
            )

        self._client = client or PolymarketWsClient()
        self._global_callbacks: List[MessageCallback] = []
        self._asset_callbacks: Dict[str, List[MessageCallback]] = defaultdict(list)
        self._messages_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._dispatch_complete = asyncio.Event()
        self._dispatch_complete.set()
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    def add_asset(self, asset_id: str) -> None:
        self._config.assets_ids.add(asset_id)

    def remove_asset(self, asset_id: str) -> None:
        if asset_id in self._config.assets_ids:
            self._config.assets_ids.remove(asset_id)

    def on_message(
        self, callback: MessageCallback, *, asset_id: Optional[str] = None
    ) -> None:
        if asset_id:
            self._asset_callbacks[asset_id].append(callback)
        else:
            self._global_callbacks.append(callback)

    async def start(self) -> None:
        if self._messages_task and not self._messages_task.done():
            raise RuntimeError("WsConnectionManager already running")

        self._config = self._config.model_copy(deep=True)
        await self._client.connect()
        await self._client.subscribe(
            self._config.channels, self._config.subscription_payload()
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
                self._config.channels, self._config.subscription_payload()
            )

    def config(self) -> SubscriptionConfig:
        return self._config.model_copy(deep=True)

    # ------------------------------------------------------------------
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
            logger.exception("Error in WsConnectionManager message loop")
            raise

    async def _dispatch(self, msg: VenueMessage) -> None:
        callbacks = list(self._global_callbacks)
        asset_id = self._asset_id_from_message(msg)
        if asset_id:
            callbacks.extend(self._asset_callbacks.get(asset_id, []))

        if not callbacks:
            return

        await asyncio.gather(*(cb(msg) for cb in callbacks), return_exceptions=True)

    @staticmethod
    def _asset_id_from_message(msg: VenueMessage) -> Optional[str]:
        payload = msg.raw_data or {}
        return payload.get("asset_id")
