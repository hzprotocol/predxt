# Venues

## Polymarket

Polymarket market websockets are public. Subscribe with asset ids:

```python
from predxt.polymarket import PolymarketWsClient

client = PolymarketWsClient()
await client.connect()
await client.subscribe(["market"], {"assets_ids": ["123"], "initial_dump": True})
```

## Kalshi

Kalshi websockets require signed auth headers. Use either precomputed signature
values or `key_id` plus `private_key_pem`.

```python
from predxt.kalshi import KalshiWsClient

client = KalshiWsClient()
await client.connect({"key_id": "...", "private_key_pem": "..."})
await client.subscribe(["orderbook_snapshot", "orderbook_delta"], {"market_tickers": ["..."]})
```

## Opinion

Opinion websockets require an API key.

```python
from predxt.opinion import OpinionWsClient

client = OpinionWsClient(api_key="...")
await client.connect()
await client.subscribe(["market.depth.diff"], {"market_ids": ["2764"]})
```
