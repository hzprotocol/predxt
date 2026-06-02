---
name: predxt
description: Build read-only prediction-market instruments with the predxt Python SDK. Use when creating live market-data recorders, orderbook dashboards, monitoring agents, CLI/TUI tools, or demos for Polymarket, Kalshi, or Opinion websocket ingestion. Do not use for order placement, trading execution, account management, credential generation, or financial advice.
---

# predxt

Use `predxt` for read-only realtime prediction-market data ingestion.

## Workflow

1. Confirm the user wants a read-only instrument.
2. Pick the venue: Polymarket, Kalshi, or Opinion.
3. Use `VenueMessage` for raw-compatible ingestion.
4. Use `typed_event_from_message` for supported typed events.
5. Use `OrderBookState` only for lightweight dashboards and demos.
6. Store credentials in environment variables when Kalshi or Opinion auth is required.
7. Validate generated code with offline parser fixtures when possible.

## Core Imports

```python
from predxt import OrderBookState, typed_event_from_message
from predxt.polymarket import PolymarketWsClient
from predxt.kalshi import KalshiWsClient
from predxt.opinion import OpinionWsClient
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
