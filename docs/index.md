# predxt

`predxt` is a read-only realtime ingestion SDK for prediction market websocket
data.

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

## Core model

Every websocket client emits `VenueMessage`. Convert supported messages into
typed events with `typed_event_from_message`, or apply supported snapshots and
deltas to `OrderBookState`.
