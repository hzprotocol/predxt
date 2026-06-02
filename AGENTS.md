# AGENTS

This repository is public-facing. Optimize for clear, release-ready SDK changes.

## Product Boundary

- `predxt` is a read-only realtime ingestion SDK for prediction-market websocket data.
- Do not add order placement, execution, account management, trading advice, or secret-handling shortcuts.
- Keep raw venue payload access available even when adding typed helpers.
- Prefer additive API changes until a planned major version.

## First Files To Read

- `README.md`
- `pyproject.toml`
- `docs/index.md`
- `llms.txt`
- `git status --short --branch`

## Validation

```bash
uv sync --group dev
uv run ruff check .
uv run mypy
uv run pytest -q -s
uv build
uv run twine check dist/*
```

## Agent Rules

- Never invent unsupported venues, auth schemes, or trading APIs.
- Do not paste real API keys, signatures, private keys, or account identifiers into docs or tests.
- Keep examples runnable without secrets unless the venue requires auth; then fail with a clear env-var message.
- Update `llms.txt` and `docs/` when public APIs change.
