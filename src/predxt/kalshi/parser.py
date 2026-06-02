from __future__ import annotations

from typing import Any, Dict, Iterable, Optional


def parse_message(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalize Kalshi websocket envelopes into a stable message shape.

    Supported kinds: orderbook_snapshot, orderbook_delta, ticker, trade.
    """

    msg_type = (data.get("type") or "").lower()
    if msg_type not in {"orderbook_snapshot", "orderbook_delta", "ticker", "trade"}:
        return None

    msg = data.get("msg")
    payload: Dict[str, Any] = msg if isinstance(msg, dict) else data
    market_ticker = payload.get("market_ticker") or data.get("market_ticker")
    timestamp = (
        payload.get("timestamp")
        or data.get("timestamp")
        or payload.get("ts")
        or data.get("ts")
    )
    seq = data.get("seq") or payload.get("seq") or data.get("sequence")

    if msg_type == "orderbook_snapshot":
        has_binary_book = "yes_dollars_fp" in payload or "no_dollars_fp" in payload
        bids = _parse_yes_levels(
            payload.get("yes_dollars_fp") or payload.get("bids", [])
        )
        asks = (
            _parse_no_levels_as_yes_asks(payload.get("no_dollars_fp", []))
            if has_binary_book
            else _parse_yes_levels(payload.get("asks", []))
        )
        return {
            "type": msg_type,
            "market_ticker": market_ticker or payload.get("market"),
            "timestamp": timestamp,
            "seq": seq,
            "bids": bids,
            "asks": asks,
            "side": payload.get("side"),
            "price": payload.get("price"),
            "size": payload.get("size"),
            "best_bid": max((level["price"] for level in bids), default=None),
            "best_ask": min((level["price"] for level in asks), default=None),
            "hash": data.get("hash") or payload.get("hash"),
            "raw": data,
        }

    return {
        "type": msg_type,
        "market_ticker": market_ticker or payload.get("market"),
        "timestamp": timestamp,
        "seq": seq,
        "bids": payload.get("bids", []),
        "asks": payload.get("asks", []),
        "side": payload.get("side"),
        "price": payload.get("price"),
        "size": payload.get("size"),
        "best_bid": payload.get("best_bid"),
        "best_ask": payload.get("best_ask"),
        "hash": data.get("hash") or payload.get("hash"),
        "raw": data,
    }


def _parse_yes_levels(levels: Iterable[Any]) -> list[dict[str, float]]:
    normalized: list[dict[str, float]] = []
    for level in levels:
        parsed = _coerce_level(level)
        if parsed is None:
            continue
        normalized.append(parsed)
    return normalized


def _parse_no_levels_as_yes_asks(levels: Iterable[Any]) -> list[dict[str, float]]:
    normalized: list[dict[str, float]] = []
    for level in levels:
        parsed = _coerce_level(level)
        if parsed is None:
            continue
        yes_ask_price = round(1.0 - parsed["price"], 4)
        normalized.append({"price": yes_ask_price, "size": parsed["size"]})
    return normalized


def _coerce_level(level: Any) -> Optional[dict[str, float]]:
    price: object
    size: object
    if isinstance(level, dict):
        price = level.get("price")
        size = level.get("size")
    elif isinstance(level, (list, tuple)) and len(level) >= 2:
        price, size = level[0], level[1]
    else:
        return None

    coerced_price = _as_float(price)
    coerced_size = _as_float(size)
    if coerced_price is None or coerced_size is None:
        return None
    return {"price": coerced_price, "size": coerced_size}


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None
