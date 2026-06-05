from __future__ import annotations

from typing import Any

from predxt.events import BookLevel, OrderBookSnapshot
from predxt.models import MarketDetail, MarketSummary, VenueCredentialStatus
from predxt.rest import BaseRestClient, as_text, current_timestamp_ms, parse_book_levels


class OpinionRestClient(BaseRestClient):
    """Read-only REST client for Opinion OpenAPI market data."""

    BASE_URL = "https://openapi.opinion.trade/openapi"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = BASE_URL,
        timeout: float = 10.0,
        client: Any = None,
    ) -> None:
        super().__init__(
            venue="opinion",
            base_url=base_url,
            timeout=timeout,
            client=client,
        )
        self.api_key = api_key

    async def search_markets(self, query: str, limit: int = 20) -> list[MarketSummary]:
        capped_limit = max(1, min(int(limit), 20))
        payload = await self._get_json(
            "/market",
            params={"page": 1, "limit": capped_limit, "marketType": 2},
            headers=self._headers(),
        )
        rows = _extract_rows(payload)
        needle = query.strip().lower()
        if needle:
            rows = [
                row
                for row in rows
                if needle
                in " ".join(
                    str(row.get(key) or "")
                    for key in ("title", "marketTitle", "question", "slug")
                ).lower()
            ]
        return [_summary(row) for row in rows[:limit]]

    async def get_market(self, market_id: str) -> MarketDetail:
        payload = await self._get_json(
            f"/market/{market_id}",
            headers=self._headers(),
        )
        row = _unwrap_result(payload)
        return _detail(row)

    async def get_orderbook(self, market_id_or_token_id: str) -> OrderBookSnapshot:
        payload = await self._get_json(
            "/token/orderbook",
            params={"token_id": market_id_or_token_id},
            headers=self._headers(),
        )
        row = _unwrap_result(payload)
        return OrderBookSnapshot(
            venue="opinion",
            event_type="rest_orderbook",
            timestamp_ms=current_timestamp_ms(),
            market_id=as_text(row.get("market")),
            asset_id=as_text(row.get("tokenId") or row.get("token_id")),
            raw_data=payload if isinstance(payload, dict) else {"payload": payload},
            bids=_levels(row, "bids"),
            asks=_levels(row, "asks"),
        )

    async def healthcheck(self) -> VenueCredentialStatus:
        try:
            await self._get_json(
                "/market",
                params={"page": 1, "limit": 1},
                headers=self._headers(),
            )
        except Exception as exc:
            return VenueCredentialStatus(
                venue="opinion",
                ok=False,
                message=str(exc),
            )
        return VenueCredentialStatus(
            venue="opinion",
            ok=True,
            message="Opinion OpenAPI read-only market data is reachable.",
        )

    async def test_credentials(self) -> VenueCredentialStatus:
        return await self.healthcheck()

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["apikey"] = self.api_key
        return headers


def _extract_rows(payload: Any) -> list[dict[str, Any]]:
    result = _unwrap_result(payload)
    for key in ("items", "list", "data", "markets", "records"):
        value = result.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def _unwrap_result(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    result = payload.get("result")
    if isinstance(result, dict):
        return result
    return payload


def _summary(row: dict[str, Any]) -> MarketSummary:
    return MarketSummary(
        venue="opinion",
        market_id=as_text(row.get("id") or row.get("marketId")) or "",
        title=as_text(row.get("title") or row.get("marketTitle") or row.get("question")),
        subtitle=as_text(row.get("slug")),
        category=as_text(row.get("category") or row.get("categoryName")),
        status=as_text(row.get("status")),
        close_time=as_text(row.get("endTime") or row.get("closeTime")),
        outcomes=_outcomes(row),
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
        event_id=as_text(row.get("rootMarketId") or row.get("collectionId")),
        outcomes=summary.outcomes,
        token_ids=[
            value
            for value in (
                as_text(row.get("yesTokenId")),
                as_text(row.get("noTokenId")),
                as_text(row.get("tokenId")),
            )
            if value
        ],
        raw_data=row,
    )


def _outcomes(row: dict[str, Any]) -> list[str]:
    values = row.get("outcomes")
    if isinstance(values, list):
        return [str(value).strip() for value in values if str(value).strip()]
    labels = [
        as_text(row.get("yesTitle") or row.get("yesOutcome") or "yes"),
        as_text(row.get("noTitle") or row.get("noOutcome") or "no"),
    ]
    return [label for label in labels if label]


def _levels(payload: dict[str, Any], key: str) -> list[BookLevel]:
    return [
        BookLevel(price=row["price"], size=row["size"])
        for row in parse_book_levels(payload.get(key))
    ]


__all__ = ["OpinionRestClient"]
