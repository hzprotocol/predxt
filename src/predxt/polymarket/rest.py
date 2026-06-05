from __future__ import annotations

import json
from typing import Any

from predxt.events import BookLevel, OrderBookSnapshot
from predxt.models import MarketDetail, MarketSummary, VenueCredentialStatus
from predxt.rest import BaseRestClient, as_text, current_timestamp_ms, parse_book_levels


class PolymarketRestClient(BaseRestClient):
    """Read-only REST client for Polymarket Gamma and CLOB market data."""

    GAMMA_URL = "https://gamma-api.polymarket.com"
    CLOB_URL = "https://clob.polymarket.com"

    def __init__(
        self,
        *,
        gamma_url: str = GAMMA_URL,
        clob_url: str = CLOB_URL,
        timeout: float = 10.0,
        client: Any = None,
    ) -> None:
        super().__init__(
            venue="polymarket",
            base_url=clob_url,
            timeout=timeout,
            client=client,
        )
        self.gamma_url = gamma_url.rstrip("/")

    async def search_markets(self, query: str, limit: int = 20) -> list[MarketSummary]:
        payload = await self._get_json(
            f"{self.gamma_url}/markets",
            params={"search": query, "limit": limit},
        )
        rows = _extract_rows(payload, "markets")
        return [_summary(row) for row in rows[:limit]]

    async def get_market(self, market_id: str) -> MarketDetail:
        payload = await self._get_json(f"{self.gamma_url}/markets/{market_id}")
        row = _unwrap_market(payload)
        return _detail(row)

    async def get_orderbook(self, market_id_or_token_id: str) -> OrderBookSnapshot:
        payload = await self._get_json(
            "/book",
            params={"token_id": market_id_or_token_id},
        )
        return OrderBookSnapshot(
            venue="polymarket",
            event_type="rest_orderbook",
            timestamp_ms=current_timestamp_ms(),
            market_id=as_text(payload.get("market")) if isinstance(payload, dict) else None,
            asset_id=(
                as_text(payload.get("asset_id")) if isinstance(payload, dict) else None
            ),
            raw_data=payload if isinstance(payload, dict) else {"payload": payload},
            bids=_levels(payload, "bids"),
            asks=_levels(payload, "asks"),
        )

    async def healthcheck(self) -> VenueCredentialStatus:
        try:
            await self._get_json(f"{self.gamma_url}/markets", params={"limit": 1})
        except Exception as exc:
            return VenueCredentialStatus(
                venue="polymarket",
                ok=False,
                message=str(exc),
            )
        return VenueCredentialStatus(
            venue="polymarket",
            ok=True,
            message="Polymarket public market data API is reachable.",
        )

    async def test_credentials(self) -> VenueCredentialStatus:
        return await self.healthcheck()


def _extract_rows(payload: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        value = payload.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
        data = payload.get("data")
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]
    return []


def _unwrap_market(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        market = payload.get("market")
        if isinstance(market, dict):
            return market
        return payload
    return {}


def _summary(row: dict[str, Any]) -> MarketSummary:
    market_id = as_text(row.get("id") or row.get("conditionId") or row.get("slug"))
    return MarketSummary(
        venue="polymarket",
        market_id=market_id or "",
        title=as_text(row.get("question") or row.get("title")),
        subtitle=as_text(row.get("slug")),
        category=as_text(row.get("category")),
        status=as_text(row.get("status") or row.get("active")),
        close_time=as_text(row.get("endDate") or row.get("end_date")),
        outcomes=_parse_string_list(row.get("outcomes")),
        raw_data=row,
    )


def _detail(row: dict[str, Any]) -> MarketDetail:
    summary = _summary(row)
    return MarketDetail(
        venue=summary.venue,
        market_id=summary.market_id,
        title=summary.title,
        subtitle=summary.subtitle,
        category=summary.category,
        status=summary.status,
        close_time=summary.close_time,
        description=as_text(row.get("description")),
        event_id=as_text(row.get("eventId") or row.get("event_id")),
        outcomes=summary.outcomes,
        token_ids=_parse_string_list(
            row.get("clobTokenIds") or row.get("clob_token_ids")
        ),
        raw_data=row,
    )


def _parse_string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except ValueError:
            decoded = [value]
        value = decoded
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _levels(payload: Any, key: str) -> list[BookLevel]:
    if not isinstance(payload, dict):
        return []
    return [
        BookLevel(price=row["price"], size=row["size"])
        for row in parse_book_levels(payload.get(key))
    ]


__all__ = ["PolymarketRestClient"]
