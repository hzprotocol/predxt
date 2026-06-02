from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable, Optional


@dataclass
class HealthMetrics:
    connected: bool
    last_message_timestamp_ms: Optional[float] = None
    reconnect_count: int = 0
    messages_received: int = 0
    messages_sent: int = 0
    last_error: Optional[str] = None
    last_error_timestamp_ms: Optional[float] = None
    uptime_seconds: float = 0.0


class VenueMessage:
    """Base class for venue-native messages."""

    venue: str
    raw_data: dict[str, Any]
    timestamp_ms: float


class BaseWsClient(ABC):
    @abstractmethod
    async def connect(self, auth_params: Optional[dict[str, Any]] = None) -> None:
        pass

    @abstractmethod
    async def subscribe(
        self, channels: list[str], params: Optional[dict[str, Any]] = None
    ) -> None:
        pass

    @abstractmethod
    async def unsubscribe(self, channels: list[str]) -> None:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass

    @abstractmethod
    async def messages(self) -> AsyncIterator[VenueMessage]:
        pass

    @abstractmethod
    def health(self) -> HealthMetrics:
        pass

    def on_message(self, callback: Callable[[VenueMessage], Any]):
        """Register a callback. Optional convenience; implementations may return a Subscription-like object."""
        raise NotImplementedError
