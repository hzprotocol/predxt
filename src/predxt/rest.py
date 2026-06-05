from __future__ import annotations

import time
from typing import Any
from urllib.parse import urljoin

import httpx

from predxt.models import VenueApiError


class BaseRestClient:
    """Base async REST client for read-only venue market data APIs."""

    def __init__(
        self,
        *,
        venue: str,
        base_url: str,
        timeout: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.venue = venue
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = client
        self._owns_client = client is None

    async def close(self) -> None:
        if self._client is not None and self._owns_client:
            await self._client.aclose()
        self._client = None

    async def __aenter__(self) -> "BaseRestClient":
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.close()

    async def _get_json(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        return await self._request_json(
            "GET",
            path,
            params=params,
            headers=headers,
        )

    async def _post_json(
        self,
        path: str,
        *,
        json: Any,
        headers: dict[str, str] | None = None,
    ) -> Any:
        return await self._request_json(
            "POST",
            path,
            json=json,
            headers=headers,
        )

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        client = self._ensure_client()
        url = self._url(path)
        try:
            response = await client.request(
                method,
                url,
                params=params,
                json=json,
                headers=headers,
            )
        except httpx.HTTPError as exc:
            raise VenueApiError(
                venue=self.venue,
                message=str(exc),
                endpoint=path,
            ) from exc

        payload = self._decode_payload(response)
        if response.is_error:
            raise VenueApiError(
                venue=self.venue,
                message=self._error_message(payload),
                status_code=response.status_code,
                endpoint=path,
                payload=payload,
            )
        return payload

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
            self._owns_client = True
        return self._client

    def _url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return urljoin(f"{self.base_url}/", path.lstrip("/"))

    @staticmethod
    def _decode_payload(response: httpx.Response) -> Any:
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError:
            return response.text

    @staticmethod
    def _error_message(payload: Any) -> str:
        if isinstance(payload, dict):
            for key in ("message", "msg", "error", "detail"):
                value = payload.get(key)
                if value:
                    return str(value)
        if isinstance(payload, str) and payload.strip():
            return payload.strip()
        return "venue API request failed"


def current_timestamp_ms() -> float:
    return time.time() * 1000


def as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def as_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_book_levels(levels: Any) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    if not isinstance(levels, list):
        return rows
    for level in levels:
        price: Any
        size: Any
        if isinstance(level, dict):
            price = level.get("price")
            size = level.get("size")
        elif isinstance(level, (list, tuple)) and len(level) >= 2:
            price = level[0]
            size = level[1]
        else:
            continue
        parsed_price = as_float(price)
        parsed_size = as_float(size)
        if parsed_price is None or parsed_size is None:
            continue
        rows.append({"price": parsed_price, "size": parsed_size})
    return rows


__all__ = [
    "BaseRestClient",
    "as_float",
    "as_text",
    "current_timestamp_ms",
    "parse_book_levels",
]
