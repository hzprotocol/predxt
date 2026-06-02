from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from predxt.kalshi import KalshiWsClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stream Kalshi market messages.")
    parser.add_argument(
        "--market",
        dest="markets",
        action="append",
        required=True,
        help="Kalshi market ticker. Repeat for multiple markets.",
    )
    parser.add_argument("--limit", type=int, default=10)
    return parser.parse_args()


def auth_params_from_env() -> dict[str, str]:
    key_id = os.environ.get("KALSHI_KEY_ID", "").strip()
    signature = os.environ.get("KALSHI_SIGNATURE", "").strip()
    timestamp = os.environ.get("KALSHI_TIMESTAMP", "").strip()
    private_key_path = os.environ.get("KALSHI_PRIVATE_KEY_PATH", "").strip()
    passphrase = os.environ.get("KALSHI_PASSPHRASE", "").strip()

    if key_id and signature and timestamp:
        return {
            "key_id": key_id,
            "signature": signature,
            "timestamp": timestamp,
        }

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


async def run(markets: list[str], limit: int) -> None:
    client = KalshiWsClient()
    await client.connect(auth_params=auth_params_from_env())
    try:
        await client.subscribe(
            ["orderbook_snapshot", "orderbook_delta"],
            {"market_tickers": markets},
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
    asyncio.run(run(args.markets, args.limit))


if __name__ == "__main__":
    main()
