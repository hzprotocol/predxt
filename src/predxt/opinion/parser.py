from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

MaybeMessages = Optional[Dict[str, Any] | List[Dict[str, Any]]]


def parse_message(data: Dict[str, Any]) -> MaybeMessages:
    msg_type = str(data.get("msgType") or data.get("channel") or "").strip()
    if msg_type == "market.depth.diff":
        return _parse_depth_diff(data)
    if msg_type == "market.last.price":
        return _parse_last_price(data)
    if msg_type == "market.last.trade":
        return _parse_last_trade(data)
    return None


def _parse_depth_diff(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": "depth_diff",
        "msgType": "market.depth.diff",
        "market_id": _market_id(data),
        "marketId": _as_int(data.get("marketId")),
        "rootMarketId": _as_int(data.get("rootMarketId")),
        "token_id": _as_str(data.get("tokenId")),
        "outcome_side": _as_int(data.get("outcomeSide")),
        "side": _as_str(data.get("side")).lower(),
        "price": _as_str(data.get("price")),
        "size": _as_str(data.get("size")),
        "timestamp": _timestamp(data),
        "hash": _hash(data),
    }


def _parse_last_price(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": "last_price",
        "msgType": "market.last.price",
        "market_id": _market_id(data),
        "marketId": _as_int(data.get("marketId")),
        "rootMarketId": _as_int(data.get("rootMarketId")),
        "token_id": _as_str(data.get("tokenId")),
        "outcome_side": _as_int(data.get("outcomeSide")),
        "price": _as_str(data.get("price")),
        "timestamp": _timestamp(data),
        "hash": _hash(data),
    }


def _parse_last_trade(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": "last_trade",
        "msgType": "market.last.trade",
        "market_id": _market_id(data),
        "marketId": _as_int(data.get("marketId")),
        "rootMarketId": _as_int(data.get("rootMarketId")),
        "token_id": _as_str(data.get("tokenId")),
        "outcome_side": _as_int(data.get("outcomeSide")),
        "side": _as_str(data.get("side")).lower(),
        "price": _as_str(data.get("price")),
        "shares": _as_str(data.get("shares")),
        "amount": _as_str(data.get("amount")),
        "timestamp": _timestamp(data),
        "hash": _hash(data),
    }


def _market_id(data: Dict[str, Any]) -> str:
    value = data.get("marketId")
    return "" if value is None else str(value).strip()


def _timestamp(data: Dict[str, Any]) -> int:
    value = data.get("timestamp") or data.get("ts") or data.get("time")
    parsed = _as_int(value)
    return parsed if parsed is not None else 0


def _hash(data: Dict[str, Any]) -> str:
    return hashlib.sha1(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()


def _as_str(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
