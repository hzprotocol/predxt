from __future__ import annotations

import httpx
import pytest

from predxt import OrderBookSnapshot, VenueApiError
from predxt.kalshi import KalshiRestClient
from predxt.opinion import OpinionRestClient
from predxt.polymarket import PolymarketRestClient


@pytest.mark.asyncio
async def test_polymarket_rest_client_reads_markets_and_orderbook() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "gamma.test" and request.url.path == "/markets":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": "1",
                        "question": "Will it rain?",
                        "clobTokenIds": '["yes-token", "no-token"]',
                        "outcomes": '["Yes", "No"]',
                    }
                ],
            )
        if request.url.host == "gamma.test" and request.url.path == "/markets/1":
            return httpx.Response(
                200,
                json={
                    "id": "1",
                    "question": "Will it rain?",
                    "clobTokenIds": '["yes-token", "no-token"]',
                    "outcomes": '["Yes", "No"]',
                },
            )
        if request.url.host == "clob.test" and request.url.path == "/book":
            assert request.url.params["token_id"] == "yes-token"
            return httpx.Response(
                200,
                json={
                    "market": "condition-1",
                    "asset_id": "yes-token",
                    "bids": [{"price": "0.41", "size": "100"}],
                    "asks": [{"price": "0.43", "size": "75"}],
                },
            )
        raise AssertionError(f"Unexpected request: {request.url}")

    client = PolymarketRestClient(
        gamma_url="https://gamma.test",
        clob_url="https://clob.test",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    rows = await client.search_markets("rain")
    detail = await client.get_market("1")
    book = await client.get_orderbook("yes-token")

    assert rows[0].market_id == "1"
    assert detail.token_ids == ["yes-token", "no-token"]
    assert isinstance(book, OrderBookSnapshot)
    assert book.market_id == "condition-1"
    assert book.asset_id == "yes-token"
    assert book.bids[0].price == 0.41
    assert book.asks[0].size == 75


@pytest.mark.asyncio
async def test_kalshi_rest_client_reads_markets_and_implied_yes_asks(monkeypatch) -> None:
    monkeypatch.setattr(
        "predxt.kalshi.auth._sign_rsa_pss",
        lambda **_kwargs: "signed-token",
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/trade-api/v2/markets":
            assert request.headers["KALSHI-ACCESS-KEY"] == "key-id"
            return httpx.Response(
                200,
                json={
                    "markets": [
                        {
                            "ticker": "KXTEST",
                            "title": "Will it happen?",
                            "status": "open",
                        }
                    ]
                },
            )
        if request.url.path == "/trade-api/v2/markets/KXTEST":
            return httpx.Response(
                200,
                json={"market": {"ticker": "KXTEST", "title": "Will it happen?"}},
            )
        if request.url.path == "/trade-api/v2/markets/KXTEST/orderbook":
            return httpx.Response(
                200,
                json={
                    "orderbook_fp": {
                        "yes_dollars": [["0.41", "100"]],
                        "no_dollars": [["0.55", "80"]],
                    }
                },
            )
        raise AssertionError(f"Unexpected request: {request.url}")

    client = KalshiRestClient(
        base_url="https://kalshi.test/trade-api/v2",
        api_key_id="key-id",
        private_key_pem="PRIVATE KEY",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    rows = await client.search_markets("happen")
    detail = await client.get_market("KXTEST")
    book = await client.get_orderbook("KXTEST")

    assert rows[0].market_id == "KXTEST"
    assert detail.market_id == "KXTEST"
    assert book.bids[0].price == 0.41
    assert book.asks[0].price == 0.45
    assert book.asks[0].size == 80


@pytest.mark.asyncio
async def test_opinion_rest_client_reads_markets_and_orderbook() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["apikey"] == "opinion-key"
        if request.url.path == "/openapi/market":
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "msg": "success",
                    "result": {
                        "items": [
                            {
                                "id": 2764,
                                "title": "Will it happen?",
                                "yesTokenId": "yes-2764",
                                "noTokenId": "no-2764",
                            }
                        ]
                    },
                },
            )
        if request.url.path == "/openapi/market/2764":
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "msg": "success",
                    "result": {
                        "id": 2764,
                        "title": "Will it happen?",
                        "yesTokenId": "yes-2764",
                    },
                },
            )
        if request.url.path == "/openapi/token/orderbook":
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "msg": "success",
                    "result": {
                        "market": "2764",
                        "tokenId": "yes-2764",
                        "bids": [{"price": "0.50", "size": "11"}],
                        "asks": [{"price": "0.53", "size": "8"}],
                    },
                },
            )
        raise AssertionError(f"Unexpected request: {request.url}")

    client = OpinionRestClient(
        api_key="opinion-key",
        base_url="https://opinion.test/openapi",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    rows = await client.search_markets("happen")
    detail = await client.get_market("2764")
    book = await client.get_orderbook("yes-2764")

    assert rows[0].market_id == "2764"
    assert detail.token_ids == ["yes-2764"]
    assert book.market_id == "2764"
    assert book.asset_id == "yes-2764"
    assert book.asks[0].price == 0.53


@pytest.mark.asyncio
async def test_rest_error_does_not_include_secret_headers() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"msg": "invalid credentials"})

    client = OpinionRestClient(
        api_key="secret-opinion-key",
        base_url="https://opinion.test/openapi",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(VenueApiError) as excinfo:
        await client.get_market("2764")

    assert "secret-opinion-key" not in str(excinfo.value)
    assert "invalid credentials" in str(excinfo.value)
