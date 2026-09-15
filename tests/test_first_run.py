from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from predxt import first_run
from predxt.cli import main
from predxt.polymarket import PolymarketRestClient


def market(**changes):
    return {
        "id": "42",
        "question": "Example question?",
        "active": True,
        "closed": False,
        "enableOrderBook": True,
        "outcomes": '["Yes", "No"]',
        "clobTokenIds": '["111", "222"]',
        **changes,
    }


def book(**changes):
    return {
        "market": "condition-42",
        "asset_id": "222",
        "bids": [{"price": "0.40", "size": "10"}, {"price": "0.42", "size": "20"}],
        "asks": [{"price": "0.46", "size": "30"}, {"price": "0.44", "size": "40"}],
        **changes,
    }


def install_transport(monkeypatch, handler):
    clients = []
    requests = []

    async def checked(request):
        requests.append(request)
        assert request.method == "GET"
        return await handler(request)

    class TestClient(PolymarketRestClient):
        def _ensure_client(self):
            if self._client is None:
                self._client = httpx.AsyncClient(transport=httpx.MockTransport(checked))
                clients.append(self._client)
            return self._client

    monkeypatch.setattr(first_run, "PolymarketRestClient", TestClient)
    return requests, clients


def test_demo_works_outside_repository_without_network(monkeypatch, tmp_path, capsys):
    def no_network(*args, **kwargs):
        pytest.fail("Offline demo attempted to construct a network client")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(first_run, "PolymarketRestClient", no_network)
    assert main(["demo", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["synthetic"] is True
    assert data["best_bid"] == 0.42
    assert data["best_ask"] == 0.44
    assert data["book"]["raw_data"] == {"synthetic": True}


def test_explore_search_selection_and_book(monkeypatch, capsys):
    async def handler(request):
        if request.url.path == "/public-search":
            assert request.url.params["q"] == "weather"
            assert request.url.params["events_status"] == "active"
            assert request.url.params["search_profiles"] == "false"
            return httpx.Response(200, json={"events": [{"markets": [market()]}]})
        if request.url.path == "/markets/42":
            return httpx.Response(200, json=market())
        if request.url.path == "/book":
            assert request.url.params["token_id"] == "222"
            return httpx.Response(200, json=book())
        pytest.fail(f"Unexpected endpoint {request.url.path}")

    requests, clients = install_transport(monkeypatch, handler)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    answers = iter(["1", "2"])
    monkeypatch.setattr("builtins.input", lambda: next(answers))
    assert main(["explore", "polymarket", "--query", "weather"]) == 0
    output = capsys.readouterr()
    assert "Outcome: No" in output.out
    assert "REST SNAPSHOT" in output.out
    assert "Spread: 0.0200" in output.out
    assert "--asset-id 222" in output.out
    assert len(requests) == 3
    assert all(client.is_closed for client in clients)


@pytest.mark.parametrize(
    "levels, message",
    [
        ({"bids": [], "asks": []}, "orderbook is empty"),
        ({"bids": []}, "Only one side"),
    ],
)
def test_explore_empty_and_one_sided_book(monkeypatch, capsys, levels, message):
    async def handler(request):
        return httpx.Response(
            200, json=market() if request.url.path == "/markets/42" else book(**levels)
        )

    install_transport(monkeypatch, handler)
    assert (
        main(["explore", "polymarket", "--market-id", "42", "--outcome-index", "2"])
        == 0
    )
    assert message in capsys.readouterr().out


def test_explore_json_preserves_raw_book_and_has_no_prompts_on_stdout(
    monkeypatch, capsys
):
    async def handler(request):
        return httpx.Response(
            200, json=market() if request.url.path == "/markets/42" else book()
        )

    install_transport(monkeypatch, handler)
    assert (
        main(
            [
                "explore",
                "polymarket",
                "--market-id",
                "42",
                "--outcome-index",
                "2",
                "--json",
            ]
        )
        == 0
    )
    data = json.loads(capsys.readouterr().out)
    assert data["synthetic"] is False
    assert data["outcome"] == "No"
    assert data["book"]["raw_data"] == book()


@pytest.mark.parametrize(
    "changes",
    [
        {"closed": True},
        {"active": False},
        {"enableOrderBook": False},
        {"clobTokenIds": '["111"]'},
        {"clobTokenIds": '["111", "111"]'},
        {"clobTokenIds": '["111", "bad; command"]'},
        {"outcomes": "[]"},
        {"outcomes": '["Yes", "", "No"]', "clobTokenIds": '["111", "222", ""]'},
    ],
)
def test_invalid_market_stops_before_book_request(monkeypatch, capsys, changes):
    async def handler(request):
        assert request.url.path == "/markets/42"
        return httpx.Response(200, json=market(**changes))

    requests, clients = install_transport(monkeypatch, handler)
    assert (
        main(["explore", "polymarket", "--market-id", "42", "--outcome-index", "1"])
        == 1
    )
    assert len(requests) == 1
    assert all(client.is_closed for client in clients)
    assert "Error:" in capsys.readouterr().err


def test_wrong_book_identity_is_not_displayed(monkeypatch, capsys):
    async def handler(request):
        return httpx.Response(
            200,
            json=market()
            if request.url.path == "/markets/42"
            else book(asset_id="999"),
        )

    install_transport(monkeypatch, handler)
    assert (
        main(["explore", "polymarket", "--market-id", "42", "--outcome-index", "2"])
        == 1
    )
    output = capsys.readouterr()
    assert not output.out
    assert "does not match" in output.err


@pytest.mark.parametrize("payload", [{}, {"events": None}, {"events": []}])
def test_no_results_are_actionable(monkeypatch, capsys, payload):
    async def handler(request):
        return httpx.Response(200, json=payload)

    requests, _ = install_transport(monkeypatch, handler)
    assert main(["explore", "polymarket"]) == 1
    assert len(requests) == 1
    assert "Try a different --query" in capsys.readouterr().err


def test_noninteractive_search_lists_ids_and_explains_arguments(monkeypatch, capsys):
    async def handler(request):
        return httpx.Response(200, json={"events": [{"markets": [market()]}]})

    requests, _ = install_transport(monkeypatch, handler)
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    assert main(["explore", "polymarket"]) == 1
    output = capsys.readouterr()
    assert "market ID: 42" in output.err
    assert "--market-id ID --outcome-index N" in output.err
    assert len(requests) == 1


@pytest.mark.parametrize("failure", ["timeout", "forbidden"])
def test_network_failures_are_bounded_and_close_client(monkeypatch, capsys, failure):
    async def handler(request):
        if failure == "timeout":
            await asyncio.Event().wait()
        return httpx.Response(403, json={"error": "private response detail"})

    requests, clients = install_transport(monkeypatch, handler)
    assert main(["explore", "polymarket", "--timeout", "0.01"]) == 1
    output = capsys.readouterr()
    assert "predxt demo" in output.err
    assert "private response detail" not in output.err
    assert len(requests) == 1
    assert all(client.is_closed for client in clients)


@pytest.mark.parametrize(
    "args",
    [
        ["--timeout", "0"],
        ["--timeout", "nan"],
        ["--timeout", "inf"],
        ["--outcome-index", "0"],
        ["--query", "x", "--market-id", "42"],
    ],
)
def test_invalid_arguments_fail_before_network(monkeypatch, args):
    def no_network(*args, **kwargs):
        pytest.fail("Invalid arguments caused network access")

    monkeypatch.setattr(first_run, "PolymarketRestClient", no_network)
    with pytest.raises(SystemExit) as error:
        main(["explore", "polymarket", *args])
    assert error.value.code == 2


@pytest.mark.parametrize("answer", ["0", "3", "abc"])
def test_invalid_outcome_selection_stops_before_book(monkeypatch, capsys, answer):
    async def handler(request):
        assert request.url.path == "/markets/42"
        return httpx.Response(200, json=market())

    requests, clients = install_transport(monkeypatch, handler)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda: answer)
    assert main(["explore", "polymarket", "--market-id", "42"]) == 1
    assert len(requests) == 1
    assert all(client.is_closed for client in clients)


@pytest.mark.asyncio
async def test_search_flattens_deduplicates_and_filters_active_markets():
    async def handler(request):
        assert request.url.path == "/public-search"
        assert request.url.params["limit_per_type"] == "2"
        return httpx.Response(
            200,
            json={
                "events": [
                    {"markets": [market(id="closed", closed=True), market()]},
                    {"markets": [market(), None, market(id="43"), market(id="44")]},
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = PolymarketRestClient(client=http)
        results = await client.search_markets("example", limit=2, active_only=True)
    assert [row.market_id for row in results] == ["42", "43"]
    assert results[0].raw_data == market()


@pytest.mark.asyncio
async def test_empty_search_uses_market_listing():
    async def handler(request):
        assert request.url.path == "/markets"
        assert "search" not in request.url.params
        return httpx.Response(200, json=[market()])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = PolymarketRestClient(client=http)
        assert len(await client.search_markets("")) == 1


@pytest.mark.parametrize(
    "failure, expected_code", [(EOFError, 1), (KeyboardInterrupt, 130)]
)
def test_interrupted_selection_closes_client(
    monkeypatch, capsys, failure, expected_code
):
    async def handler(request):
        assert request.url.path == "/markets/42"
        return httpx.Response(200, json=market())

    def stop_input():
        raise failure

    requests, clients = install_transport(monkeypatch, handler)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", stop_input)
    assert main(["explore", "polymarket", "--market-id", "42"]) == expected_code
    assert len(requests) == 1
    assert all(client.is_closed for client in clients)
    if failure is EOFError:
        assert "Selection ended" in capsys.readouterr().err


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [0, -1])
async def test_invalid_search_limit_fails_before_network(limit):
    async def no_network(request):
        pytest.fail("Invalid limit caused a network request")

    async with httpx.AsyncClient(transport=httpx.MockTransport(no_network)) as http:
        client = PolymarketRestClient(client=http)
        with pytest.raises(ValueError, match="limit must be positive"):
            await client.search_markets("example", limit=limit)
