# Eval: Dashboard Stream Health

Build a minimal dashboard backend that exposes stream health, latest event, and
current orderbook state for a read-only prediction-market monitor.

Expected APIs:

- `OrderBookState`
- `VenueMessage`
- `typed_event_from_message`
- public websocket clients from `predxt.polymarket`, `predxt.kalshi`, or
  `predxt.opinion`

Constraints:

- live venue checks may be manual and gated by credentials
- CI should use offline fixtures
- no trading, account, or execution API should be generated

