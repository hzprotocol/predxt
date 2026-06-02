from __future__ import annotations

from dataclasses import dataclass, field

from predxt.base import VenueMessage
from predxt.events import (
    BookLevel,
    OrderBookDelta,
    OrderBookSnapshot,
    TypedEvent,
    typed_event_from_message,
)


@dataclass
class OrderBookState:
    """In-memory best-effort orderbook for normalized snapshot/delta events."""

    bids: dict[float, float] = field(default_factory=dict)
    asks: dict[float, float] = field(default_factory=dict)
    last_event: TypedEvent | None = None

    def apply(self, event: TypedEvent | VenueMessage) -> None:
        typed_event = (
            typed_event_from_message(event) if isinstance(event, VenueMessage) else event
        )
        if typed_event is None:
            return
        self.last_event = typed_event
        if isinstance(typed_event, OrderBookSnapshot):
            self.bids = _levels_to_map(typed_event.bids)
            self.asks = _levels_to_map(typed_event.asks)
            return
        if isinstance(typed_event, OrderBookDelta):
            self._apply_delta(typed_event)

    @property
    def best_bid(self) -> float | None:
        return max(self.bids) if self.bids else None

    @property
    def best_ask(self) -> float | None:
        return min(self.asks) if self.asks else None

    def best_bid_size(self) -> float | None:
        price = self.best_bid
        return self.bids.get(price) if price is not None else None

    def best_ask_size(self) -> float | None:
        price = self.best_ask
        return self.asks.get(price) if price is not None else None

    def snapshot(self, *, depth: int | None = None) -> dict[str, list[dict[str, float]]]:
        bids = sorted(self.bids.items(), reverse=True)
        asks = sorted(self.asks.items())
        if depth is not None:
            bids = bids[:depth]
            asks = asks[:depth]
        return {
            "bids": [{"price": price, "size": size} for price, size in bids],
            "asks": [{"price": price, "size": size} for price, size in asks],
        }

    def _apply_delta(self, event: OrderBookDelta) -> None:
        if event.price is None or event.size is None:
            return
        book = self.bids if event.side == "bid" else self.asks
        if event.size <= 0:
            book.pop(event.price, None)
        else:
            book[event.price] = event.size


def _levels_to_map(levels: list[BookLevel]) -> dict[float, float]:
    return {level.price: level.size for level in levels if level.size > 0}
