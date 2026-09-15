# CLI

## First run (development version)

Install this checkout with `pip install .`; the new commands are not in PyPI 0.2.2.

```bash
predxt demo
predxt demo --json
predxt explore polymarket --query "bitcoin"
```

`demo` is synthetic and never connects to a venue. `explore` asks you to select
a market and outcome, displays one REST snapshot, and prints a WebSocket command.
Use `--market-id ID --outcome-index N --json` for noninteractive selection.
`--timeout` sets the deadline for each API request (10 seconds by default).
See [Your first orderbook](first-run.md).

## Parse offline fixtures

This command uses a fixture from the repository checkout:

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
