"""Small, bounded first-run CLI flows; all network operations read market data."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
from collections.abc import Awaitable
from dataclasses import asdict
from datetime import datetime, timezone
from typing import TypeVar

from predxt.events import BookLevel, OrderBookSnapshot
from predxt.models import MarketDetail, VenueApiError
from predxt.orderbook import OrderBookState
from predxt.polymarket import PolymarketRestClient

T = TypeVar("T")


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def positive_seconds(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a finite positive number")
    return number


def demo(*, json_output: bool = False) -> int:
    """Show synthetic data from the installed package, without files or network."""
    book = OrderBookSnapshot(
        venue="polymarket",
        event_type="demo_orderbook",
        timestamp_ms=0,
        market_id="demo-market",
        asset_id="demo-yes",
        bids=[BookLevel(0.42, 100), BookLevel(0.41, 50)],
        asks=[BookLevel(0.44, 80), BookLevel(0.45, 120)],
        raw_data={"synthetic": True},
    )
    _show_book(
        book,
        title="Example market",
        outcome="Yes",
        synthetic=True,
        json_output=json_output,
    )
    if not json_output:
        print('\nRead a real market: predxt explore polymarket --query "bitcoin"')
    return 0


async def explore(args: argparse.Namespace) -> int:
    client = PolymarketRestClient(timeout=args.timeout)
    try:
        market_id = args.market_id
        if market_id is None:
            if not args.query.strip():
                raise ValueError("Enter a search query or use --market-id.")
            markets = await _bounded(
                client.search_markets(args.query, limit=10, active_only=True),
                args.timeout,
            )
            markets = [m for m in markets if m.raw_data.get("enableOrderBook") is True]
            if not markets:
                raise ValueError(
                    "No open orderbook markets in these search results. "
                    "Try a different --query."
                )
            for index, candidate in enumerate(markets, 1):
                print(
                    f"{index}. {_text(candidate.title or candidate.market_id)} "
                    f"(market ID: {_text(candidate.market_id)})",
                    file=sys.stderr,
                )
            selected = _choose(len(markets), "market", None)
            market_id = markets[selected].market_id

        market = await _bounded(client.get_market(market_id), args.timeout)
        _check_market(market)
        for index, outcome in enumerate(market.outcomes, 1):
            print(f"{index}. {_text(outcome)}", file=sys.stderr)
        selected = _choose(len(market.outcomes), "outcome", args.outcome_index)
        token_id = market.token_ids[selected]
        book = await _bounded(client.get_orderbook(token_id), args.timeout)
        if book.asset_id != token_id:
            raise ValueError(
                "The returned orderbook does not match the chosen outcome."
            )
        _show_book(
            book,
            title=market.title or market.market_id,
            outcome=market.outcomes[selected],
            synthetic=False,
            json_output=args.json,
        )
        if not args.json:
            print("\nContinue with WebSocket events (Ctrl-C to stop):")
            print(f"predxt stream polymarket --asset-id {token_id} --limit 5 --jsonl")
        return 0
    except TimeoutError:
        print(
            f"Timed out after {args.timeout:g}s waiting for Polymarket. "
            "Try predxt demo for an offline example.",
            file=sys.stderr,
        )
        return 1
    except VenueApiError as exc:
        status = f" (HTTP {exc.status_code})" if exc.status_code else ""
        print(
            f"Polymarket request failed{status}. "
            "Check venue availability; try predxt demo for an offline example.",
            file=sys.stderr,
        )
        return 1
    except EOFError:
        print("Selection ended before a number was entered.", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        await client.close()


async def _bounded(operation: Awaitable[T], timeout: float) -> T:
    async with asyncio.timeout(timeout):
        return await operation


def _choose(count: int, label: str, requested: int | None) -> int:
    if requested is None:
        if not sys.stdin.isatty():
            raise ValueError(
                "Interactive selection needs a terminal. For scripts, pass "
                "--market-id ID --outcome-index N (1-based)."
            )
        print(f"Choose {label} [1-{count}]: ", file=sys.stderr, end="", flush=True)
        try:
            requested = int(input())
        except ValueError:
            raise ValueError(
                f"Enter the {label} number between 1 and {count}."
            ) from None
    if not 1 <= requested <= count:
        raise ValueError(f"Choose the {label} number between 1 and {count}.")
    return requested - 1


def _check_market(market: MarketDetail) -> None:
    raw = market.raw_data
    if (
        raw.get("active") is not True
        or raw.get("closed") is not False
        or raw.get("enableOrderBook") is not True
    ):
        raise ValueError(
            "This market has no open orderbook. Search for another market."
        )
    if (
        not market.outcomes
        or len(market.outcomes) != len(market.token_ids)
        or len(set(market.token_ids)) != len(market.token_ids)
        or any(
            not token.isascii() or not token.isdecimal() for token in market.token_ids
        )
    ):
        raise ValueError("This market has incomplete outcome/token identifiers.")
    # Reject independently filtered arrays that could silently pair the wrong
    # label with a token. The CLI needs the original one-to-one association.
    outcomes = raw.get("outcomes")
    tokens = raw.get("clobTokenIds", raw.get("clob_token_ids"))
    if isinstance(outcomes, str):
        outcomes = json.loads(outcomes)
    if isinstance(tokens, str):
        tokens = json.loads(tokens)
    if outcomes != market.outcomes or tokens != market.token_ids:
        raise ValueError("This market has ambiguous outcome/token identifiers.")


def _text(value: str) -> str:
    return "".join(char if char.isprintable() else " " for char in value)


def _show_book(
    book: OrderBookSnapshot,
    *,
    title: str,
    outcome: str,
    synthetic: bool,
    json_output: bool,
) -> None:
    state = OrderBookState()
    state.apply(book)
    if json_output:
        print(
            json.dumps(
                {
                    "synthetic": synthetic,
                    "title": title,
                    "outcome": outcome,
                    "book": asdict(book),
                    "best_bid": state.best_bid,
                    "best_ask": state.best_ask,
                },
                sort_keys=True,
            )
        )
        return
    print("SYNTHETIC DEMO — no network requests" if synthetic else "REST SNAPSHOT")
    print(f"Market: {_text(title)}\nOutcome: {_text(outcome)}")
    if not synthetic:
        fetched = datetime.fromtimestamp(book.timestamp_ms / 1000, tz=timezone.utc)
        print(f"Fetched at: {fetched.isoformat()} (local receipt time)")
    print(f"{'BID PRICE':>10} {'SIZE':>12} | {'ASK PRICE':>10} {'SIZE':>12}")
    levels = state.snapshot(depth=5)
    for index in range(max(len(levels["bids"]), len(levels["asks"]))):
        sides = []
        for side in ("bids", "asks"):
            if index < len(levels[side]):
                level = levels[side][index]
                sides.append(f"{level['price']:10.4f} {level['size']:12g}")
            else:
                sides.append(f"{'—':>10} {'—':>12}")
        print(" | ".join(sides))
    if not state.bids and not state.asks:
        print("The orderbook is empty; no bid or ask is available.")
    elif state.best_bid is not None and state.best_ask is not None:
        print(f"Spread: {state.best_ask - state.best_bid:.4f}")
    else:
        print("Only one side of the orderbook is available; spread is unavailable.")
