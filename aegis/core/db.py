"""Central SQLite schema creation and lightweight migrations."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from aegis.config import settings


def db_path() -> Path:
    return Path(settings.sqlite_path)


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {r[1] for r in rows}


def init_database() -> None:
    """Idempotent: creates tables used across modules."""
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS gateway_mirror (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                env TEXT NOT NULL,
                resource TEXT NOT NULL,
                verb TEXT NOT NULL,
                payload TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS demo_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                event_type TEXT NOT NULL,
                request_id TEXT NOT NULL,
                actor_id TEXT,
                payload TEXT NOT NULL DEFAULT '{}',
                payload_encrypted INTEGER NOT NULL DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_audit_events_request ON audit_events(request_id);
            CREATE INDEX IF NOT EXISTS idx_audit_events_ts ON audit_events(ts);
            CREATE INDEX IF NOT EXISTS idx_audit_events_type ON audit_events(event_type);

            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                description TEXT,
                role TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                labels TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS policies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                priority INTEGER NOT NULL DEFAULT 0,
                enabled INTEGER NOT NULL DEFAULT 1,
                resource_pattern TEXT,
                verbs_json TEXT,
                environments_json TEXT,
                effect TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_policies_enabled_pri ON policies(enabled, priority DESC);

            CREATE TABLE IF NOT EXISTS backup_manifest (
                id TEXT PRIMARY KEY,
                reason TEXT NOT NULL,
                request_id TEXT,
                created_at REAL NOT NULL,
                source_db TEXT NOT NULL,
                backup_path TEXT,
                encrypted INTEGER NOT NULL DEFAULT 0,
                sha256_hex TEXT,
                size_bytes INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_hash TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'agent',
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                last_used_at TEXT
            );
            """
        )
        conn.commit()

        # Migrate older DBs missing columns
        if _column_names(
            conn, "audit_events"
        ) and "payload_encrypted" not in _column_names(conn, "audit_events"):
            conn.execute(
                "ALTER TABLE audit_events ADD COLUMN payload_encrypted INTEGER NOT NULL DEFAULT 0"
            )
            conn.commit()

        # Seed demo orders once
        cur = conn.execute("SELECT COUNT(*) FROM demo_orders")
        if cur.fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO demo_orders (label) VALUES (?)",
                [("order-a",), ("order-b",), ("order-c",)],
            )
            conn.commit()


def utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def touch_now() -> float:
    return time.time()
