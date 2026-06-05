# predxt

`predxt` is a read-only market-data SDK for prediction market websocket streams
and REST snapshots.

Use it when you need to build:

- live market-data recorders
- orderbook dashboards
- monitoring agents
- research tooling
- read-only market scanners

Do not use it for order placement, execution, account management, or financial
advice.

## Quick install

```bash
pip install predxt
```

## Quick stream

```bash
predxt stream polymarket --asset-id 1234567890 --limit 5 --jsonl
```

## Quick REST snapshot

```python
from predxt.polymarket import PolymarketRestClient

client = PolymarketRestClient()
book = await client.get_orderbook("CLOB_TOKEN_ID")
await client.close()
```

## Core model

Every websocket client emits `VenueMessage`. Convert supported messages into
typed events with `typed_event_from_message`, or apply supported snapshots and
deltas to `OrderBookState`. REST clients expose normalized `MarketSummary`,
`MarketDetail`, `VenueCredentialStatus`, and `OrderBookSnapshot` objects while
retaining raw venue payloads.
