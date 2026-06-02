from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Union

NormalizedMessage = Dict[str, Any]
MaybeMessages = Optional[Union[NormalizedMessage, List[NormalizedMessage]]]


def parse_message(data: Dict[str, Any]) -> MaybeMessages:
    """Normalize Polymarket events including batch price_change payloads."""

    msg_type = data.get("type") or data.get("event_type")

    if msg_type == "book":
        return {
            "type": "book",
            "asset_id": data.get("asset_id"),
            "bids": data.get("bids", []),
            "asks": data.get("asks", []),
            "hash": data.get("hash"),
            "market": data.get("market"),
            "timestamp": data.get("timestamp"),
        }

    if msg_type == "price_change":
        if "price_changes" in data:
            return _normalize_price_changes(data["price_changes"], fallback=data)
        return {
            "type": "price_change",
            "asset_id": data.get("asset_id"),
            "price": data.get("price"),
            "size": data.get("size"),
            "side": data.get("side"),
            "best_bid": data.get("new_best_bid") or data.get("best_bid"),
            "best_ask": data.get("new_best_ask") or data.get("best_ask"),
            "timestamp": data.get("timestamp") or data.get("timestamp_s"),
            "hash": data.get("hash"),
        }

    if msg_type == "best_bid_ask":
        return {
            "type": "best_bid_ask",
            "asset_id": data.get("asset_id"),
            "best_bid": data.get("best_bid"),
            "best_ask": data.get("best_ask"),
            "timestamp": data.get("timestamp"),
        }

    if msg_type == "last_trade_price":
        return {
            "type": "last_trade_price",
            "asset_id": data.get("asset_id"),
            "market": data.get("market"),
            "price": data.get("price"),
            "size": data.get("size"),
            "side": data.get("side"),
            "fee_rate_bps": data.get("fee_rate_bps"),
            "timestamp": data.get("timestamp"),
            "transaction_hash": data.get("transaction_hash"),
        }

    if msg_type == "new_market":
        return {"type": "new_market", "market": data.get("market", data)}

    if msg_type == "market_resolved":
        return {"type": "market_resolved", "market": data.get("market", data)}

    if msg_type == "price_change_batch" or "price_changes" in data:
        return _normalize_price_changes(data.get("price_changes", []), fallback=data)

    return None


def _normalize_price_changes(
    price_changes: Iterable[Dict[str, Any]], fallback: Optional[Dict[str, Any]] = None
) -> MaybeMessages:
    normalized: List[NormalizedMessage] = []
    for change in price_changes or []:
        normalized.append(
            {
                "type": "price_change",
                "asset_id": change.get("asset_id") or (fallback or {}).get("asset_id"),
                "price": change.get("price") or (fallback or {}).get("price"),
                "size": change.get("size"),
                "side": change.get("side"),
                "best_bid": change.get("best_bid"),
                "best_ask": change.get("best_ask"),
                "timestamp": change.get("timestamp")
                or (fallback or {}).get("timestamp"),
                "hash": change.get("hash"),
            }
        )

    if not normalized:
        return None
    if len(normalized) == 1:
        return normalized[0]
    return normalized
