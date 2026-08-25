# Reconnects and Health

Clients expose `health()`:

- `connected`
- `last_message_timestamp_ms`
- `reconnect_count`
- `messages_received`
- `messages_sent`
- `last_error`
- `last_error_timestamp_ms`
- `uptime_seconds`

Connection retry behavior uses exponential backoff with jitter. Live systems
should monitor `last_message_timestamp_ms`, reconnect counts, and process-level
logs.

## Connection manager shutdown

Polymarket, Kalshi, and Opinion connection managers own their background
message reader. Always shut a manager down through its public lifecycle:

```python
await manager.start()
try:
    ...
finally:
    await manager.stop()
```

`stop()` cancels and awaits the message reader before closing the websocket
client, so it completes even when the stream is idle. Calling `stop()` before
`start()` or more than once is safe. Consumers should not inspect or cancel
private task attributes.
