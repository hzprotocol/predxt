# Security

`predxt` is read-only, but venue credentials still matter for authenticated
websocket streams and REST market-data APIs.

- Store credentials in environment variables or a secret manager.
- Never commit Kalshi private keys, signatures, Opinion API keys, or account identifiers.
- Do not paste secrets into GitHub issues, agent prompts, or examples.
- Report vulnerabilities privately using `security@hzprotocol.com`.

`predxt` never includes request headers or request bodies in `VenueApiError`
messages. Venue response text may still contain venue-provided details, so keep
production logs private.

`predxt` does not bypass venue access controls or geographic restrictions.
