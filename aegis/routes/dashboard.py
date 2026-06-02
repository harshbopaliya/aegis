"""Dashboard API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from aegis.core.auth import require_operator
from aegis.modules import backup_recovery, human_loop, observability

router = APIRouter()


@router.get("/overview")
def dashboard_overview(
    hours: int = Query(default=24, ge=1, le=8760),
    _role: str = Depends(require_operator),
):
    """KPIs, active pipelines, pending approvals, recent completions, snapshots."""
    stats = observability.dashboard_stats(hours)
    return {
        "stats": stats,
        "active_pipelines": observability.list_active_pipelines(),
        "pending_approvals": human_loop.list_pending(),
        "recent_completed": observability.recent_completed(20),
        "snapshots": backup_recovery.list_snapshots()[:10],
        "modules": [
            "token_scoping",
            "policy_engine",
            "sandbox",
            "risk_scoring",
            "human_loop",
            "execution",
            "observability",
            "backup_recovery",
        ],
    }


@router.get("/events")
def dashboard_events(
    limit: int = Query(default=80, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    _role: str = Depends(require_operator),
):
    """Newest audit rows."""
    return observability.recent_events(limit=limit, offset=offset)


@router.get("/requests/{request_id}")
def dashboard_request_detail(
    request_id: str,
    _role: str = Depends(require_operator),
):
    """Per-request audit timeline plus active pipeline state."""
    pipeline = observability.get_pipeline(request_id)
    module_data = observability.module_outputs_for_request(request_id)
    return {
        "request_id": request_id,
        "pipeline": pipeline,
        **module_data,
    }
