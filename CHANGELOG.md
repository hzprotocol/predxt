# Changelog

All notable changes to `predxt` are documented here.

## 0.1.0 - Unreleased

- extracted websocket clients, parsers, auth helpers, connection managers, and
  tests from `prediction-platform`
- added Polymarket, Kalshi, and Opinion websocket client support
- added typed `VenueMessage`, typed event dataclasses, `OrderBookState`, and CLI
- made CLI output safe for common pipe consumers such as `head`
- added package metadata, examples, CI, docs, agent docs, and release workflow
  scaffolding
