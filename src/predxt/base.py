from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
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


@dataclass
class VenueMessage:
    """Normalized wrapper around a parsed venue websocket payload."""

    venue: str = ""
    raw_data: dict[str, Any] = field(default_factory=dict)
    timestamp_ms: float = 0.0
    event_type: str | None = None
    market_id: str | None = None
    asset_id: str | None = None
    received_at_ms: float | None = None


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
    def messages(self) -> AsyncIterator[VenueMessage]:
        pass

    @abstractmethod
    def health(self) -> HealthMetrics:
        pass

    def on_message(self, callback: Callable[[VenueMessage], Any]) -> Any:
        """Register a callback when an implementation provides callback mode."""
        raise NotImplementedError


def build_venue_message(
    *,
    venue: str,
    raw_data: dict[str, Any],
    timestamp_ms: float,
) -> VenueMessage:
    """Build a VenueMessage with common metadata extracted from raw_data."""

    event_type = _as_optional_str(
        raw_data.get("type") or raw_data.get("event_type") or raw_data.get("msgType")
    )
    market_id = _as_optional_str(
        raw_data.get("market_id")
        or raw_data.get("marketId")
        or raw_data.get("market_ticker")
        or raw_data.get("market")
    )
    asset_id = _as_optional_str(raw_data.get("asset_id") or raw_data.get("token_id"))
    return VenueMessage(
        venue=venue,
        raw_data=raw_data,
        timestamp_ms=timestamp_ms,
        event_type=event_type,
        market_id=market_id,
        asset_id=asset_id,
        received_at_ms=timestamp_ms,
    )


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
