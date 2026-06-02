# API Patterns

## Public Polymarket stream

```python
from predxt.polymarket import PolymarketWsClient

client = PolymarketWsClient()
await client.connect()
await client.subscribe(["market"], {"assets_ids": ["..."], "initial_dump": True})
async for message in client.messages():
    ...
```

## Typed events

```python
from predxt import typed_event_from_message

event = typed_event_from_message(message)
if event is not None:
    print(event.event_type, event.raw_data)
```

## Orderbook helper

```python
from predxt import OrderBookState

state = OrderBookState()
state.apply(message)
print(state.best_bid, state.best_ask)
```

## CLI

```bash
predxt parse-fixture --venue polymarket --jsonl tests/fixtures/polymarket_order_books.json
predxt stream polymarket --asset-id 1234567890 --limit 10 --jsonl
```

## Auth

- Polymarket market stream: no auth.
- Kalshi: `KALSHI_KEY_ID` plus signed headers or `KALSHI_PRIVATE_KEY_PATH`.
- Opinion: `OPINION_API_KEY`.
