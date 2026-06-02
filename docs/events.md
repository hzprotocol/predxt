# Normalized Events

`predxt.events` provides dataclasses for common message shapes.

```python
from predxt import typed_event_from_message

event = typed_event_from_message(message)
```

## Event types

- `OrderBookSnapshot`: full bid/ask book levels
- `OrderBookDelta`: one price-level update
- `TradeEvent`: latest trade or trade update
- `PriceChangeEvent`: best bid/ask or price-change payload

## Raw data

All typed events include `raw_data`. Prefer typed fields for common workflows,
but keep `raw_data` for venue-specific fields and forward compatibility.
