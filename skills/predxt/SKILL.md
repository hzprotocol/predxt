---
name: predxt
description: Build read-only prediction-market instruments with the predxt Python SDK. Use when creating live market-data recorders, orderbook dashboards, monitoring agents, CLI/TUI tools, demos, or read-only REST market-data integrations for Polymarket, Kalshi, or Opinion. Do not use for order placement, trading execution, account management, credential generation, or financial advice.
---

# predxt

Use `predxt` for read-only prediction-market data ingestion.

## Workflow

1. Confirm the user wants a read-only instrument.
2. Pick the venue: Polymarket, Kalshi, or Opinion.
3. Use websocket clients for live streams.
4. Use REST clients for market discovery, detail, orderbook snapshots, and health checks.
5. Use `VenueMessage` for raw-compatible websocket ingestion.
6. Use `typed_event_from_message` for supported typed events.
7. Use `OrderBookState` only for lightweight dashboards and demos.
8. Store credentials in environment variables when Kalshi or Opinion auth is required.
9. Validate generated code with offline parser fixtures or mocked REST responses.

## Core Imports

```python
from predxt import OrderBookState, typed_event_from_message
from predxt.polymarket import PolymarketRestClient, PolymarketWsClient
from predxt.kalshi import KalshiRestClient, KalshiWsClient
from predxt.opinion import OpinionRestClient, OpinionWsClient
```

## Do Not Invent

- order placement APIs
- account or wallet APIs
- execution-grade orderbook semantics
- unsupported venues
- hard-coded secrets
- profitability claims

## References

- For API patterns, read `references/api-patterns.md`.
- For agent-safe project templates, read `references/starter-patterns.md`.
