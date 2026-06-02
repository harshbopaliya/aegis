"""
SQLite implementation of Aegis storage, execution, and approval backends.
"""

from __future__ import annotations

import json
import secrets
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from aegis.adapters.base import ApprovalQueue, ExecutionBackend, StorageBackend
from aegis.config import settings
from aegis.core.crypto import encrypt_bytes, get_fernet
from aegis.core.db import connect, init_database, utc_now_iso
from aegis.models.schemas import AgentAction, Environment, HttpVerb


class SQLiteStorageBackend(StorageBackend):
    """Storage backend powered by a local SQLite database."""

    def init(self) -> None:
        init_database()

    def _row_to_agent_dict(self, row: sqlite3.Row) -> dict[str, Any]:
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

    def get_agent(self, agent_id: str) -> dict[str, Any] | None:
        with connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM agents WHERE agent_id = ?", (agent_id,)
            ).fetchone()
            return self._row_to_agent_dict(row) if row else None

    def list_agents(self, enabled_only: bool = False) -> list[dict[str, Any]]:
        with connect() as conn:
            conn.row_factory = sqlite3.Row
            q = "SELECT * FROM agents"
            if enabled_only:
                q += " WHERE enabled = 1"
            q += " ORDER BY display_name COLLATE NOCASE"
            rows = conn.execute(q).fetchall()
            return [self._row_to_agent_dict(r) for r in rows]

    def upsert_agent(
        self,
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
                (
                    agent_id,
                    display_name,
                    description,
                    role,
                    int(enabled),
                    labels_json,
                    now,
                    now,
                ),
            )
            conn.commit()
        return self.get_agent(agent_id)  # type: ignore

    def delete_agent(self, agent_id: str) -> bool:
        with connect() as conn:
            cur = conn.execute(
                "DELETE FROM agents WHERE agent_id = ?", (agent_id,)
            )
            conn.commit()
            return cur.rowcount > 0

    def clear_agents(self) -> None:
        with connect() as conn:
            conn.execute("DELETE FROM agents")
            conn.commit()

    def _row_to_policy_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        verbs_raw = row["verbs_json"]
        envs_raw = row["environments_json"]
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "priority": row["priority"],
            "enabled": bool(row["enabled"]),
            "resource_pattern": row["resource_pattern"],
            "verbs": json.loads(verbs_raw) if verbs_raw else None,
            "environments": json.loads(envs_raw) if envs_raw else None,
            "effect": row["effect"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def get_policy(self, policy_id: int) -> dict[str, Any] | None:
        with connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM policies WHERE id = ?", (policy_id,)
            ).fetchone()
            return self._row_to_policy_dict(row) if row else None

    def list_all_policies(self) -> list[dict[str, Any]]:
        with connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM policies ORDER BY priority DESC, id"
            ).fetchall()
            return [self._row_to_policy_dict(r) for r in rows]

    def list_enabled_policies_ordered(self) -> list[dict[str, Any]]:
        with connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM policies WHERE enabled = 1 ORDER BY priority DESC, id"
            ).fetchall()
            return [self._row_to_policy_dict(r) for r in rows]

    def create_policy(
        self,
        name: str,
        effect: str,
        description: str | None = None,
        priority: int = 100,
        enabled: bool = True,
        resource_pattern: str | None = None,
        verbs: list[str] | None = None,
        environments: list[str] | None = None,
    ) -> dict[str, Any]:
        now = utc_now_iso()
        verbs_json = json.dumps(verbs) if verbs else None
        envs_json = json.dumps(environments) if environments else None
        with connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO policies
                    (name, description, priority, enabled, resource_pattern,
                     verbs_json, environments_json, effect, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    description,
                    priority,
                    int(enabled),
                    resource_pattern,
                    verbs_json,
                    envs_json,
                    effect,
                    now,
                    now,
                ),
            )
            conn.commit()
            return self.get_policy(cur.lastrowid)  # type: ignore

    def update_policy(
        self, policy_id: int, fields: dict[str, Any]
    ) -> dict[str, Any] | None:
        existing = self.get_policy(policy_id)
        if not existing:
            return None
        now = utc_now_iso()
        name = fields.get("name", existing["name"])
        description = fields.get("description", existing["description"])
        priority = fields.get("priority", existing["priority"])
        enabled = fields.get("enabled", existing["enabled"])
        resource_pattern = fields.get(
            "resource_pattern", existing["resource_pattern"]
        )
        verbs = fields.get("verbs", existing["verbs"])
        environments = fields.get("environments", existing["environments"])
        effect = fields.get("effect", existing["effect"])
        if hasattr(effect, "value"):
            effect = effect.value
        verbs_json = json.dumps(verbs) if verbs else None
        envs_json = json.dumps(environments) if environments else None
        with connect() as conn:
            conn.execute(
                """
                UPDATE policies SET
                    name=?, description=?, priority=?, enabled=?,
                    resource_pattern=?, verbs_json=?, environments_json=?,
                    effect=?, updated_at=?
                WHERE id=?
                """,
                (
                    name,
                    description,
                    priority,
                    int(enabled),
                    resource_pattern,
                    verbs_json,
                    envs_json,
                    effect,
                    now,
                    policy_id,
                ),
            )
            conn.commit()
        return self.get_policy(policy_id)

    def delete_policy(self, policy_id: int) -> bool:
        with connect() as conn:
            cur = conn.execute(
                "DELETE FROM policies WHERE id = ?", (policy_id,)
            )
            conn.commit()
            return cur.rowcount > 0

    def clear_policies(self) -> None:
        with connect() as conn:
            conn.execute("DELETE FROM policies")
            conn.commit()

    def store_audit_event(
        self,
        ts: str,
        event_type: str,
        request_id: str,
        actor_id: str | None,
        payload_json: str,
        payload_encrypted: int,
    ) -> None:
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_events (ts, event_type, request_id, actor_id, payload, payload_encrypted)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    ts,
                    event_type,
                    request_id,
                    actor_id,
                    payload_json,
                    payload_encrypted,
                ),
            )
            conn.commit()

    def _row_to_event_display(self, row: sqlite3.Row) -> dict[str, Any]:
        from aegis.modules.observability.service import _row_payload_display

        raw = row["payload"]
        payload = _row_payload_display(raw)
        return {
            "id": row["id"],
            "ts": row["ts"],
            "event_type": row["event_type"],
            "request_id": row["request_id"],
            "actor_id": row["actor_id"],
            "payload": payload,
            "payload_encrypted": bool(row["payload_encrypted"]),
        }

    def recent_events(self, limit: int, offset: int) -> list[dict[str, Any]]:
        with connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, ts, event_type, request_id, actor_id, payload, payload_encrypted
                FROM audit_events
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
            return [self._row_to_event_display(r) for r in rows]

    def events_for_request(self, request_id: str) -> list[dict[str, Any]]:
        with connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, ts, event_type, request_id, actor_id, payload, payload_encrypted
                FROM audit_events
                WHERE request_id = ?
                ORDER BY id ASC
                """,
                (request_id,),
            ).fetchall()
            return [self._row_to_event_display(r) for r in rows]

    def dashboard_stats(self, hours: int) -> dict[str, Any]:
        cutoff = time.time() - hours * 3600
        cutoff_iso = time.strftime(
            "%Y-%m-%dT%H:%M:%S", time.gmtime(cutoff)
        )
        with connect() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM audit_events WHERE ts >= ?",
                (cutoff_iso,),
            ).fetchone()[0]
            by_type_rows = conn.execute(
                """
                SELECT event_type, COUNT(*) AS c
                FROM audit_events
                WHERE ts >= ?
                GROUP BY event_type
                ORDER BY c DESC
                """,
                (cutoff_iso,),
            ).fetchall()
            distinct_req = conn.execute(
                """
                SELECT COUNT(DISTINCT request_id) FROM audit_events WHERE ts >= ?
                """,
                (cutoff_iso,),
            ).fetchone()[0]
        return {
            "window_hours": hours,
            "total_events": total,
            "by_event_type": {r[0]: r[1] for r in by_type_rows},
            "distinct_requests": distinct_req,
        }

    def store_backup_snapshot(
        self,
        snap_id: str,
        reason: str,
        request_id: str,
        created_at: float,
        source_db: str,
        backup_path: str,
        encrypted: int,
        sha256_hex: str,
        size_bytes: int,
    ) -> None:
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
                    created_at,
                    source_db,
                    backup_path,
                    encrypted,
                    sha256_hex,
                    size_bytes,
                ),
            )
            conn.commit()

    def get_backup_snapshot(self, snapshot_id: str) -> dict[str, Any] | None:
        with connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM backup_manifest WHERE id = ?", (snapshot_id,)
            ).fetchone()
            return dict(row) if row else None

    def list_snapshots(self) -> list[dict[str, Any]]:
        with connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM backup_manifest ORDER BY created_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def clear_snapshots(self) -> None:
        with connect() as conn:
            conn.execute("DELETE FROM backup_manifest")
            conn.commit()

    def get_gateway_mirror_count(self) -> int:
        with connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM gateway_mirror").fetchone()[0]

    def get_demo_orders_count(self) -> int:
        with connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM demo_orders").fetchone()[0]


class SQLiteApprovalQueue(ApprovalQueue):
    """In-memory thread-safe approval state queue matching the default behavior."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pending: dict[str, Any] = {}
        self._decisions: dict[str, tuple[bool, str | None]] = {}

    def enqueue(self, request_id: str, summary: str) -> str:
        approval_id = f"appr_{secrets.token_hex(6)}"
        with self._lock:
            self._pending[request_id] = {
                "request_id": request_id,
                "approval_id": approval_id,
                "summary": summary,
                "created_at": time.time(),
                "resolved": False,
                "approved": None,
                "approver_id": None,
            }
        return approval_id

    def list_pending(self) -> list[dict[str, Any]]:
        with self._lock:
            items = []
            for req_id, p in self._pending.items():
                if p["resolved"]:
                    continue
                items.append(
                    {
                        "request_id": p["request_id"],
                        "approval_id": p["approval_id"],
                        "summary": p["summary"],
                        "created_at": p["created_at"],
                    }
                )
            items.sort(key=lambda x: x["created_at"])
            return items

    def resolve(
        self,
        request_id: str,
        approver_id: str,
        approve: bool,
        reason: str | None,
    ) -> bool:
        with self._lock:
            p = self._pending.get(request_id)
            if p is None:
                return False
            p["resolved"] = True
            p["approved"] = approve
            p["approver_id"] = approver_id
            self._decisions[request_id] = (approve, reason)
            return True

    def is_approved(self, request_id: str) -> bool | None:
        with self._lock:
            d = self._decisions.get(request_id)
            if d is None:
                return None
            return d[0]

    def reset_state(self) -> None:
        with self._lock:
            self._pending.clear()
            self._decisions.clear()


class SQLiteExecutionBackend(ExecutionBackend):
    """Execution backend executing mutations and reads on local SQLite."""

    def __init__(self) -> None:
        self._lock = threading.Lock()

    def execute(self, action: AgentAction) -> dict[str, Any]:
        init_database()
        path = Path(settings.sqlite_path)
        out: dict[str, Any] = {"ok": True, "path": str(path)}

        with self._lock, sqlite3.connect(path) as conn:
            if action.verb == HttpVerb.GET:
                if "demo_orders" in action.resource.lower():
                    rows = conn.execute(
                        "SELECT id, label FROM demo_orders"
                    ).fetchall()
                    out["rows"] = [{"id": r[0], "label": r[1]} for r in rows]
                else:
                    out["rows"] = []
                return out

            payload_json = (
                json.dumps(action.payload) if action.payload else "{}"
            )
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
            out["mirror_id"] = conn.execute(
                "SELECT last_insert_rowid()"
            ).fetchone()[0]

            if (
                action.verb == HttpVerb.DELETE
                and action.environment != Environment.PRODUCTION
            ):
                conn.execute(
                    "DELETE FROM demo_orders WHERE id = (SELECT MAX(id) FROM demo_orders)"
                )
                conn.commit()
                out["note"] = (
                    "Non-production: removed latest demo row (simulated destructive effect)."
                )

        return out
