"""Persistent agent registry — maps agent_id → bound Role (token scope at identity layer)."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from app.core.db import connect, utc_now_iso


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    labels = row["labels"]
    parsed = None
    if labels:
        try:
            parsed = json.loads(labels)
        except json.JSONDecodeError:
            parsed = {}
    return {
        "agent_id": row["agent_id"],
        "display_name": row["display_name"],
        "description": row["description"],
        "role": row["role"],
        "enabled": bool(row["enabled"]),
        "labels": parsed,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get(agent_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM agents WHERE agent_id = ?", (agent_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None


def list_agents(enabled_only: bool = False) -> list[dict[str, Any]]:
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        q = "SELECT * FROM agents"
        if enabled_only:
            q += " WHERE enabled = 1"
        q += " ORDER BY display_name COLLATE NOCASE"
        rows = conn.execute(q).fetchall()
        return [_row_to_dict(r) for r in rows]


def upsert(
    agent_id: str,
    display_name: str,
    description: str | None,
    role: str,
    enabled: bool,
    labels: dict[str, str] | None,
) -> dict[str, Any]:
    now = utc_now_iso()
    labels_json = json.dumps(labels or {})
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO agents (agent_id, display_name, description, role, enabled, labels, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(agent_id) DO UPDATE SET
                display_name = excluded.display_name,
                description = excluded.description,
                role = excluded.role,
                enabled = excluded.enabled,
                labels = excluded.labels,
                updated_at = excluded.updated_at,
                created_at = agents.created_at
            """,
            (agent_id, display_name, description, role, int(enabled), labels_json, now, now),
        )
        conn.commit()
    return get(agent_id)  # type: ignore


def update_partial(agent_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
    row = get(agent_id)
    if not row:
        return None
    display_name = fields.get("display_name", row["display_name"])
    description = fields.get("description", row["description"])
    role = fields.get("role", row["role"])
    enabled = fields.get("enabled", row["enabled"])
    labels = fields.get("labels", row["labels"])
    role_str = role.value if hasattr(role, "value") else str(role)
    return upsert(
        agent_id,
        str(display_name),
        description,
        role_str,
        bool(enabled),
        labels if isinstance(labels, dict) else row["labels"],
    )


def delete_agent(agent_id: str) -> bool:
    with connect() as conn:
        cur = conn.execute("DELETE FROM agents WHERE agent_id = ?", (agent_id,))
        conn.commit()
        return cur.rowcount > 0


def clear_all_for_tests() -> None:
    with connect() as conn:
        conn.execute("DELETE FROM agents")
        conn.commit()
