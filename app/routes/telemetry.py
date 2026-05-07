"""Structured agent-side telemetry (no raw production row dumps)."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import AgentLogMessage
from app.modules import observability

router = APIRouter(prefix="/v1/telemetry", tags=["telemetry"])


@router.post("/agent-log")
def post_agent_log(body: AgentLogMessage):
    rid = observability.new_request_id()
    payload = {
        "level": body.level,
        "message": body.message,
        "context": body.context or {},
    }
    observability.emit(
        "agent_log",
        rid,
        payload,
        actor_id=body.agent_id,
    )
    return {"ok": True, "request_id": rid}
