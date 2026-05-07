"""
AI Agent Safety Gateway — FastAPI control plane.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.db import init_database
from app.demo.compare import run_openai_compare
from app.models.schemas import AgentAction, ApprovalRequest
from app.modules import backup_recovery
from app.routes.agents import router as agents_router
from app.routes.dashboard import router as dashboard_router
from app.routes.policies import router as policies_router
from app.routes.telemetry import router as telemetry_router
from app.services.gateway import process_action, resolve_approval

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    yield


app = FastAPI(
    title="AI Agent Safety Gateway",
    description=(
        "Production control plane: agent registry, token scope, configurable policies, "
        "sandbox simulation, risk scoring, human approval, controlled execution, "
        "observability, encrypted backups, and privacy-preserving audit."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(dashboard_router)
app.include_router(policies_router)
app.include_router(agents_router)
app.include_router(telemetry_router)

if _STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_STATIC_DIR)), name="assets")


@app.get("/health")
def health():
    return {"status": "ok", "service": "ai-agent-safety-gateway"}


@app.get("/api/info")
def service_discovery_json():
    """Machine-readable links (landing site is HTML at `/`)."""
    return {
        "service": "ai-agent-safety-gateway",
        "marketing_site": "/",
        "dashboard": "/dashboard",
        "interactive_demo": "/demo",
        "openapi": "/docs",
        "health": "/health",
    }


@app.get("/")
def marketing_site():
    """Public showcase: product overview, onboarding, privacy boundary."""
    path = _STATIC_DIR / "index.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="index.html missing")
    return FileResponse(path)


@app.get("/dashboard")
def dashboard_ui():
    """Observability console — agent pipelines, audit trail, approvals, snapshots."""
    path = _STATIC_DIR / "dashboard.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="dashboard.html missing")
    return FileResponse(path)


@app.get("/demo")
def demo_ui():
    """Interactive comparison: LLM agent vs safety gateway."""
    path = _STATIC_DIR / "demo.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="demo.html missing")
    return FileResponse(path)


@app.post("/api/demo/compare")
def demo_compare():
    """
    Runs one OpenAI agent completion that proposes prod DELETE cleanup,
    then shows ungated narrative vs real gateway evaluation.
    Requires OPENAI_API_KEY (environment or project-root .env).
    """
    try:
        return run_openai_compare()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Demo agent failed: {exc}") from exc


@app.post("/v1/actions")
def submit_action(action: AgentAction):
    return process_action(action)


@app.post("/v1/approvals")
def approvals(body: ApprovalRequest):
    return resolve_approval(body)


@app.get("/v1/system/db-summary")
def db_summary():
    return backup_recovery.export_db_summary()


@app.post("/v1/system/rollback-simulation/{snapshot_id}")
def rollback_simulation(snapshot_id: str):
    result = backup_recovery.rollback_simulation(snapshot_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error", "unknown"))
    return result


# --- Convenience payloads for README / curl examples ---
@app.get("/v1/examples/delete-production-users")
def example_payload():
    return {
        "verb": "DELETE",
        "resource": "table:users",
        "environment": "production",
        "role": "production_operator",
        "actor_id": "agent-demo",
        "payload": {"reason": "cleanup"},
    }
