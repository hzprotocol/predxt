# Venues

## Polymarket

Polymarket market websockets are public. Subscribe with asset ids:

```python
from predxt.polymarket import PolymarketWsClient

client = PolymarketWsClient()
await client.connect()
await client.subscribe(["market"], {"assets_ids": ["123"], "initial_dump": True})
```

Polymarket REST market discovery and CLOB orderbook snapshots are public:

```python
from predxt.polymarket import PolymarketRestClient

client = PolymarketRestClient()
markets = await client.search_markets("weather", limit=5)
book = await client.get_orderbook("CLOB_TOKEN_ID")
await client.close()
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

Kalshi REST market-data helpers are read-only:

```python
from predxt.kalshi import KalshiRestClient

client = KalshiRestClient(
    api_key_id="...",
    private_key_pem="...",
)
markets = await client.search_markets("inflation", limit=5)
book = await client.get_orderbook("MARKET-TICKER")
await client.close()
```

## Opinion

Opinion websockets require an API key.

```python
from predxt.opinion import OpinionWsClient

client = OpinionWsClient(api_key="...")
await client.connect()
await client.subscribe(["market.depth.diff"], {"market_ids": ["2764"]})
```

Opinion OpenAPI REST calls require an API key and are read-only:

```python
from predxt.opinion import OpinionRestClient

client = OpinionRestClient(api_key="...")
markets = await client.search_markets("sports", limit=5)
book = await client.get_orderbook("TOKEN_ID")
await client.close()
```
