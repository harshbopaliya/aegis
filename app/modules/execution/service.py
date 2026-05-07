"""
Execution layer — single choke point for controlled data access (SQLite demo).
Replace this module with your production connectors; keep the gateway contract.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from app.config import settings
from app.core.db import init_database
from app.models.schemas import AgentAction, Environment, HttpVerb

_lock = threading.Lock()


def execute(action: AgentAction) -> dict:
    """
    Controlled execution: mutating actions persist only through this module.
    """
    init_database()
    path = Path(settings.sqlite_path)
    out: dict = {"ok": True, "path": str(path)}

    with _lock, sqlite3.connect(path) as conn:
        if action.verb == HttpVerb.GET:
            if "demo_orders" in action.resource.lower():
                rows = conn.execute("SELECT id, label FROM demo_orders").fetchall()
                out["rows"] = [{"id": r[0], "label": r[1]} for r in rows]
            else:
                out["rows"] = []
            return out

        payload_json = json.dumps(action.payload) if action.payload else "{}"
        conn.execute(
            """
            INSERT INTO gateway_mirror (env, resource, verb, payload)
            VALUES (?, ?, ?, ?)
            """,
            (
                action.environment.value,
                action.resource,
                action.verb.value,
                payload_json,
            ),
        )
        conn.commit()
        out["mirror_id"] = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        if action.verb == HttpVerb.DELETE and action.environment != Environment.PRODUCTION:
            conn.execute("DELETE FROM demo_orders WHERE id = (SELECT MAX(id) FROM demo_orders)")
            conn.commit()
            out["note"] = "Non-production: removed latest demo row (simulated destructive effect)."

    return out
