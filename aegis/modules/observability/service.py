"""
[MODULE 6] Observability — structured audit trail (JSON lines + SQLite).

Payload persistence respects ASG_AUDIT_PAYLOAD_MODE (redact / encrypt) so operators
do not accidentally retain raw production bodies.
"""

from __future__ import annotations

import json
import threading
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aegis.adapters import get_storage
from aegis.config import settings
from aegis.core.audit_payload import maybe_decrypt_payload_row, serialize_for_audit

_lock = threading.Lock()
_completed_recent: deque[dict[str, Any]] = deque(maxlen=200)
_PIPELINES: dict[str, dict[str, Any]] = {}

_pipeline_lock = threading.Lock()


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_audit_schema_file() -> None:
    get_storage().init()


def _log_path() -> Path:
    p = Path(settings.log_dir)
    p.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return p / f"audit-{day}.jsonl"


def emit(
    event_type: str,
    request_id: str,
    payload: dict[str, Any],
    *,
    actor_id: str | None = None,
) -> None:
    ts = _utc_iso()
    stored, enc_flag = serialize_for_audit(event_type, payload)
    try:
        payload_obj: Any = json.loads(stored)
    except json.JSONDecodeError:
        payload_obj = {"_serialization_error": True}

    record_for_line = {
        "ts": ts,
        "event_type": event_type,
        "request_id": request_id,
        "actor_id": actor_id,
        "payload": payload_obj,
    }
    line = json.dumps(record_for_line, default=str) + "\n"

    with _lock:
        with _log_path().open("a", encoding="utf-8") as f:
            f.write(line)

        ensure_audit_schema_file()
        get_storage().store_audit_event(
            ts=ts,
            event_type=event_type,
            request_id=request_id,
            actor_id=actor_id,
            payload_json=stored,
            payload_encrypted=enc_flag,
        )


def new_request_id() -> str:
    return str(uuid.uuid4())


def pipeline_start(
    request_id: str,
    *,
    actor_id: str,
    verb: str,
    resource: str,
    environment: str,
) -> None:
    with _pipeline_lock:
        _PIPELINES[request_id] = {
            "request_id": request_id,
            "actor_id": actor_id,
            "verb": verb,
            "resource": resource,
            "environment": environment,
            "current_stage": "request_received",
            "status": "in_progress",
            "updated_at": _utc_iso(),
            "stages": [
                {"stage": "request_received", "ts": _utc_iso(), "detail": None}
            ],
        }


def pipeline_advance(
    request_id: str,
    stage: str,
    detail: str | None = None,
) -> None:
    with _pipeline_lock:
        p = _PIPELINES.get(request_id)
        if not p:
            return
        ts = _utc_iso()
        p["stages"].append({"stage": stage, "ts": ts, "detail": detail})
        p["current_stage"] = stage
        p["updated_at"] = ts


def pipeline_set_status(request_id: str, status: str) -> None:
    with _pipeline_lock:
        p = _PIPELINES.pop(request_id, None)
        if p is None:
            return
        ts = _utc_iso()
        p["status"] = status
        p["updated_at"] = ts
        if status == "awaiting_approval":
            _PIPELINES[request_id] = p
            return
        _completed_recent.appendleft(
            {
                "request_id": request_id,
                "actor_id": p.get("actor_id"),
                "verb": p.get("verb"),
                "resource": p.get("resource"),
                "environment": p.get("environment"),
                "final_status": status,
                "completed_at": ts,
                "stages": p.get("stages", []),
            }
        )


def pipeline_touch_approval_wait(
    request_id: str, summary: str
) -> None:
    with _pipeline_lock:
        p = _PIPELINES.get(request_id)
        if not p:
            return
        ts = _utc_iso()
        p["stages"].append(
            {
                "stage": "human_in_the_loop",
                "ts": ts,
                "detail": summary[:500],
            }
        )
        p["current_stage"] = "human_in_the_loop"
        p["status"] = "awaiting_approval"
        p["updated_at"] = ts


def list_active_pipelines() -> list[dict[str, Any]]:
    with _pipeline_lock:
        return sorted(
            (_PIPELINES.values()),
            key=lambda x: x.get("updated_at") or "",
            reverse=True,
        )


def get_pipeline(request_id: str) -> dict[str, Any] | None:
    with _pipeline_lock:
        p = _PIPELINES.get(request_id)
        return dict(p) if p else None


def recent_completed(limit: int = 50) -> list[dict[str, Any]]:
    with _pipeline_lock:
        return list(_completed_recent)[:limit]


def _row_payload_display(raw_payload: str) -> dict[str, Any]:
    try:
        base = json.loads(raw_payload or "{}")
    except json.JSONDecodeError:
        return {}
    if isinstance(base, dict) and base.get("_enc"):
        return maybe_decrypt_payload_row(raw_payload)
    return base


def recent_events(
    limit: int = 100, offset: int = 0
) -> list[dict[str, Any]]:
    ensure_audit_schema_file()
    return get_storage().recent_events(limit, offset)


def events_for_request(request_id: str) -> list[dict[str, Any]]:
    ensure_audit_schema_file()
    return get_storage().events_for_request(request_id)


def dashboard_stats(hours: int = 24) -> dict[str, Any]:
    ensure_audit_schema_file()
    return get_storage().dashboard_stats(hours)


def reset_pipeline_state_for_tests() -> None:
    with _pipeline_lock:
        _PIPELINES.clear()
        _completed_recent.clear()


def module_outputs_for_request(
    request_id: str,
) -> dict[str, Any]:
    """Maps layer_* audit events to a stable structure for the operator UI."""
    events = events_for_request(request_id)
    layers: dict[str, Any] = {}
    for e in events:
        et = e["event_type"]
        if et.startswith("layer_"):
            key = et.replace("layer_", "", 1)
            layers[key] = {
                "event_type": et,
                "payload": e["payload"],
                "ts": e["ts"],
            }
    return {"request_id": request_id, "layers": layers, "events": events}
