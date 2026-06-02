# Starter Patterns

## Recorder

- Accept venue and market identifiers from CLI args.
- Emit JSONL with one record per `VenueMessage`.
- Include `raw_data` and typed event output when available.
- Handle Ctrl-C and close websocket clients.

## TUI

- Use `OrderBookState` for best-effort book display.
- Show connection health and reconnect count.
- Include JSONL recording as an optional flag.
- Never request trading credentials.

## Web dashboard

- Keep websocket ingestion server-side.
- Broadcast normalized read-only events to the browser.
- Show venue, event type, latest message time, and best bid/ask.
- Avoid account, portfolio, or order placement UI.

## Agent monitor

- Expose read-only tools such as `stream_market`, `latest_book`, and `record_jsonl`.
- Make tool descriptions explicit that they do not trade.
- Read credentials only from environment variables.
