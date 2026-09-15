# Your first orderbook

The commands below are in development and are not part of PyPI 0.2.2 yet.
With Python 3.12 or later, install a checkout containing this guide:

```bash
pip install .
```

## 1. See a result without credentials or network

```bash
predxt demo
```

This displays a **synthetic** two-sided book. Its best bid is 0.42, best ask is
0.44, and spread is 0.02. These are example values, not market quotes. The demo
is included in the installed package and works outside the repository.

To inspect the structured output:

```bash
predxt demo --json
```

The output includes `synthetic: true`, the book, and best bid/ask. No network
client is created, and no source-checkout fixture is required.

## 2. Find a real market

```bash
predxt explore polymarket --query "bitcoin"
```

In an interactive terminal, the command:

1. Searches Polymarket's public Gamma API and lists up to ten open orderbook markets.
2. Asks for the market number you want to inspect.
3. Fetches current details and asks for an outcome number.
4. Uses that outcome's token ID to fetch its CLOB orderbook.
5. Prints the top five bid/ask levels and a command for streaming WebSocket events.

The display is one REST snapshot, not a continuously updating monitor. The fetch
time is measured locally when the response arrives; it is not a guarantee that
the venue's quote is fresh. An empty or one-sided book is shown explicitly.

The printed `predxt stream` command includes the chosen token ID. Copy it to
receive normalized events and raw payloads. It stops after five messages;
an inactive stream may wait, so use Ctrl-C to stop it manually.

## 3. Use the result in a script

The selection menus go to stderr. Pass a Gamma market ID from the search results
and a **1-based** outcome index to skip interactive prompts:

```bash
predxt explore polymarket --market-id "$MARKET_ID" --outcome-index 1 --json
```

Set `MARKET_ID` to the market you selected. The JSON response includes
`synthetic: false`, the market title, outcome label, normalized snapshot,
best bid/ask, and the snapshot's original `raw_data`. It emits one JSON document
on stdout. Inspect outcome labels in the interactive view before selecting by index.

Gamma market IDs identify questions; CLOB token IDs identify the individual
outcomes whose orderbooks you read. The CLI handles that distinction for you.

## Network and selection errors

- Each API request has a wall-clock deadline, defaulting to 10 seconds. Change it
  with `--timeout 5`. Human selection time is separate from request timeouts.
- Empty results: try a different query. The command reads the first search page;
  it does not crawl the whole catalog or guarantee exhaustive results.
- Closed markets or incomplete outcome identifiers: select a different market.
  Details are checked again after selection because market status can change.
- HTTP 403 or other API errors: check venue availability. The command exits with
  an error and suggests `predxt demo`; it never substitutes synthetic output for
  a live result automatically.
- Without a terminal, the search prints market IDs and explains how to pass
  `--market-id` and `--outcome-index`. It does not guess your selections.

Success returns exit code 0, API/selection errors return 1, invalid command-line
arguments return 2, and interrupting the interactive flow returns 130.

## Python search

`PolymarketRestClient.search_markets(query, limit=20, active_only=False)` uses
Gamma's documented `/public-search` endpoint for non-empty queries, flattens
the nested event markets, and removes duplicate market IDs. `active_only=True`
requests active results and filters out closed or unconfirmed-active rows.
An empty query lists markets through `/markets`. `limit` must be positive.

Responses retain the existing `MarketSummary` model and each raw market row.
Use `get_market(market_id)` for outcome labels and token IDs, then
`get_orderbook(token_id)` for that outcome's snapshot.

Source: [Polymarket search API](https://docs.polymarket.com/api-reference/search/search-markets-events-and-profiles).
