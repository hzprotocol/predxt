from __future__ import annotations

import argparse
import asyncio
import os

from predxt.opinion import OpinionWsClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stream Opinion market messages.")
    parser.add_argument(
        "--market-id",
        dest="market_ids",
        action="append",
        required=True,
        help="Opinion market id. Repeat for multiple markets.",
    )
    parser.add_argument("--limit", type=int, default=10)
    return parser.parse_args()


def api_key_from_env() -> str:
    api_key = os.environ.get("OPINION_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("Set OPINION_API_KEY.")
    return api_key


async def run(market_ids: list[str], limit: int) -> None:
    client = OpinionWsClient(api_key=api_key_from_env())
    await client.connect()
    try:
        await client.subscribe(["market.depth.diff"], {"market_ids": market_ids})
        seen = 0
        async for message in client.messages():
            print(message.raw_data)
            seen += 1
            if seen >= limit:
                return
    finally:
        await client.close()


def main() -> None:
    args = parse_args()
    asyncio.run(run(args.market_ids, args.limit))


if __name__ == "__main__":
    main()
