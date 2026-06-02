from predxt.kalshi.parser import parse_message


def test_parse_kalshi_snapshot_message():
    payload = {
        "type": "orderbook_snapshot",
        "market_ticker": "EVT-1",
        "timestamp": 100,
        "bids": [{"price": "0.4", "size": "5"}],
        "asks": [{"price": "0.45", "size": "6"}],
    }

    parsed = parse_message(payload)

    assert parsed is not None
    assert parsed["type"] == "orderbook_snapshot"
    assert parsed["market_ticker"] == "EVT-1"
    assert parsed["best_bid"] == 0.4
    assert parsed["best_ask"] == 0.45


def test_parse_kalshi_live_snapshot_envelope():
    payload = {
        "type": "orderbook_snapshot",
        "seq": 2,
        "msg": {
            "market_ticker": "KXNBA-26-OKC",
            "yes_dollars_fp": [["0.4100", "4626.00"]],
            "no_dollars_fp": [["0.5700", "29404.00"]],
        },
    }

    parsed = parse_message(payload)

    assert parsed is not None
    assert parsed["market_ticker"] == "KXNBA-26-OKC"
    assert parsed["bids"] == [{"price": 0.41, "size": 4626.0}]
    assert parsed["asks"] == [{"price": 0.43, "size": 29404.0}]
    assert parsed["best_bid"] == 0.41
    assert parsed["best_ask"] == 0.43


def test_parse_kalshi_unsupported_message_returns_none():
    assert parse_message({"type": "status"}) is None
