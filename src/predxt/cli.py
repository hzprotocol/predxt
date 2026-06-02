from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterable

from predxt.base import VenueMessage, build_venue_message
from predxt.events import typed_event_from_message
from predxt.kalshi import KalshiWsClient
from predxt.kalshi.parser import parse_message as parse_kalshi_message
from predxt.opinion import OpinionWsClient
from predxt.opinion.parser import parse_message as parse_opinion_message
from predxt.polymarket import PolymarketWsClient
from predxt.polymarket.parser import parse_message as parse_polymarket_message


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "parse-fixture":
        return _parse_fixture(args)
    if args.command == "stream":
        return asyncio.run(_stream(args))
    parser.print_help()
    return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="predxt",
        description="Read-only prediction market realtime ingestion tools.",
    )
    subcommands = parser.add_subparsers(dest="command")

    fixture = subcommands.add_parser(
        "parse-fixture",
        help="Parse offline JSON fixture messages with a venue parser.",
    )
    fixture.add_argument("path", type=Path)
    fixture.add_argument(
        "--venue",
        choices=["polymarket", "kalshi", "opinion"],
        required=True,
    )
    fixture.add_argument("--jsonl", action="store_true", help="Emit one JSON object per line.")

    stream = subcommands.add_parser("stream", help="Stream venue websocket messages.")
    stream_subcommands = stream.add_subparsers(dest="venue", required=True)

    polymarket = stream_subcommands.add_parser("polymarket", help="Stream Polymarket.")
    polymarket.add_argument("--asset-id", dest="asset_ids", action="append", required=True)
    _add_stream_common_args(polymarket)

    kalshi = stream_subcommands.add_parser("kalshi", help="Stream Kalshi.")
    kalshi.add_argument("--market", dest="markets", action="append", required=True)
    _add_stream_common_args(kalshi)

    opinion = stream_subcommands.add_parser("opinion", help="Stream Opinion.")
    opinion.add_argument("--market-id", dest="market_ids", action="append", required=True)
    _add_stream_common_args(opinion)

    return parser


def _add_stream_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--jsonl", action="store_true", help="Emit one JSON object per line.")


def _parse_fixture(args: argparse.Namespace) -> int:
    parser = _parser_for_venue(args.venue)
    payload = json.loads(args.path.read_text())
    messages = payload if isinstance(payload, list) else [payload]
    for raw in messages:
        if not isinstance(raw, dict):
            continue
        for parsed in _iter_parsed(parser(raw)):
            message = build_venue_message(
                venue=args.venue,
                raw_data=parsed,
                timestamp_ms=time.time() * 1000,
            )
            _emit_message(message, jsonl=args.jsonl)
    return 0


async def _stream(args: argparse.Namespace) -> int:
    if args.venue == "polymarket":
        await _stream_polymarket(args)
        return 0
    if args.venue == "kalshi":
        await _stream_kalshi(args)
        return 0
    if args.venue == "opinion":
        await _stream_opinion(args)
        return 0
    raise SystemExit(f"Unsupported venue: {args.venue}")


async def _stream_polymarket(args: argparse.Namespace) -> None:
    client = PolymarketWsClient()
    await client.connect()
    try:
        await client.subscribe(
            ["market"],
            {"assets_ids": args.asset_ids, "initial_dump": True},
        )
        await _emit_stream(client.messages(), limit=args.limit, jsonl=args.jsonl)
    finally:
        await client.close()


async def _stream_kalshi(args: argparse.Namespace) -> None:
    client = KalshiWsClient()
    await client.connect(auth_params=_kalshi_auth_from_env())
    try:
        await client.subscribe(
            ["orderbook_snapshot", "orderbook_delta"],
            {"market_tickers": args.markets},
        )
        await _emit_stream(client.messages(), limit=args.limit, jsonl=args.jsonl)
    finally:
        await client.close()


async def _stream_opinion(args: argparse.Namespace) -> None:
    api_key = os.environ.get("OPINION_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("Set OPINION_API_KEY.")
    client = OpinionWsClient(api_key=api_key)
    await client.connect()
    try:
        await client.subscribe(["market.depth.diff"], {"market_ids": args.market_ids})
        await _emit_stream(client.messages(), limit=args.limit, jsonl=args.jsonl)
    finally:
        await client.close()


async def _emit_stream(
    messages: Any,
    *,
    limit: int,
    jsonl: bool,
) -> None:
    seen = 0
    async for message in messages:
        _emit_message(message, jsonl=jsonl)
        seen += 1
        if seen >= limit:
            return


def _emit_message(message: VenueMessage, *, jsonl: bool) -> None:
    payload = {
        "message": _message_to_dict(message),
        "typed_event": _dataclass_to_dict(typed_event_from_message(message)),
    }
    if jsonl:
        _safe_print(json.dumps(payload, sort_keys=True))
    else:
        _safe_print(json.dumps(payload, indent=2, sort_keys=True))


def _safe_print(text: str) -> None:
    try:
        print(text)
    except BrokenPipeError:
        try:
            sys.stdout.close()
        except OSError:
            pass
        raise SystemExit(0) from None


def _message_to_dict(message: VenueMessage) -> dict[str, Any]:
    return {
        "venue": message.venue,
        "event_type": message.event_type,
        "market_id": message.market_id,
        "asset_id": message.asset_id,
        "timestamp_ms": message.timestamp_ms,
        "received_at_ms": message.received_at_ms,
        "raw_data": message.raw_data,
    }


def _dataclass_to_dict(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    return None


def _parser_for_venue(venue: str) -> Any:
    if venue == "polymarket":
        return parse_polymarket_message
    if venue == "kalshi":
        return parse_kalshi_message
    if venue == "opinion":
        return parse_opinion_message
    raise SystemExit(f"Unsupported venue: {venue}")


def _iter_parsed(parsed: Any) -> Iterable[dict[str, Any]]:
    if parsed is None:
        return []
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    if isinstance(parsed, dict):
        return [parsed]
    return []


def _kalshi_auth_from_env() -> dict[str, str]:
    key_id = os.environ.get("KALSHI_KEY_ID", "").strip()
    signature = os.environ.get("KALSHI_SIGNATURE", "").strip()
    timestamp = os.environ.get("KALSHI_TIMESTAMP", "").strip()
    private_key_path = os.environ.get("KALSHI_PRIVATE_KEY_PATH", "").strip()
    passphrase = os.environ.get("KALSHI_PASSPHRASE", "").strip()

    if key_id and signature and timestamp:
        return {"key_id": key_id, "signature": signature, "timestamp": timestamp}

    if key_id and private_key_path:
        params = {
            "key_id": key_id,
            "private_key_pem": Path(private_key_path).read_text(),
        }
        if passphrase:
            params["passphrase"] = passphrase
        return params

    raise SystemExit(
        "Set KALSHI_KEY_ID plus either KALSHI_SIGNATURE/KALSHI_TIMESTAMP "
        "or KALSHI_PRIVATE_KEY_PATH."
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
