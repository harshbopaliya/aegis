"""Symmetric encryption helpers for audit storage and encrypted backups (optional)."""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

_fernet: Fernet | None = None


def get_fernet() -> Fernet | None:
    """Returns Fernet instance when ASG_FERNET_KEY is set (url-safe base64 32-byte key)."""
    global _fernet
    key = settings.fernet_key
    if not key:
        return None
    if _fernet is None:
        _fernet = Fernet(key.strip().encode() if isinstance(key, str) else key)
    return _fernet


def encrypt_bytes(data: bytes) -> bytes:
    f = get_fernet()
    if not f:
        raise RuntimeError("Encryption requested but ASG_FERNET_KEY is not configured.")
    return f.encrypt(data)


def decrypt_bytes(token: bytes) -> bytes:
    f = get_fernet()
    if not f:
        raise RuntimeError("Decryption requested but ASG_FERNET_KEY is not configured.")
    return f.decrypt(token)


def decrypt_token_safe(token_b64: str) -> bytes | None:
    try:
        return decrypt_bytes(token_b64.encode())
    except (InvalidToken, ValueError):
        return None


def generate_key_b64() -> str:
    """Run once in a secure environment; store in ASG_FERNET_KEY."""
    return Fernet.generate_key().decode()
