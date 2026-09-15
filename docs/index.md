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
pip install "predxt>=0.3.0"
```

## First orderbook

These commands require Python 3.12 or later and predxt 0.3.0 or later.

```bash
predxt demo
predxt explore polymarket --query "bitcoin"
```

`demo` shows a labelled synthetic orderbook with no network access. `explore`
lets you select a real market and outcome, shows a REST snapshot, then prints
a WebSocket command with the selected token ID already filled in.

Read the [first-run guide](first-run.md) for expected output and error handling.

## Core model

Every websocket client emits `VenueMessage`. Convert supported messages into
typed events with `typed_event_from_message`, or apply supported snapshots and
deltas to `OrderBookState`. REST clients expose normalized `MarketSummary`,
`MarketDetail`, `VenueCredentialStatus`, and `OrderBookSnapshot` objects while
retaining raw venue payloads.
