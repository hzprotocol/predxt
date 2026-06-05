from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from predxt.events import BookLevel, OrderBookSnapshot
from predxt.kalshi.auth import build_kalshi_auth_headers
from predxt.models import MarketDetail, MarketSummary, VenueCredentialStatus
from predxt.rest import BaseRestClient, as_float, as_text, current_timestamp_ms


class KalshiRestClient(BaseRestClient):
    """Read-only REST client for Kalshi market data."""

    BASE_URL = "https://external-api.kalshi.com/trade-api/v2"

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        api_key_id: str | None = None,
        api_key: str | None = None,
        private_key_pem: str | None = None,
        private_key_path: str | None = None,
        private_key_passphrase: str | None = None,
        timeout: float = 10.0,
        client: Any = None,
    ) -> None:
        super().__init__(
            venue="kalshi",
            base_url=base_url,
            timeout=timeout,
            client=client,
        )
        self.api_key_id = api_key_id
        self.api_key = api_key
        self.private_key_pem = private_key_pem
        self.private_key_path = private_key_path
        self.private_key_passphrase = private_key_passphrase

    async def search_markets(self, query: str, limit: int = 20) -> list[MarketSummary]:
        payload = await self._get_json(
            "/markets",
            params={"search": query, "limit": limit},
            headers=self._headers("/trade-api/v2/markets"),
        )
        rows = _extract_rows(payload, "markets")
        return [_summary(row) for row in rows[:limit]]

    async def get_market(self, market_id: str) -> MarketDetail:
        path = f"/markets/{market_id}"
        payload = await self._get_json(
            path,
            headers=self._headers(f"/trade-api/v2{path}"),
        )
        row = _unwrap_market(payload)
        return _detail(row)

    async def get_orderbook(self, market_id_or_token_id: str) -> OrderBookSnapshot:
        path = f"/markets/{market_id_or_token_id}/orderbook"
        payload = await self._get_json(
            path,
            headers=self._headers(f"/trade-api/v2{path}"),
        )
        row = _unwrap_orderbook(payload)
        yes_bids = _kalshi_levels(
            row.get("yes_dollars") or row.get("yes") or row.get("yes_cents")
        )
        no_bids = _kalshi_levels(
            row.get("no_dollars") or row.get("no") or row.get("no_cents")
        )
        asks = [
            BookLevel(price=round(1.0 - level.price, 8), size=level.size)
            for level in no_bids
            if level.price is not None
        ]
        asks.sort(key=lambda level: level.price)
        return OrderBookSnapshot(
            venue="kalshi",
            event_type="rest_orderbook",
            timestamp_ms=current_timestamp_ms(),
            market_id=market_id_or_token_id,
            raw_data=payload if isinstance(payload, dict) else {"payload": payload},
            bids=yes_bids,
            asks=asks,
        )

    async def healthcheck(self) -> VenueCredentialStatus:
        try:
            await self._get_json(
                "/markets",
                params={"limit": 1},
                headers=self._headers("/trade-api/v2/markets"),
            )
        except Exception as exc:
            return VenueCredentialStatus(
                venue="kalshi",
                ok=False,
                message=str(exc),
            )
        return VenueCredentialStatus(
            venue="kalshi",
            ok=True,
            message="Kalshi read-only market data API is reachable.",
        )

    async def test_credentials(self) -> VenueCredentialStatus:
        return await self.healthcheck()

    def _headers(self, request_path: str) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        private_key = self._private_key()
        if self.api_key_id and private_key:
            parsed_path = urlparse(request_path).path
            headers.update(
                build_kalshi_auth_headers(
                    {
                        "key_id": self.api_key_id,
                        "private_key_pem": private_key,
                        "passphrase": self.private_key_passphrase,
                    },
                    ws_path=parsed_path,
                    method="GET",
                )
            )
            return headers
        if self.api_key_id and self.api_key:
            headers["X-Api-Key-Id"] = self.api_key_id
            headers["X-Api-Key"] = self.api_key
        return headers

    def _private_key(self) -> str | None:
        if self.private_key_pem:
            return self.private_key_pem
        if self.private_key_path:
            return Path(self.private_key_path).read_text(encoding="utf-8")
        return None


def _extract_rows(payload: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        value = payload.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def _unwrap_market(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        market = payload.get("market")
        if isinstance(market, dict):
            return market
        return payload
    return {}


def _unwrap_orderbook(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    if isinstance(payload.get("orderbook_fp"), dict):
        return payload["orderbook_fp"]
    if isinstance(payload.get("orderbook"), dict):
        return payload["orderbook"]
    return payload


def _summary(row: dict[str, Any]) -> MarketSummary:
    return MarketSummary(
        venue="kalshi",
        market_id=as_text(row.get("ticker")) or "",
        title=as_text(row.get("title")),
        subtitle=as_text(row.get("subtitle") or row.get("event_ticker")),
        category=as_text(row.get("category") or row.get("series_ticker")),
        status=as_text(row.get("status")),
        close_time=as_text(row.get("close_time") or row.get("close_ts")),
        outcomes=["yes", "no"],
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
        description=as_text(row.get("rules_primary") or row.get("rules_secondary")),
        event_id=as_text(row.get("event_ticker")),
        outcomes=summary.outcomes,
        raw_data=row,
    )


def _kalshi_levels(levels: Any) -> list[BookLevel]:
    rows: list[BookLevel] = []
    if not isinstance(levels, list):
        return rows
    for level in levels:
        if not isinstance(level, (list, tuple)) or len(level) < 2:
            continue
        price = as_float(level[0])
        size = as_float(level[1])
        if price is None or size is None:
            continue
        if price > 1:
            price = price / 100
        rows.append(BookLevel(price=price, size=size))
    rows.sort(key=lambda item: item.price, reverse=True)
    return rows


__all__ = ["KalshiRestClient"]
