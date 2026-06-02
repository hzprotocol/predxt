# Agent Prompt Evals

These prompts are lightweight regression fixtures for agent-facing docs. They
describe common tasks that should be solved with supported `predxt` APIs only.

Expected generated code must:

- use `PolymarketWsClient`, `typed_event_from_message`, and/or `OrderBookState`
- keep raw venue payload access available
- stay read-only
- avoid account, wallet, order placement, execution, and trading advice flows

