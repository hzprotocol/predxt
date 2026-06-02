# Eval: Polymarket Orderbook Recorder

Build a Python CLI that subscribes to one public Polymarket asset id, records
JSONL messages, and prints best bid/ask while it runs.

Expected APIs:

- `from predxt.polymarket import PolymarketWsClient`
- `from predxt import OrderBookState, typed_event_from_message`
- `await client.subscribe(["market"], {"assets_ids": [asset_id], "initial_dump": True})`

Constraints:

- read-only market-data ingestion only
- no order placement or account management
- no financial advice

