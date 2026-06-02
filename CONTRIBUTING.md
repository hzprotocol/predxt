# Contributing

Thanks for improving `predxt`.

## Local Setup

```bash
uv sync --group dev
uv run pytest -q -s
```

## Pull Requests

- Keep the SDK read-only.
- Add or update tests for parser, event, orderbook, CLI, and docs behavior.
- Update `README.md`, `docs/`, and `llms.txt` for public API changes.
- Do not include secrets or live account data.

## Validation

```bash
uv run ruff check .
uv run mypy
uv run pytest -q -s
uv build
uv run twine check dist/*
```
