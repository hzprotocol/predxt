# Eval: Offline Fixture Parser

Build a small read-only offline parser demo that reads a Polymarket fixture
file and prints normalized typed events.

Expected APIs:

- `predxt parse-fixture ... --venue polymarket --jsonl`, or
- `from predxt.polymarket.parser import parse_message`
- `from predxt import build_venue_message, typed_event_from_message`

Constraints:

- no websocket connection required
- preserve raw payload fields for unsupported data
- do not invent venue fields that are not in the fixture
- no order placement, execution, or account management
