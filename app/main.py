"""
Aegis — Production FastAPI control plane.

A comprehensive safety infrastructure for AI agents that enforces:
- Token scoping and role-based access control
- Configurable policy guardrails
- Sandbox simulation for prediction
- Risk scoring and assessment
- Human-in-the-loop approval workflows
- Controlled execution with audit trail
- Observability and compliance logging
- Encrypted backup and recovery
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings
from app.core.db import init_database
from app.core.logging_config import RequestContextLogger, setup_logging
from app.core.middleware import (
    RequestIdMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    setup_cors,
)
from app.demo.compare import run_openai_compare
from app.models.schemas import AgentAction, ApprovalRequest
from app.modules import backup_recovery
from app.routes.agent_demo import router as agent_demo_router
from app.routes.agents import router as agents_router
from app.routes.dashboard import router as dashboard_router
from app.routes.policies import router as policies_router
from app.routes.telemetry import router as telemetry_router
from app.services.gateway import process_action, resolve_approval

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    logger.info("Starting Aegis", extra={"environment": settings.environment})
    
    # Initialize database and tables
    try:
        init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database", exc_info=True)
        raise
    
    # Log configuration (non-sensitive)
    logger.info(
        "Gateway configuration loaded",
        extra={
            "require_agent_registration": settings.require_agent_registration,
            "strict_block_delete_production": settings.strict_block_delete_production,
            "audit_payload_mode": settings.audit_payload_mode,
            "environment": settings.environment,
        },
    )
    
    yield
    
    logger.info("Shutting down Aegis")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description=(
        "Production-grade control plane for AI agents: token scoping, policy guardrails, "
        "sandbox simulation, risk scoring, human-in-the-loop approval, controlled execution, "
        "observability, encrypted backups, and privacy-preserving audit trail."
    ),
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ========== Middleware Setup ==========
# Add middleware in reverse order (last added = first executed)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(setup_cors)

# ========== Router Registration ==========
app.include_router(dashboard_router, prefix="/v1/dashboard", tags=["Dashboard"])
app.include_router(policies_router, prefix="/v1/policies", tags=["Policies"])
app.include_router(agents_router, prefix="/v1/agents", tags=["Agents"])
app.include_router(agent_demo_router, tags=["AI Agent Demo"])
app.include_router(telemetry_router, prefix="/v1/telemetry", tags=["Telemetry"])

# ========== Static Files ==========
if _STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_STATIC_DIR)), name="assets")


# ========== Exception Handlers ==========
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with structured response."""
    request_id = request.headers.get("x-request-id", "unknown")
    logger.warning(
        "Validation error",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "errors": exc.errors(),
        },
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Invalid request",
            "request_id": request_id,
            "errors": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with structured response."""
    request_id = request.headers.get("x-request-id", "unknown")
    logger.error(
        f"Unhandled exception: {type(exc).__name__}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "error": str(exc),
        },
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "request_id": request_id,
        },
    )


# ========== Health & Monitoring Endpoints ==========
@app.get("/health", tags=["Health"])
def health_check():
    """Basic health check endpoint."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/health/ready", tags=["Health"])
def readiness_check():
    """Kubernetes readiness probe."""
    try:
        init_database()
        return {
            "status": "ready",
            "service": settings.app_name,
            "checks": {
                "database": "ok",
            },
        }
    except Exception as e:
        logger.error("Readiness check failed", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "error": str(e),
            },
        )


@app.get("/health/live", tags=["Health"])
def liveness_check():
    """Kubernetes liveness probe."""
    return {
        "status": "alive",
        "service": settings.app_name,
    }


# ========== Service Discovery ==========
@app.get("/api/info", tags=["Discovery"])
def service_discovery_json():
    """Machine-readable API discovery endpoint."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "endpoints": {
            "marketing_site": "/",
            "dashboard": "/dashboard",
            "interactive_demo": "/demo",
            "openapi": "/docs",
            "health": "/health",
            "actions": "/v1/actions",
            "approvals": "/v1/approvals",
        },
    }


# ========== UI Endpoints ==========
@app.get("/", tags=["UI"])
def marketing_site():
    """Public showcase: product overview, onboarding, privacy boundary."""
    path = _STATIC_DIR / "index.html"
    if not path.is_file():
        logger.warning("Marketing site HTML not found", extra={"path": str(path)})
        raise HTTPException(status_code=404, detail="Marketing site not available")
    return FileResponse(path, media_type="text/html")


@app.get("/dashboard", tags=["UI"])
def dashboard_ui():
    """Observability console — agent pipelines, audit trail, approvals, snapshots."""
    path = _STATIC_DIR / "dashboard.html"
    if not path.is_file():
        logger.warning("Dashboard HTML not found", extra={"path": str(path)})
        raise HTTPException(status_code=404, detail="Dashboard not available")
    return FileResponse(path, media_type="text/html")


@app.get("/demo", tags=["UI"])
def demo_ui():
    """Interactive comparison: LLM agent vs safety gateway."""
    path = _STATIC_DIR / "demo.html"
    if not path.is_file():
        logger.warning("Demo HTML not found", extra={"path": str(path)})
        raise HTTPException(status_code=404, detail="Demo not available")
    return FileResponse(path, media_type="text/html")


# ========== Core Gateway Endpoints ==========
@app.post("/v1/actions", tags=["Actions"], response_model=dict)
@limiter.limit(f"{settings.rate_limit_actions_per_minute}/minute")
async def submit_action(action: AgentAction, request: Request):
    """
    Submit an action for safety evaluation.
    
    The action flows through:
    1. Agent registry (if required)
    2. Token scoping (role-based access control)
    3. Policy engine (allow/block/require_approval)
    4. Sandbox simulation (predict outcome without executing)
    5. Risk scoring (0-100 risk assessment)
    6. Human-in-the-loop (if approval required)
    7. Controlled execution (only via gateway)
    
    Returns request_id for tracking and approval workflow.
    """
    request_id = request.headers.get("x-request-id", "unknown")
    actor_id = action.actor_id
    
    try:
        with RequestContextLogger(request_id, actor_id) as ctx_logger:
            ctx_logger.info("Processing action", extra={
                "verb": action.verb.value,
                "resource": action.resource,
                "environment": action.environment.value,
            })
            result = process_action(action)
            ctx_logger.info("Action processed", extra={
                "outcome": result.final_outcome,
                "executed": result.executed,
            })
            return result
    except Exception as e:
        logger.error(f"Action processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process action",
        )


@app.post("/v1/approvals", tags=["Approvals"], response_model=dict)
@limiter.limit(f"{settings.rate_limit_requests_per_minute}/minute")
async def approvals(body: ApprovalRequest, request: Request):
    """
    Resolve (approve or reject) a pending human approval.
    
    Used by human operators to approve or reject actions queued by the
    human-in-the-loop module.
    """
    request_id = request.headers.get("x-request-id", "unknown")
    
    try:
        with RequestContextLogger(request_id, body.approver_id) as ctx_logger:
            ctx_logger.info("Processing approval", extra={
                "request_id": body.request_id,
                "approve": body.approve,
            })
            result = resolve_approval(body)
            ctx_logger.info("Approval processed", extra={
                "status": result.get("status", "unknown"),
            })
            return result
    except Exception as e:
        logger.error(f"Approval processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process approval",
        )


# ========== System Endpoints ==========
@app.get("/v1/system/db-summary", tags=["System"])
def db_summary():
    """Export database summary and metadata."""
    try:
        return backup_recovery.export_db_summary()
    except Exception as e:
        logger.error("DB summary export failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export database summary",
        )


@app.post("/v1/system/rollback-simulation/{snapshot_id}", tags=["System"])
def rollback_simulation(snapshot_id: str, request: Request):
    """Simulate rollback to a previous snapshot."""
    request_id = request.headers.get("x-request-id", "unknown")
    
    try:
        logger.info("Rollback simulation requested", extra={
            "request_id": request_id,
            "snapshot_id": snapshot_id,
        })
        result = backup_recovery.rollback_simulation(snapshot_id)
        if not result.get("ok"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.get("error", "Snapshot not found"),
            )
        return result
    except Exception as e:
        logger.error("Rollback simulation failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to simulate rollback",
        )


# ========== Example Payloads ==========
@app.get("/v1/examples/delete-production-users", tags=["Examples"])
def example_delete_production():
    """Example payload: destructive action on production (for testing HITL)."""
    return {
        "verb": "DELETE",
        "resource": "table:users",
        "environment": "production",
        "role": "production_operator",
        "actor_id": "agent-demo",
        "payload": {"reason": "cleanup"},
    }


@app.get("/v1/examples/safe-read", tags=["Examples"])
def example_safe_read():
    """Example payload: safe read operation (should execute)."""
    return {
        "verb": "GET",
        "resource": "table:demo_orders",
        "environment": "staging",
        "role": "read_only",
        "actor_id": "agent-demo",
    }


@app.post("/api/demo/compare", tags=["Demo"])
def demo_compare(request: Request):
    """
    Interactive demo: Compare ungated LLM agent vs safety gateway.
    
    Runs an OpenAI agent completion that proposes production DELETE,
    then shows both:
    1. What ungated agent would do (narrative)
    2. What safety gateway actually allows (real evaluation)
    
    Requires OPENAI_API_KEY in environment or .env file.
    """
    request_id = request.headers.get("x-request-id", "unknown")
    
    try:
        logger.info("Starting demo comparison", extra={"request_id": request_id})
        return run_openai_compare()
    except RuntimeError as exc:
        logger.warning(f"Demo not available: {exc}", extra={"request_id": request_id})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(f"Demo comparison failed: {exc}", extra={"request_id": request_id}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Demo agent failed: {exc}",
        ) from exc


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=1 if settings.debug else settings.workers,
        log_level=settings.log_level.lower(),
    )
