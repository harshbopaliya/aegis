"""
Backup & recovery — filesystem copies of the gateway SQLite DB + manifest rows.

Optional AES Fernet encryption of backup files (requires ASG_FERNET_KEY).
"""

from __future__ import annotations

import hashlib
import secrets
import shutil
import sqlite3
import time
from pathlib import Path

from app.config import settings
from app.core.crypto import encrypt_bytes, get_fernet
from app.core.db import connect, init_database


def snapshot(reason: str, request_id: str) -> str:
    init_database()
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

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO backup_manifest (
                id, reason, request_id, created_at, source_db, backup_path,
                encrypted, sha256_hex, size_bytes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snap_id,
                reason,
                request_id,
                time.time(),
                str(src),
                str(dest),
                int(encrypted),
                sha256_hex,
                size,
            ),
        )
        conn.commit()

    return snap_id


def rollback_simulation(snapshot_id: str) -> dict:
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM backup_manifest WHERE id = ?", (snapshot_id,)
        ).fetchone()
    if not row:
        return {"ok": False, "error": "snapshot not found"}
    meta = dict(row)
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
    path = Path(settings.sqlite_path)
    if not path.exists():
        return {"exists": False}
    init_database()
    with sqlite3.connect(path) as conn:
        mirror = conn.execute("SELECT COUNT(*) FROM gateway_mirror").fetchone()[0]
        orders = conn.execute("SELECT COUNT(*) FROM demo_orders").fetchone()[0]
    return {"exists": True, "gateway_mirror_rows": mirror, "demo_orders_rows": orders}


def reset_snapshots() -> None:
    with connect() as conn:
        conn.execute("DELETE FROM backup_manifest")
        conn.commit()
    backup_root = Path(settings.backup_dir)
    if backup_root.is_dir():
        for p in backup_root.glob("snap_*.sqlite*"):
            try:
                p.unlink()
            except OSError:
                pass


def list_snapshots() -> list[dict]:
    init_database()
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM backup_manifest ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]
