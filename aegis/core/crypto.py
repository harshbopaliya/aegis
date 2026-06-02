"""Fernet encryption helpers for audit payload and backup encryption."""

from __future__ import annotations

from typing import Optional

from aegis.config import settings

_fernet_instance = None


def get_fernet():
    """Return a cached Fernet instance or None if no key is configured."""
    global _fernet_instance
    if _fernet_instance is not None:
        return _fernet_instance
    key = settings.fernet_key
    if not key:
        return None
    try:
        from cryptography.fernet import Fernet

        _fernet_instance = Fernet(key.encode() if isinstance(key, str) else key)
        return _fernet_instance
    except Exception:
        return None


def encrypt_bytes(data: bytes) -> bytes:
    """Encrypt bytes using the configured Fernet key."""
    f = get_fernet()
    if f is None:
        raise RuntimeError("No Fernet key configured (ASG_FERNET_KEY)")
    return f.encrypt(data)


def decrypt_bytes(token: bytes) -> bytes:
    """Decrypt Fernet-encrypted bytes."""
    f = get_fernet()
    if f is None:
        raise RuntimeError("No Fernet key configured (ASG_FERNET_KEY)")
    return f.decrypt(token)
