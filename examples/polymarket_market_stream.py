from __future__ import annotations

import argparse
import asyncio

from predxt.polymarket import PolymarketWsClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stream Polymarket market messages.")
    parser.add_argument(
        "--asset-id",
        dest="asset_ids",
        action="append",
        required=True,
        help="Polymarket asset id to subscribe to. Repeat for multiple assets.",
    )
    parser.add_argument("--limit", type=int, default=10)
    return parser.parse_args()


async def run(asset_ids: list[str], limit: int) -> None:
    client = PolymarketWsClient()
    await client.connect()
    try:
        await client.subscribe(
            ["market"],
            {
                "assets_ids": asset_ids,
                "initial_dump": True,
            },
        )
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
    asyncio.run(run(args.asset_ids, args.limit))


if __name__ == "__main__":
    main()
