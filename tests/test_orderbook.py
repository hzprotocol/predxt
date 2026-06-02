from predxt.base import build_venue_message
from predxt.orderbook import OrderBookState


def test_orderbook_applies_snapshot_and_delta():
    state = OrderBookState()
    state.apply(
        build_venue_message(
            venue="polymarket",
            raw_data={
                "type": "book",
                "bids": [{"price": "0.40", "size": "10"}],
                "asks": [{"price": "0.45", "size": "8"}],
            },
            timestamp_ms=1000,
        )
    )

    assert state.best_bid == 0.40
    assert state.best_ask == 0.45

    state.apply(
        build_venue_message(
            venue="opinion",
            raw_data={
                "type": "depth_diff",
                "side": "bids",
                "price": "0.41",
                "size": "6",
            },
            timestamp_ms=1001,
        )
    )

    assert state.best_bid == 0.41
    assert state.best_bid_size() == 6

    state.apply(
        build_venue_message(
            venue="opinion",
            raw_data={
                "type": "depth_diff",
                "side": "bids",
                "price": "0.41",
                "size": "0",
            },
            timestamp_ms=1002,
        )
    )

    assert state.best_bid == 0.40


def test_orderbook_snapshot_depth():
    state = OrderBookState()
    state.apply(
        build_venue_message(
            venue="polymarket",
            raw_data={
                "type": "book",
                "bids": [
                    {"price": "0.40", "size": "10"},
                    {"price": "0.39", "size": "9"},
                ],
                "asks": [
                    {"price": "0.45", "size": "8"},
                    {"price": "0.46", "size": "7"},
                ],
            },
            timestamp_ms=1000,
        )
    )

    assert state.snapshot(depth=1) == {
        "bids": [{"price": 0.40, "size": 10.0}],
        "asks": [{"price": 0.45, "size": 8.0}],
    }
