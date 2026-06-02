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
