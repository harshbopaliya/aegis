"""
Backup & recovery — filesystem copies of the gateway SQLite DB + manifest rows.

Optional AES Fernet encryption of backup files (requires ASG_FERNET_KEY).
"""

from __future__ import annotations

import hashlib
import secrets
import shutil
import time
from pathlib import Path

from aegis.adapters import get_storage
from aegis.config import settings
from aegis.core.crypto import encrypt_bytes, get_fernet


def snapshot(reason: str, request_id: str) -> str:
    get_storage().init()
    snap_id = f"snap_{secrets.token_hex(8)}"
    src = Path(settings.sqlite_path)
    backup_root = Path(settings.backup_dir)
    backup_root.mkdir(parents=True, exist_ok=True)

    if src.exists():
        data = src.read_bytes()
    else:
        data = b""

    sha256_hex = hashlib.sha256(data).hexdigest()
    encrypt = bool(settings.encrypt_backup_files) and get_fernet() is not None

    if encrypt:
        blob = encrypt_bytes(data)
        dest = backup_root / f"{snap_id}.sqlite.enc"
        dest.write_bytes(blob)
        encrypted = True
    else:
        dest = backup_root / f"{snap_id}.sqlite"
        if data:
            shutil.copy2(src, dest)
        else:
            dest.write_bytes(b"")
        encrypted = False

    size = dest.stat().st_size if dest.exists() else 0

    get_storage().store_backup_snapshot(
        snap_id=snap_id,
        reason=reason,
        request_id=request_id,
        created_at=time.time(),
        source_db=str(src),
        backup_path=str(dest),
        encrypted=int(encrypted),
        sha256_hex=sha256_hex,
        size_bytes=size,
    )

    return snap_id


def rollback_simulation(snapshot_id: str) -> dict:
    meta = get_storage().get_backup_snapshot(snapshot_id)
    if not meta:
        return {"ok": False, "error": "snapshot not found"}
    return {
        "ok": True,
        "snapshot_id": snapshot_id,
        "plan": [
            "detach application traffic",
            f"restore database file from {meta.get('backup_path')}",
            "if encrypted, decrypt with ASG_FERNET_KEY on a trusted host",
            "replay audit-forwarding since snapshot if incremental backups enabled",
            "verify integrity checksums",
            "gradual traffic ramp",
        ],
        "metadata": meta,
    }


def export_db_summary() -> dict:
    get_storage().init()
    try:
        mirror = get_storage().get_gateway_mirror_count()
        orders = get_storage().get_demo_orders_count()
        return {
            "exists": True,
            "gateway_mirror_rows": mirror,
            "demo_orders_rows": orders,
        }
    except Exception:
        return {"exists": False}


def reset_snapshots() -> None:
    get_storage().clear_snapshots()
    backup_root = Path(settings.backup_dir)
    if backup_root.is_dir():
        for p in backup_root.glob("snap_*.sqlite*"):
            try:
                p.unlink()
            except OSError:
                pass


def list_snapshots() -> list[dict]:
    get_storage().init()
    return get_storage().list_snapshots()
