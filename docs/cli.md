# CLI

## Parse offline fixtures

```bash
predxt parse-fixture --venue polymarket --jsonl tests/fixtures/polymarket_order_books.json
```

## Stream live data

```bash
predxt stream polymarket --asset-id 1234567890 --limit 10 --jsonl
KALSHI_KEY_ID=... KALSHI_PRIVATE_KEY_PATH=... predxt stream kalshi --market MARKET
OPINION_API_KEY=... predxt stream opinion --market-id 2764
```

The CLI emits `VenueMessage` and typed event payloads. It never places orders.
