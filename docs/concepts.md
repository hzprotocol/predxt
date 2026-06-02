# Concepts

## Read-only ingestion

`predxt` opens venue websocket connections, subscribes to supported channels,
parses venue payloads, and emits normalized messages. It does not trade.

## VenueMessage

`VenueMessage` is the compatibility surface for all clients:

- `venue`
- `raw_data`
- `timestamp_ms`
- `event_type`
- `market_id`
- `asset_id`
- `received_at_ms`

`raw_data` is always retained so builders can access venue-specific fields.

## Typed events

Use `typed_event_from_message(message)` to get dataclasses for supported shapes:

- `OrderBookSnapshot`
- `OrderBookDelta`
- `TradeEvent`
- `PriceChangeEvent`

Unsupported messages return `None`.
