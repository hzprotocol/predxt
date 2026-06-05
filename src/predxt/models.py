from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypeAlias

from predxt.events import BookLevel, OrderBookSnapshot

OrderBookLevel: TypeAlias = BookLevel


@dataclass(frozen=True)
class MarketSummary:
    """Normalized read-only market row from a venue REST API."""

    venue: str
    market_id: str
    title: str | None = None
    subtitle: str | None = None
    category: str | None = None
    status: str | None = None
    close_time: str | None = None
    outcomes: list[str] = field(default_factory=list)
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MarketDetail:
    """Normalized read-only market detail from a venue REST API."""

    venue: str
    market_id: str
    title: str | None = None
    subtitle: str | None = None
    category: str | None = None
    status: str | None = None
    close_time: str | None = None
    description: str | None = None
    event_id: str | None = None
    outcomes: list[str] = field(default_factory=list)
    token_ids: list[str] = field(default_factory=list)
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VenueCredentialStatus:
    """Result of a read-only credential or API availability check."""

    venue: str
    ok: bool
    message: str
    status_code: int | None = None


class VenueApiError(RuntimeError):
    """Sanitized venue REST API error.

    Secret headers and request bodies are never included in this error.
    """

    def __init__(
        self,
        *,
        venue: str,
        message: str,
        status_code: int | None = None,
        endpoint: str | None = None,
        payload: dict[str, Any] | list[Any] | str | None = None,
    ) -> None:
        self.venue = venue
        self.status_code = status_code
        self.endpoint = endpoint
        self.payload = payload
        parts = [venue, message]
        if status_code is not None:
            parts.append(f"status={status_code}")
        if endpoint:
            parts.append(f"endpoint={endpoint}")
        super().__init__(" ".join(parts))


__all__ = [
    "MarketDetail",
    "MarketSummary",
    "OrderBookLevel",
    "OrderBookSnapshot",
    "VenueApiError",
    "VenueCredentialStatus",
]
