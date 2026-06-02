"""
API Key authentication for the Aegis gateway.

Supports role-based API keys:
- admin: full access to all endpoints
- operator: can approve/reject actions, view dashboard
- agent: can submit actions only

Keys are validated via X-API-Key header or Authorization: Bearer <key>.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from aegis.config import settings

logger = logging.getLogger(__name__)

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _hash_key(key: str) -> str:
    """Hash an API key for safe storage."""
    return hashlib.sha256(key.encode()).hexdigest()


def _parse_configured_keys() -> dict[str, str]:
    """Parse API keys from settings.

    Format: ``role:key,role:key`` or ``key`` (defaults to admin).
    Returns {key_hash: role}.
    """
    raw = settings.api_keys
    if not raw:
        return {}
    keys: dict[str, str] = {}
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if ":" in entry:
            role, key = entry.split(":", 1)
            keys[_hash_key(key.strip())] = role.strip().lower()
        else:
            keys[_hash_key(entry)] = "admin"
    return keys


def generate_api_key(role: str = "admin") -> tuple[str, str]:
    """Generate a new API key. Returns (raw_key, key_hash)."""
    raw = f"aegis_{role}_{secrets.token_urlsafe(32)}"
    return raw, _hash_key(raw)


async def get_api_key(
    request: Request,
    api_key: Optional[str] = Security(_api_key_header),
) -> Optional[str]:
    """Extract API key from request headers.

    Checks X-API-Key header first, then Authorization: Bearer.
    """
    if api_key:
        return api_key

    # Fallback to Authorization header
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()

    return None


def _validate_key(api_key: str | None, required_roles: set[str]) -> str:
    """Validate an API key and check role. Returns the role."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTHENTICATION_ERROR",
                "message": "API key required. Pass via X-API-Key header or Authorization: Bearer <key>.",
            },
        )

    key_hash = _hash_key(api_key)
    configured_keys = _parse_configured_keys()

    if key_hash not in configured_keys:
        logger.warning("Invalid API key attempt", extra={"key_prefix": api_key[:8] + "..."})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTHENTICATION_ERROR",
                "message": "Invalid API key.",
            },
        )

    role = configured_keys[key_hash]
    if required_roles and role not in required_roles:
        logger.warning(
            "Insufficient permissions",
            extra={"role": role, "required": list(required_roles)},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "AUTHORIZATION_ERROR",
                "message": f"Role '{role}' does not have access. Required: {required_roles}",
            },
        )

    return role


def require_auth(*roles: str):
    """Dependency that requires authentication with optional role check.

    Usage::

        @app.get("/protected")
        async def protected(role=Depends(require_auth("admin", "operator"))):
            ...

    If ``ASG_REQUIRE_AUTH=false``, this is a no-op (returns 'anonymous').
    """

    async def _check(api_key: Optional[str] = Depends(get_api_key)) -> str:
        if not settings.require_auth:
            return "anonymous"
        required_roles = set(roles) if roles else set()
        # admin always has access
        required_roles.add("admin")
        return _validate_key(api_key, required_roles)

    return _check


# Convenience dependencies
require_admin = require_auth("admin")
require_operator = require_auth("admin", "operator")
require_agent_or_above = require_auth("admin", "operator", "agent")
