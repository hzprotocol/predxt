from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypeAlias

from predxt.base import VenueMessage


@dataclass(frozen=True)
class BookLevel:
    price: float
    size: float


@dataclass(frozen=True)
class BaseEvent:
    venue: str
    event_type: str
    timestamp_ms: float
    market_id: str | None = None
    asset_id: str | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OrderBookSnapshot(BaseEvent):
    bids: list[BookLevel] = field(default_factory=list)
    asks: list[BookLevel] = field(default_factory=list)


@dataclass(frozen=True)
class OrderBookDelta(BaseEvent):
    side: str = ""
    price: float | None = None
    size: float | None = None


@dataclass(frozen=True)
class TradeEvent(BaseEvent):
    side: str | None = None
    price: float | None = None
    size: float | None = None


@dataclass(frozen=True)
class PriceChangeEvent(BaseEvent):
    side: str | None = None
    price: float | None = None
    size: float | None = None
    best_bid: float | None = None
    best_ask: float | None = None


TypedEvent: TypeAlias = (
    OrderBookSnapshot | OrderBookDelta | TradeEvent | PriceChangeEvent
)


def typed_event_from_message(message: VenueMessage) -> TypedEvent | None:
    """Convert a VenueMessage into a typed event when its shape is supported."""

    payload = message.raw_data or {}
    event_type = str(payload.get("type") or message.event_type or "").strip()

    if event_type in {"book", "orderbook_snapshot"}:
        return OrderBookSnapshot(
            venue=message.venue,
            event_type=event_type,
            timestamp_ms=message.timestamp_ms,
            market_id=message.market_id,
            asset_id=message.asset_id,
            raw_data=payload,
            bids=_parse_levels(payload.get("bids", [])),
            asks=_parse_levels(payload.get("asks", [])),
        )

    if event_type in {"orderbook_delta", "depth_diff"}:
        return OrderBookDelta(
            venue=message.venue,
            event_type=event_type,
            timestamp_ms=message.timestamp_ms,
            market_id=message.market_id,
            asset_id=message.asset_id,
            raw_data=payload,
            side=_normalize_side(payload.get("side")),
            price=_as_float(payload.get("price")),
            size=_as_float(payload.get("size")),
        )

    if event_type in {"trade", "last_trade", "last_trade_price"}:
        return TradeEvent(
            venue=message.venue,
            event_type=event_type,
            timestamp_ms=message.timestamp_ms,
            market_id=message.market_id,
            asset_id=message.asset_id,
            raw_data=payload,
            side=_as_optional_str(payload.get("side")),
            price=_as_float(payload.get("price")),
            size=_as_float(payload.get("size") or payload.get("shares")),
        )

    if event_type == "price_change":
        return PriceChangeEvent(
            venue=message.venue,
            event_type=event_type,
            timestamp_ms=message.timestamp_ms,
            market_id=message.market_id,
            asset_id=message.asset_id,
            raw_data=payload,
            side=_as_optional_str(payload.get("side")),
            price=_as_float(payload.get("price")),
            size=_as_float(payload.get("size")),
            best_bid=_as_float(payload.get("best_bid")),
            best_ask=_as_float(payload.get("best_ask")),
        )

    return None


def _parse_levels(levels: Any) -> list[BookLevel]:
    parsed: list[BookLevel] = []
    if not isinstance(levels, list):
        return parsed
    for level in levels:
        price: Any
        size: Any
        if isinstance(level, dict):
            price = level.get("price")
            size = level.get("size")
        elif isinstance(level, (list, tuple)) and len(level) >= 2:
            price, size = level[0], level[1]
        else:
            continue
        parsed_price = _as_float(price)
        parsed_size = _as_float(size)
        if parsed_price is not None and parsed_size is not None:
            parsed.append(BookLevel(price=parsed_price, size=parsed_size))
    return parsed


def _normalize_side(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"bid", "bids", "buy", "yes"}:
        return "bid"
    if text in {"ask", "asks", "sell", "no"}:
        return "ask"
    return text


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
