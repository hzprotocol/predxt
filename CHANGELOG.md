# Changelog

All notable changes to `predxt` are documented here.

## 0.2.1 - 2026-08-26

- fixed Polymarket, Kalshi, and Opinion connection manager shutdown so idle
  websocket streams cannot block `stop()`
- made pre-start and repeated `stop()` calls safe without requiring consumers
  to cancel private message tasks

## 0.2.0 - 2026-06-05

- added read-only REST client base, normalized market/orderbook models, and
  sanitized venue API errors
- added Polymarket, Kalshi, and Opinion REST clients for market search, market
  detail, orderbook snapshots, and API health checks
- kept order placement, balances, positions, and account management out of the
  SDK contract
- documented REST usage and updated agent context for the expanded read-only
  market-data surface

## 0.1.0 - 2026-06-03

- extracted websocket clients, parsers, auth helpers, connection managers, and
  tests from `prediction-platform`
- added Polymarket, Kalshi, and Opinion websocket client support
- added typed `VenueMessage`, typed event dataclasses, `OrderBookState`, and CLI
- made CLI output safe for common pipe consumers such as `head`
- added package metadata, examples, CI, docs, agent docs, and release workflow
  scaffolding
- switched the release workflow to direct PyPI Trusted Publishing gated by the
  `pypi` GitHub environment
