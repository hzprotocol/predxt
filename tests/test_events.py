from predxt.base import build_venue_message
from predxt.events import (
    OrderBookDelta,
    OrderBookSnapshot,
    PriceChangeEvent,
    typed_event_from_message,
)


def test_typed_event_from_polymarket_book():
    message = build_venue_message(
        venue="polymarket",
        raw_data={
            "type": "book",
            "asset_id": "asset-1",
            "bids": [{"price": "0.41", "size": "10"}],
            "asks": [{"price": "0.43", "size": "12"}],
        },
        timestamp_ms=1000,
    )

    event = typed_event_from_message(message)

    assert isinstance(event, OrderBookSnapshot)
    assert event.asset_id == "asset-1"
    assert event.bids[0].price == 0.41
    assert event.asks[0].size == 12


def test_typed_event_from_opinion_depth_diff():
    message = build_venue_message(
        venue="opinion",
        raw_data={
            "type": "depth_diff",
            "market_id": "2764",
            "side": "asks",
            "price": "0.55",
            "size": "12",
        },
        timestamp_ms=1000,
    )

    event = typed_event_from_message(message)

    assert isinstance(event, OrderBookDelta)
    assert event.side == "ask"
    assert event.market_id == "2764"
    assert event.price == 0.55
    assert event.size == 12


def test_typed_event_from_price_change():
    message = build_venue_message(
        venue="polymarket",
        raw_data={
            "type": "price_change",
            "asset_id": "asset-1",
            "best_bid": "0.40",
            "best_ask": "0.42",
        },
        timestamp_ms=1000,
    )

    event = typed_event_from_message(message)

    assert isinstance(event, PriceChangeEvent)
    assert event.best_bid == 0.40
    assert event.best_ask == 0.42
