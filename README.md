# predxt

Prediction market websocket clients for Polymarket, Kalshi, and Opinion.

`predxt` is a small Python library for venue websocket ingestion. It exposes
venue-native clients, parsers, connection managers, auth helpers, and basic
health metrics. It does not place trades, manage risk, run an arbitrage scanner,
or provide an Arblense product API.

## Install

```bash
pip install predxt
```

For local development:

```bash
uv sync --group dev
uv run pytest -q
```

## Quickstart

```python
import asyncio

from predxt.polymarket import PolymarketWsClient


async def main() -> None:
    client = PolymarketWsClient()
    await client.connect()
    await client.subscribe(
        ["market"],
        {
            "assets_ids": ["1234567890"],
            "initial_dump": True,
        },
    )

    async for message in client.messages():
        print(message.venue, message.raw_data)


asyncio.run(main())
```

## Supported venues

- Polymarket market websocket with `assets_ids`, `initial_dump`, and
  `custom_feature_enabled` subscription parameters.
- Kalshi websocket with precomputed auth headers or RSA-PSS signing from
  `key_id` and `private_key_pem`.
- Opinion websocket with API key auth and `market_ids` subscriptions.

## Public API

Core exports:

```python
from predxt import BaseWsClient, ExponentialBackoff, HealthMetrics, VenueMessage
```

Venue exports:

```python
from predxt.polymarket import PolymarketWsClient, SubscriptionConfig
from predxt.kalshi import KalshiWsClient, build_kalshi_auth_headers
from predxt.opinion import OpinionWsClient, OpinionSubscriptionConfig
```

`VenueMessage.raw_data` contains normalized venue websocket payloads. The shape
is stable enough for ingestion and tests, but it is not an order execution or
trading schema.

## Examples

The `examples/` directory contains runnable scripts for each venue. Examples use
environment variables for credentials and do not include secrets.

```bash
python examples/polymarket_market_stream.py --asset-id 1234567890
KALSHI_KEY_ID=... KALSHI_PRIVATE_KEY_PATH=... python examples/kalshi_market_stream.py --market TICKER
OPINION_API_KEY=... python examples/opinion_market_stream.py --market-id 2764
```

## Development

```bash
uv sync --group dev
uv run ruff check .
uv run pytest -q
uv build
```

## Release

Releases use SemVer and tags like `v0.1.0`. See
[`docs/releasing.md`](docs/releasing.md).
