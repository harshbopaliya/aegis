"""
Ops dashboard JSON APIs — observability, pending approvals, snapshots, live pipelines.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.config import settings
from app.core.crypto import get_fernet
from app.modules import backup_recovery, human_loop, observability
from app.modules.agents import repository as agents_repo
from app.modules.policy_engine import repository as policy_repo

router = APIRouter(prefix="/v1/dashboard", tags=["dashboard"])


@router.get("/overview")
def dashboard_overview(hours: int = Query(default=24, ge=1, le=720)):
    """Single poll-friendly payload for the operator UI."""
    return {
        "product": "AI Agent Safety Gateway",
        "pipeline_modules": [
            {"id": "agent_registry", "title": "Agent registry / identity", "order": 0},
            {"id": "token_scoping", "title": "Token scoping", "order": 1},
            {"id": "policy_engine", "title": "Policy engine (guardrails)", "order": 2},
            {"id": "sandbox", "title": "Sandbox / simulation", "order": 3},
            {"id": "risk_scoring", "title": "Risk scoring", "order": 4},
            {"id": "human_loop", "title": "Human-in-the-loop", "order": 5},
            {"id": "execution", "title": "Execution layer (controlled APIs / DB)", "order": 6},
            {"id": "observability", "title": "Observability & audit", "order": 7},
            {"id": "backup_recovery", "title": "Backup & recovery", "order": 8},
        ],
        "stats": observability.dashboard_stats(hours=hours),
        "active_agent_requests": observability.list_active_pipelines(),
        "recent_completed": observability.recent_completed(40),
        "pending_approvals": human_loop.list_pending(),
        "snapshots": backup_recovery.list_snapshots(),
        "registered_agents_count": len(agents_repo.list_agents()),
        "policy_rules_count": len(policy_repo.list_policies()),
    }


@router.get("/security")
def dashboard_security():
    """Encryption / privacy controls surfaced for operators."""
    return {
        "audit_payload_mode": settings.audit_payload_mode,
        "audit_decrypt_allowed": settings.audit_decrypt_allowed,
        "fernet_configured": get_fernet() is not None,
        "encrypt_backup_files": settings.encrypt_backup_files,
        "require_agent_registration": settings.require_agent_registration,
        "enforce_agent_roles_from_registry": settings.enforce_agent_roles_from_registry,
    }


@router.get("/events")
def dashboard_events(
    limit: int = Query(default=80, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    return {"events": observability.recent_events(limit=limit, offset=offset)}


@router.get("/requests/{request_id}")
def dashboard_request_detail(request_id: str):
    active = observability.get_pipeline(request_id)
    return {
        "request_id": request_id,
        "active_pipeline": active,
        "audit_events": observability.events_for_request(request_id),
        "module_outputs": observability.module_outputs_for_request(request_id),
    }


@router.get("/requests/{request_id}/modules")
def dashboard_module_outputs(request_id: str):
    return observability.module_outputs_for_request(request_id)
