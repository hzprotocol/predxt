# Orderbook Helper

`OrderBookState` applies supported snapshots and deltas.

```python
from predxt import OrderBookState

state = OrderBookState()
state.apply(message)

print(state.best_bid, state.best_ask)
print(state.snapshot(depth=5))
```

The helper is intentionally small. It is suitable for dashboards, local
recorders, demos, and monitoring agents. It is not an execution-grade book.
