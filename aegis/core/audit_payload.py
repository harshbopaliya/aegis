"""
Controls what appears in audit logs / SQLite so operators never see raw production payloads by default.

Modes (ASG_AUDIT_PAYLOAD_MODE):
- full: store JSON as-is (development only).
- redact: strip high-risk keys; hash body-sized content (recommended default for pilots).
- encrypt: Fernet-wrapped JSON (still encrypted at rest; decryption requires ASG_FERNET_KEY on this host).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from aegis.config import settings
from aegis.core.crypto import get_fernet


_REDACT_KEYS = frozenset(
    {
        "payload",
        "body",
        "raw",
        "secret",
        "token",
        "password",
        "credit_card",
        "ssn",
        "pii",
    }
)


def _hash_blob(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def _redact_dict(d: dict[str, Any], depth: int = 0) -> dict[str, Any]:
    if depth > 6:
        return {"_truncated": True}
    out: dict[str, Any] = {}
    for k, v in d.items():
        lk = k.lower()
        if lk in _REDACT_KEYS or "secret" in lk or "password" in lk:
            if isinstance(v, (dict, list)):
                out[k] = {"_redacted": True, "sha256": _hash_blob(v)}
            elif v is None:
                out[k] = None
            else:
                out[k] = {
                    "_redacted": True,
                    "sha256": hashlib.sha256(str(v).encode()).hexdigest(),
                }
        elif isinstance(v, dict):
            out[k] = _redact_dict(v, depth + 1)
        elif isinstance(v, list):
            out[k] = [
                _redact_dict(x, depth + 1) if isinstance(x, dict) else x
                for x in v[:50]
            ]
        else:
            out[k] = v
    return out


def serialize_for_audit(
    event_type: str, payload: dict[str, Any]
) -> tuple[str, int]:
    """
    Returns (stored_json_string, payload_encrypted_flag 0|1 for SQLite).
    """
    mode = (settings.audit_payload_mode or "redact").lower()
    if mode == "full":
        return json.dumps(payload, default=str), 0

    if mode == "redact":
        safe = _redact_dict(dict(payload))
        if event_type == "request_received" and "verb" in safe:
            # Extra: never persist full agent payload in redact mode
            if "payload" in payload and isinstance(payload.get("payload"), dict):
                safe["payload"] = {
                    "_redacted": True,
                    "sha256": _hash_blob(payload["payload"]),
                    "keys": list(payload["payload"].keys())[:20],
                }
        return json.dumps(safe, default=str), 0

    if mode == "encrypt":
        f = get_fernet()
        inner = _redact_dict(dict(payload))
        blob = json.dumps(inner, default=str).encode()
        if f:
            token = f.encrypt(blob).decode()
            return json.dumps({"_enc": True, "v": 1, "blob": token}), 1
        return json.dumps(inner, default=str), 0

    return json.dumps(payload, default=str), 0


def maybe_decrypt_payload_row(stored: str) -> dict[str, Any]:
    """For dashboard: decrypt envelope when allowed and key present."""
    try:
        data = json.loads(stored or "{}")
    except json.JSONDecodeError:
        return {"_parse_error": True}
    if not data.get("_enc"):
        return data
    if not settings.audit_decrypt_allowed:
        return {
            "_encrypted": True,
            "hint": "Set ASG_AUDIT_DECRYPT_ALLOWED=true only on locked-down ops hosts.",
        }
    f = get_fernet()
    if not f:
        return {"_encrypted": True, "hint": "Missing ASG_FERNET_KEY."}
    blob = data.get("blob")
    if not isinstance(blob, str):
        return data
    try:
        clear = f.decrypt(blob.encode()).decode()
        return json.loads(clear)
    except Exception:
        return {"_encrypted": True, "_decrypt_failed": True}
