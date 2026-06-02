# FAQ

## Does predxt place orders?

No. It is read-only.

## Is this a replacement for official venue SDKs?

No. Use official SDKs and API docs as venue source of truth. `predxt` focuses on
small, practical websocket ingestion across supported venues.

## Can I use it with coding agents?

Yes. Use `llms.txt`, `llms-full.txt`, and the bundled Codex skill in
`skills/predxt/`.

## Can I add another venue?

Yes, if the contribution is read-only, documented, tested, and keeps raw payload
access available.
