import json
from pathlib import Path

import pytest

from predxt.polymarket.parser import parse_message


@pytest.mark.parametrize(
    "payload,expected",
    [
        (
            {
                "type": "book",
                "asset_id": "0x1",
                "bids": [{"price": "0.1", "size": "10"}],
                "asks": [],
                "hash": "abc",
            },
            {
                "type": "book",
                "asset_id": "0x1",
                "bids": [{"price": "0.1", "size": "10"}],
                "asks": [],
                "hash": "abc",
                "market": None,
                "timestamp": None,
            },
        ),
        (
            {
                "type": "price_change",
                "asset_id": "0x2",
                "new_best_bid": "0.2",
                "new_best_ask": "0.3",
                "timestamp_s": 123456,
            },
            {
                "type": "price_change",
                "asset_id": "0x2",
                "price": None,
                "size": None,
                "side": None,
                "best_bid": "0.2",
                "best_ask": "0.3",
                "timestamp": 123456,
                "hash": None,
            },
        ),
        (
            {
                "type": "best_bid_ask",
                "asset_id": "0x3",
                "best_bid": "0.4",
                "best_ask": "0.5",
            },
            {
                "type": "best_bid_ask",
                "asset_id": "0x3",
                "best_bid": "0.4",
                "best_ask": "0.5",
                "timestamp": None,
            },
        ),
        (
            {
                "event_type": "last_trade_price",
                "asset_id": "0x4",
                "market": "0xmarket",
                "price": "0.52",
                "size": "50000",
                "fee_rate_bps": "0",
                "side": "BUY",
                "timestamp": "1772279206589",
                "transaction_hash": "0xabc",
            },
            {
                "type": "last_trade_price",
                "asset_id": "0x4",
                "market": "0xmarket",
                "price": "0.52",
                "size": "50000",
                "fee_rate_bps": "0",
                "side": "BUY",
                "timestamp": "1772279206589",
                "transaction_hash": "0xabc",
            },
        ),
        (
            {"type": "new_market", "market": {"id": "m1"}},
            {"type": "new_market", "market": {"id": "m1"}},
        ),
        (
            {"type": "market_resolved", "market": {"id": "m1", "result": "yes"}},
            {"type": "market_resolved", "market": {"id": "m1", "result": "yes"}},
        ),
        ({"type": "unknown"}, None),
        ({}, None),
    ],
)
def test_parse_message(payload, expected):
    assert parse_message(payload) == expected


def _fixture_path(name: str) -> Path:
    return Path(__file__).parent / "fixtures" / name


@pytest.mark.parametrize(
    "fixture_name, expected_type, min_messages",
    [
        ("polymarket_order_books.json", "book", 1),
        ("polymarket_trade_updates.json", "price_change", 2),
        ("polymarket_other.json", "last_trade_price", 1),
    ],
)
def test_parse_real_fixtures(fixture_name: str, expected_type: str, min_messages: int):
    payloads = json.loads(_fixture_path(fixture_name).read_text())
    parsed = []
    for item in payloads:
        result = parse_message(item)
        if isinstance(result, list):
            parsed.extend([r for r in result if r is not None])
        elif result is not None:
            parsed.append(result)

    assert len(parsed) >= min_messages
    assert all(p["type"] == expected_type for p in parsed)
