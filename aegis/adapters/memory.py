"""
In-memory mock implementations of Aegis storage, execution, and approval backends.
"""

from __future__ import annotations

import secrets
import threading
import time
from typing import Any

from aegis.adapters.base import ApprovalQueue, ExecutionBackend, StorageBackend
from aegis.models.schemas import AgentAction


class MemoryStorageBackend(StorageBackend):
    """In-memory thread-safe mock storage backend."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._agents: dict[str, dict[str, Any]] = {}
        self._policies: dict[int, dict[str, Any]] = {}
        self._policy_id_counter = 1
        self._audit_events: list[dict[str, Any]] = []
        self._snapshots: dict[str, dict[str, Any]] = {}
        self._mirror_count = 0
        self._orders_count = 3  # Starts with 3 demo orders mock

    def init(self) -> None:
        pass

    def get_agent(self, agent_id: str) -> dict[str, Any] | None:
        with self._lock:
            agent = self._agents.get(agent_id)
            return dict(agent) if agent else None

    def list_agents(self, enabled_only: bool = False) -> list[dict[str, Any]]:
        with self._lock:
            items = list(self._agents.values())
            if enabled_only:
                items = [x for x in items if x["enabled"]]
            return sorted(items, key=lambda x: x["display_name"].lower())

    def upsert_agent(
        self,
        agent_id: str,
        display_name: str,
        description: str | None,
        role: str,
        enabled: bool,
        labels: dict[str, str] | None,
    ) -> dict[str, Any]:
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self._lock:
            existing = self._agents.get(agent_id)
            created = existing["created_at"] if existing else now
            self._agents[agent_id] = {
                "agent_id": agent_id,
                "display_name": display_name,
                "description": description,
                "role": role,
                "enabled": enabled,
                "labels": dict(labels) if labels else {},
                "created_at": created,
                "updated_at": now,
            }
            return dict(self._agents[agent_id])

    def delete_agent(self, agent_id: str) -> bool:
        with self._lock:
            return self._agents.pop(agent_id, None) is not None

    def clear_agents(self) -> None:
        with self._lock:
            self._agents.clear()

    def get_policy(self, policy_id: int) -> dict[str, Any] | None:
        with self._lock:
            pol = self._policies.get(policy_id)
            return dict(pol) if pol else None

    def list_all_policies(self) -> list[dict[str, Any]]:
        with self._lock:
            items = list(self._policies.values())
            return sorted(items, key=lambda x: (-x["priority"], x["id"]))

    def list_enabled_policies_ordered(self) -> list[dict[str, Any]]:
        with self._lock:
            items = [x for x in self._policies.values() if x["enabled"]]
            return sorted(items, key=lambda x: (-x["priority"], x["id"]))

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
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self._lock:
            pid = self._policy_id_counter
            self._policy_id_counter += 1
            self._policies[pid] = {
                "id": pid,
                "name": name,
                "description": description,
                "priority": priority,
                "enabled": enabled,
                "resource_pattern": resource_pattern,
                "verbs": list(verbs) if verbs else None,
                "environments": list(environments) if environments else None,
                "effect": effect,
                "created_at": now,
                "updated_at": now,
            }
            return dict(self._policies[pid])

    def update_policy(
        self, policy_id: int, fields: dict[str, Any]
    ) -> dict[str, Any] | None:
        with self._lock:
            existing = self._policies.get(policy_id)
            if not existing:
                return None
            now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            for k, v in fields.items():
                if k in existing:
                    existing[k] = v
            existing["updated_at"] = now
            return dict(existing)

    def delete_policy(self, policy_id: int) -> bool:
        with self._lock:
            return self._policies.pop(policy_id, None) is not None

    def clear_policies(self) -> None:
        with self._lock:
            self._policies.clear()
            self._policy_id_counter = 1

    def store_audit_event(
        self,
        ts: str,
        event_type: str,
        request_id: str,
        actor_id: str | None,
        payload_json: str,
        payload_encrypted: int,
    ) -> None:
        with self._lock:
            self._audit_events.append(
                {
                    "id": len(self._audit_events) + 1,
                    "ts": ts,
                    "event_type": event_type,
                    "request_id": request_id,
                    "actor_id": actor_id,
                    "payload": payload_json,
                    "payload_encrypted": payload_encrypted,
                }
            )

    def _display_payload(self, raw: str) -> dict[str, Any]:
        import json

        from aegis.modules.observability.service import _row_payload_display

        return _row_payload_display(raw)

    def recent_events(self, limit: int, offset: int) -> list[dict[str, Any]]:
        with self._lock:
            items = list(reversed(self._audit_events))
            slice_items = items[offset : offset + limit]
            return [
                {
                    "id": x["id"],
                    "ts": x["ts"],
                    "event_type": x["event_type"],
                    "request_id": x["request_id"],
                    "actor_id": x["actor_id"],
                    "payload": self._display_payload(x["payload"]),
                    "payload_encrypted": bool(x["payload_encrypted"]),
                }
                for x in slice_items
            ]

    def events_for_request(self, request_id: str) -> list[dict[str, Any]]:
        with self._lock:
            matches = [x for x in self._audit_events if x["request_id"] == request_id]
            return [
                {
                    "id": x["id"],
                    "ts": x["ts"],
                    "event_type": x["event_type"],
                    "request_id": x["request_id"],
                    "actor_id": x["actor_id"],
                    "payload": self._display_payload(x["payload"]),
                    "payload_encrypted": bool(x["payload_encrypted"]),
                }
                for x in matches
            ]

    def dashboard_stats(self, hours: int) -> dict[str, Any]:
        with self._lock:
            cutoff = time.time() - hours * 3600
            cutoff_iso = time.strftime(
                "%Y-%m-%dT%H:%M:%S", time.gmtime(cutoff)
            )
            filtered = [x for x in self._audit_events if x["ts"] >= cutoff_iso]
            by_type: dict[str, int] = {}
            distinct_reqs = set()
            for x in filtered:
                by_type[x["event_type"]] = by_type.get(x["event_type"], 0) + 1
                distinct_reqs.add(x["request_id"])
            return {
                "window_hours": hours,
                "total_events": len(filtered),
                "by_event_type": by_type,
                "distinct_requests": len(distinct_reqs),
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
        with self._lock:
            self._snapshots[snap_id] = {
                "id": snap_id,
                "reason": reason,
                "request_id": request_id,
                "created_at": created_at,
                "source_db": source_db,
                "backup_path": backup_path,
                "encrypted": encrypted,
                "sha256_hex": sha256_hex,
                "size_bytes": size_bytes,
            }

    def get_backup_snapshot(self, snapshot_id: str) -> dict[str, Any] | None:
        with self._lock:
            snap = self._snapshots.get(snapshot_id)
            return dict(snap) if snap else None

    def list_snapshots(self) -> list[dict[str, Any]]:
        with self._lock:
            items = list(self._snapshots.values())
            return sorted(items, key=lambda x: x["created_at"], reverse=True)

    def clear_snapshots(self) -> None:
        with self._lock:
            self._snapshots.clear()

    def get_gateway_mirror_count(self) -> int:
        with self._lock:
            return self._mirror_count

    def get_demo_orders_count(self) -> int:
        with self._lock:
            return self._orders_count


class MemoryApprovalQueue(ApprovalQueue):
    """In-memory thread-safe mock approval queue."""

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


class MemoryExecutionBackend(ExecutionBackend):
    """In-memory mock execution backend."""

    def execute(self, action: AgentAction) -> dict[str, Any]:
        return {
            "ok": True,
            "mock": True,
            "executed_action": {
                "verb": action.verb.value,
                "resource": action.resource,
                "environment": action.environment.value,
                "payload": action.payload,
            },
        }
