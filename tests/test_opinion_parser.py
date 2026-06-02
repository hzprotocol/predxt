from predxt.opinion.parser import parse_message


def test_parse_opinion_depth_diff():
    parsed = parse_message(
        {
            "marketId": 2764,
            "tokenId": "yes-token",
            "outcomeSide": 1,
            "side": "bids",
            "price": "0.2",
            "size": "50",
            "msgType": "market.depth.diff",
        }
    )

    assert parsed is not None
    assert parsed["type"] == "depth_diff"
    assert parsed["market_id"] == "2764"
    assert parsed["outcome_side"] == 1
    assert parsed["side"] == "bids"
    assert parsed["hash"]


def test_parse_opinion_last_trade():
    parsed = parse_message(
        {
            "marketId": 2764,
            "tokenId": "yes-token",
            "outcomeSide": 1,
            "side": "Buy",
            "price": "0.85",
            "shares": "10",
            "amount": "8.5",
            "msgType": "market.last.trade",
        }
    )

    assert parsed is not None
    assert parsed["type"] == "last_trade"
    assert parsed["side"] == "buy"
    assert parsed["shares"] == "10"
