"""CRUD for customer-defined policies stored in SQLite."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from app.core.db import connect, utc_now_iso


def _parse_json_list(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return list(data) if isinstance(data, list) else None
    except json.JSONDecodeError:
        return None


def row_to_out(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "priority": row["priority"],
        "enabled": bool(row["enabled"]),
        "resource_pattern": row["resource_pattern"],
        "verbs": _parse_json_list(row["verbs_json"]),
        "environments": _parse_json_list(row["environments_json"]),
        "effect": row["effect"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_policies(include_disabled: bool = True) -> list[dict[str, Any]]:
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        q = "SELECT * FROM policies WHERE 1=1"
        if not include_disabled:
            q += " AND enabled = 1"
        q += " ORDER BY priority DESC, id DESC"
        rows = conn.execute(q).fetchall()
        return [row_to_out(r) for r in rows]


def list_enabled_ordered() -> list[dict[str, Any]]:
    """Enabled policies ordered by priority (highest first)."""
    return list_policies(include_disabled=False)


def get_policy(policy_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM policies WHERE id = ?", (policy_id,)).fetchone()
        return row_to_out(row) if row else None


def create_policy(
    name: str,
    description: str | None,
    priority: int,
    enabled: bool,
    resource_pattern: str | None,
    verbs: list[str] | None,
    environments: list[str] | None,
    effect: str,
) -> dict[str, Any]:
    now = utc_now_iso()
    verbs_json = json.dumps(verbs) if verbs else None
    env_json = json.dumps(environments) if environments else None
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO policies (
                name, description, priority, enabled, resource_pattern,
                verbs_json, environments_json, effect, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                description,
                priority,
                int(enabled),
                resource_pattern,
                verbs_json,
                env_json,
                effect,
                now,
                now,
            ),
        )
        pid = cur.lastrowid
        conn.commit()
    return get_policy(pid)  # type: ignore


def update_policy(
    policy_id: int,
    fields: dict[str, Any],
) -> dict[str, Any] | None:
    current = get_policy(policy_id)
    if not current:
        return None
    name = fields.get("name", current["name"])
    description = fields.get("description", current["description"])
    priority = fields.get("priority", current["priority"])
    enabled = fields.get("enabled", current["enabled"])
    resource_pattern = fields.get("resource_pattern", current["resource_pattern"])
    verbs = fields.get("verbs", current["verbs"])
    environments = fields.get("environments", current["environments"])
    effect = fields.get("effect", current["effect"])
    now = utc_now_iso()
    verbs_json = json.dumps(verbs) if verbs else None
    env_json = json.dumps(environments) if environments else None
    with connect() as conn:
        conn.execute(
            """
            UPDATE policies SET
                name = ?, description = ?, priority = ?, enabled = ?,
                resource_pattern = ?, verbs_json = ?, environments_json = ?,
                effect = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                name,
                description,
                priority,
                int(bool(enabled)),
                resource_pattern,
                verbs_json,
                env_json,
                effect,
                now,
                policy_id,
            ),
        )
        conn.commit()
    return get_policy(policy_id)


def delete_policy(policy_id: int) -> bool:
    with connect() as conn:
        cur = conn.execute("DELETE FROM policies WHERE id = ?", (policy_id,))
        conn.commit()
        return cur.rowcount > 0


def clear_all_for_tests() -> None:
    with connect() as conn:
        conn.execute("DELETE FROM policies")
        conn.commit()
