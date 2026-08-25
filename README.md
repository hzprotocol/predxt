# predxt

[![CI](https://github.com/hzprotocol/predxt/actions/workflows/ci.yml/badge.svg)](https://github.com/hzprotocol/predxt/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/predxt.svg)](https://pypi.org/project/predxt/)
[![Python](https://img.shields.io/pypi/pyversions/predxt.svg)](https://pypi.org/project/predxt/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Read-only market-data ingestion for prediction market builders.

`predxt` streams websocket data and reads REST market-data snapshots from
Polymarket, Kalshi, and Opinion. It is built for dashboards, recorders, research
tools, monitoring agents, market scanners, and orderbook visualizations. It is
not a trading, execution, account, or financial-advice library.

## Install

```bash
pip install predxt
```

For local development:

```bash
uv sync --group dev
uv run pytest -q -s
```

## 60-second Polymarket demo

Polymarket market websockets are public. Use any valid Polymarket CLOB asset id:

```bash
predxt stream polymarket --asset-id 1234567890 --limit 5 --jsonl
```

Or from Python:

```python
import asyncio

from predxt.polymarket import PolymarketWsClient


async def main() -> None:
    client = PolymarketWsClient()
    await client.connect()
    await client.subscribe(
        ["market"],
        {"assets_ids": ["1234567890"], "initial_dump": True},
    )

    async for message in client.messages():
        print(message.event_type, message.asset_id, message.raw_data)
        break

    await client.close()


asyncio.run(main())
```

## Venue matrix

| Venue | Public stream | REST market data | Auth | Current support |
| --- | --- | --- | --- | --- |
| Polymarket | Yes | Yes | None for public market data | books, price changes, trades, market search/detail, orderbook snapshots |
| Kalshi | No | Yes | signed headers for authenticated paths | orderbook snapshots/deltas, market search/detail, orderbook snapshots |
| Opinion | No | Yes | API key | depth diffs, last price/trade, market list/detail, orderbook snapshots |

## API contract

Core imports:

```python
from predxt import (
    OrderBookState,
    VenueMessage,
    typed_event_from_message,
)
```

Venue imports:

```python
from predxt.polymarket import (
    PolymarketRestClient,
    PolymarketSubscriptionConfig,
    PolymarketWsClient,
)
from predxt.kalshi import (
    KalshiRestClient,
    KalshiWsClient,
    build_kalshi_auth_headers,
)
from predxt.opinion import (
    OpinionRestClient,
    OpinionSubscriptionConfig,
    OpinionWsClient,
)
```

Every client emits `VenueMessage` objects with:

- `venue`
- `event_type`
- `market_id`
- `asset_id`
- `timestamp_ms`
- `received_at_ms`
- `raw_data`

Use `typed_event_from_message(message)` when you want dataclass events such as
`OrderBookSnapshot`, `OrderBookDelta`, `TradeEvent`, or `PriceChangeEvent`.
Use `OrderBookState` when you need a small in-memory orderbook helper.

REST clients expose read-only market-data methods:

```python
from predxt.polymarket import PolymarketRestClient

client = PolymarketRestClient()
markets = await client.search_markets("weather", limit=5)
book = await client.get_orderbook("CLOB_TOKEN_ID")
await client.close()
```

Connection managers own their background websocket reader. Use their public
`start()` and `stop()` methods for lifecycle management; `stop()` also handles
idle streams and is safe to call before `start()` or more than once. Consumers
do not need to access private task attributes.

## CLI

Offline parser demo:

```bash
predxt parse-fixture --venue polymarket --jsonl tests/fixtures/polymarket_order_books.json
```

Live streams:

```bash
predxt stream polymarket --asset-id 1234567890 --limit 10 --jsonl
KALSHI_KEY_ID=... KALSHI_PRIVATE_KEY_PATH=... predxt stream kalshi --market MARKET-TICKER
OPINION_API_KEY=... predxt stream opinion --market-id 2764
```

## Examples

This repository keeps minimal examples in `examples/`. Public showcase starters:

- [`hzprotocol/predxt-orderbook-tui`](https://github.com/hzprotocol/predxt-orderbook-tui)
  - terminal orderbook monitor
- [`hzprotocol/predxt-web-dashboard`](https://github.com/hzprotocol/predxt-web-dashboard)
  - FastAPI + React dashboard
- [`hzprotocol/predxt-agent-market-monitor`](https://github.com/hzprotocol/predxt-agent-market-monitor)
  - read-only agent/MCP starter

## What this is not

`predxt` does not place orders, derive trading credentials, manage positions,
execute strategies, bypass venue restrictions, or provide financial advice. It
is a read-only market-data SDK. Keep credentials in environment variables or a
secret manager; never hard-code them in examples or agent prompts.

## Documentation

- Docs site: <https://hzprotocol.github.io/predxt>
- AI context: [`llms.txt`](llms.txt), [`llms-full.txt`](llms-full.txt)
- Codex skill: [`skills/predxt/SKILL.md`](skills/predxt/SKILL.md)

## Development

```bash
uv sync --group dev
uv run ruff check .
uv run mypy
uv run pytest -q -s
uv build
uv run twine check dist/*
```

## Release

Releases use SemVer and tags like `v0.1.0`. See
[`docs/releasing.md`](docs/releasing.md).
