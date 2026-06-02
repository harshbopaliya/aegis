"""
Aegis — AI Safety Gateway for Production Systems.

A pluggable, installable safety control plane that sits between AI agents
and your production infrastructure. Enforces token scoping, policy guardrails,
sandbox simulation, risk scoring, human-in-the-loop approval, controlled
execution, and full observability.

Usage:
    # Quick start
    from aegis import create_app
    app = create_app()

    # With custom backends
    from aegis import create_app
    from aegis.adapters.sqlite import SQLiteStorage
    app = create_app(storage=SQLiteStorage("./data/gateway.db"))

    # SDK client
    from aegis.client import AegisClient
    client = AegisClient("http://localhost:8000", api_key="your-key")
    result = client.submit_action(verb="GET", resource="table:orders", ...)
"""

from __future__ import annotations

__version__ = "2.0.0"
__all__ = [
    "create_app",
    "AegisClient",
    "__version__",
]


def create_app(**kwargs):
    """Create a configured Aegis FastAPI application.

    See :func:`aegis.server.create_app` for full signature.
    """
    from aegis.server import create_app as _create_app

    return _create_app(**kwargs)


def AegisClient(*args, **kwargs):
    """Create an Aegis SDK client.

    See :class:`aegis.client.AegisClient` for full signature.
    """
    from aegis.client import AegisClient as _AegisClient

    return _AegisClient(*args, **kwargs)
