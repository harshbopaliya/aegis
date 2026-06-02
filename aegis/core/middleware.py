"""
Production-grade middleware for security, rate limiting, and request tracking.
"""

from __future__ import annotations

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from aegis.config import settings
from aegis.core.logging_config import RequestContextLogger, get_logger

logger = get_logger(__name__)


class RequestIdMiddleware:
    """Add X-Request-ID header to all requests and responses."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = scope.get("headers", [])
        request_id = next(
            (
                value.decode()
                for name, value in request_id
                if name == b"x-request-id"
            ),
            str(uuid.uuid4()),
        )

        scope["request_id"] = request_id

        async def send_with_header(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_header)


class RequestLoggingMiddleware:
    """Log all HTTP requests and responses with timing."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = scope.get("request_id", "unknown")
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")
        client = scope.get("client")
        client_host = client[0] if client else "unknown"

        start_time = time.time()
        status_code = 200

        async def send_with_logging(message: dict) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_with_logging)
        except Exception as e:
            status_code = 500
            logger.error(
                f"Request failed: {method} {path}",
                extra={
                    "request_id": request_id,
                    "status": status_code,
                    "error": str(e),
                },
            )
            raise
        finally:
            duration = time.time() - start_time
            logger.info(
                f"{method} {path}",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "status": status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "client_host": client_host,
                },
            )


class SecurityHeadersMiddleware:
    """Add security headers to all responses."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                # Security headers
                headers.extend(
                    [
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY"),
                        (b"x-xss-protection", b"1; mode=block"),
                        (
                            b"strict-transport-security",
                            b"max-age=31536000; includeSubDomains",
                        ),
                        (
                            b"content-security-policy",
                            b"default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'",
                        ),
                    ]
                )
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


def setup_cors(app: ASGIApp) -> ASGIApp:
    """Configure CORS for production deployment."""
    allowed_origins = (
        settings.allowed_origins.split(",")
        if settings.allowed_origins
        else ["http://localhost:3000"]
    )

    return CORSMiddleware(
        app,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        max_age=600,
    )


def setup_trusted_host(app: ASGIApp) -> ASGIApp:
    """Configure trusted host middleware for security."""
    trusted_hosts = (
        settings.trusted_hosts.split(",")
        if settings.trusted_hosts
        else ["localhost", "127.0.0.1"]
    )

    return TrustedHostMiddleware(
        app,
        allowed_hosts=trusted_hosts,
    )


async def add_request_tracking(request: Request) -> tuple[str, str | None]:
    """Extract or create request ID and actor ID from request."""
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    actor_id = request.headers.get("x-actor-id")
    return request_id, actor_id
