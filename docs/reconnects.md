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

## SOCKS proxy setup

When `websockets` selects a SOCKS proxy from your operating system or environment,
it needs the optional `python-socks` package. Install it in the Python environment
that runs predxt:

```bash
python -m pip install "python-socks[asyncio]"
```

Restart the Python process after installation because `websockets` checks this
dependency when its module is imported. predxt preserves the existing proxy
selection; it does not disable or bypass your proxy.

If the dependency is missing, Polymarket, Kalshi, and Opinion immediately raise
`predxt.SocksDependencyError` (an `ImportError`) with the installation command.
The error is recorded in `health().last_error` with a timestamp. There is no
retry wait for this setup error, including when `messages()` opens a connection.
`predxt stream` prints the message to stderr and exits with code 1 without a
traceback or JSON output. Transient connection errors keep their existing
backoff behavior.

This optional package supports WebSocket SOCKS connections; it is not required
for `predxt demo` or a direct WebSocket connection. REST clients use a separate
HTTP transport.

Source: [websockets proxy documentation](https://websockets.readthedocs.io/en/stable/topics/proxies.html).

## Graceful stream endings

Polymarket, Kalshi, and Opinion recover when the remote websocket iterator
ends normally as well as when it raises a connection error. Each disconnect
sets `connected` to false, increments `reconnect_count` once, and waits for
backoff before reconnecting and restoring the saved subscription. Opinion
stops its old heartbeat before waiting and starts a new one after connecting.
A completed socket is never repeatedly read without a retry delay.

`close()` marks the client stopped before closing the socket and interrupts
pending retry waits. Cancelling the message reader or calling `aclose()` on
its iterator releases the connection and heartbeat without reconnecting.
Repeated `close()` calls are safe, including before the first connection.
After closing, call `connect()` explicitly to start a new session.

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
