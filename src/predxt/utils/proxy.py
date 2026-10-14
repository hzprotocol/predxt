"""Translate the optional WebSocket SOCKS dependency error without retrying."""

import time

from predxt.base import HealthMetrics


class SocksDependencyError(ImportError):
    """The selected SOCKS proxy requires the optional python-socks package."""


def _raise_missing_socks_dependency(exc: Exception, health: HealthMetrics) -> None:
    # websockets raises this ImportError before opening the proxy connection.
    # Match its specific diagnostic; other errors retain the existing retry policy.
    if not isinstance(exc, ImportError) or str(exc) != (
        "connecting through a SOCKS proxy requires python-socks"
    ):
        return

    error = SocksDependencyError(
        "WebSocket SOCKS proxy support is missing. In the Python environment "
        'running predxt, install: python -m pip install "python-socks[asyncio]". '
        "Then restart the process."
    )
    health.last_error = str(error)
    health.last_error_timestamp_ms = time.time() * 1000
    raise error from exc
