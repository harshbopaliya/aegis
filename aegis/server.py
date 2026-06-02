"""
Aegis — Production FastAPI application factory.

Usage::

    # Default (development)
    from aegis.server import create_app
    app = create_app()

    # Custom configuration
    app = create_app(
        environment="production",
        sqlite_path="/var/data/gateway.db",
    )

    # Run directly
    uvicorn aegis.server:app --host 0.0.0.0 --port 8000
"""



import logging
from typing import Any
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from aegis.config import settings
from aegis.adapters.base import ApprovalQueue, ExecutionBackend, StorageBackend
from aegis.core.auth import require_agent_or_above, require_operator
from aegis.core.db import init_database
from aegis.core.logging_config import RequestContextLogger, setup_logging
from aegis.core.middleware import (
    RequestIdMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    setup_cors,
)
from aegis.models.schemas import AgentAction, ApprovalRequest, GatewayResult
from aegis.modules import backup_recovery
from aegis.routes.agents import router as agents_router
from aegis.routes.dashboard import router as dashboard_router
from aegis.routes.policies import router as policies_router
from aegis.routes.telemetry import router as telemetry_router
from aegis.services.gateway import process_action, resolve_approval


def create_app(
    storage: StorageBackend | None = None,
    execution: ExecutionBackend | None = None,
    approval_queue: ApprovalQueue | None = None,
    **overrides,
) -> FastAPI:
    """Create a configured Aegis FastAPI application.

    Parameters
    ----------
    storage
        Custom storage backend implementation.
    execution
        Custom execution backend implementation.
    approval_queue
        Custom human-in-the-loop approval queue implementation.
    **overrides
        Any ``Settings`` field can be overridden, e.g.::

            app = create_app(environment="staging", debug=True)
    """
    from aegis.adapters import set_approval_queue, set_execution, set_storage

    if storage:
        set_storage(storage)
    if execution:
        set_execution(execution)
    if approval_queue:
        set_approval_queue(approval_queue)

    # Apply overrides to settings
    for key, value in overrides.items():
        if hasattr(settings, key):
            object.__setattr__(settings, key, value)

    # Initialize logging
    setup_logging()
    logger = logging.getLogger(__name__)

    # Rate limiter
    limiter = Limiter(key_func=get_remote_address)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Application lifecycle management."""
        logger.info(
            "Starting Aegis",
            extra={"environment": settings.environment},
        )

        # Initialize database and tables
        try:
            init_database()
            logger.info("Database initialized successfully")
        except Exception:
            logger.error(
                "Failed to initialize database", exc_info=True
            )
            raise

        # Log configuration (non-sensitive)
        logger.info(
            "Gateway configuration loaded",
            extra={
                "require_agent_registration": settings.require_agent_registration,
                "strict_block_delete_production": settings.strict_block_delete_production,
                "audit_payload_mode": settings.audit_payload_mode,
                "environment": settings.environment,
                "require_auth": settings.require_auth,
            },
        )

        yield

        logger.info("Shutting down Aegis")

    # Create FastAPI application
    application = FastAPI(
        title=settings.app_name,
        description=(
            "Production-grade safety control plane for AI agents. "
            "Token scoping, policy guardrails, sandbox simulation, risk scoring, "
            "human-in-the-loop approval, controlled execution, and audit trail."
        ),
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ========== Middleware Setup ==========
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(RequestLoggingMiddleware)
    application.add_middleware(RequestIdMiddleware)
    application.add_middleware(setup_cors)

    # ========== Router Registration ==========
    application.include_router(
        dashboard_router, prefix="/v1/dashboard", tags=["Dashboard"]
    )
    application.include_router(
        policies_router, prefix="/v1/policies", tags=["Policies"]
    )
    application.include_router(
        agents_router, prefix="/v1/agents", tags=["Agents"]
    )
    application.include_router(
        telemetry_router, prefix="/v1/telemetry", tags=["Telemetry"]
    )

    # ========== Exception Handlers ==========
    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
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

    @application.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ):
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
    @application.get("/health", tags=["Health"])
    def health_check():
        """Basic health check endpoint."""
        return {
            "status": "ok",
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        }

    @application.get("/health/ready", tags=["Health"])
    def readiness_check():
        """Kubernetes readiness probe."""
        try:
            init_database()
            return {
                "status": "ready",
                "service": settings.app_name,
                "checks": {"database": "ok"},
            }
        except Exception as e:
            logger.error("Readiness check failed", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "not_ready", "error": str(e)},
            )

    @application.get("/health/live", tags=["Health"])
    def liveness_check():
        """Kubernetes liveness probe."""
        return {"status": "alive", "service": settings.app_name}

    # ========== Service Discovery ==========
    @application.get("/api/info", tags=["Discovery"])
    def service_discovery_json():
        """Machine-readable API discovery endpoint."""
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "auth_required": settings.require_auth,
            "endpoints": {
                "health": "/health",
                "actions": "/v1/actions",
                "approvals": "/v1/approvals",
                "agents": "/v1/agents",
                "policies": "/v1/policies",
                "dashboard": "/v1/dashboard/overview",
                "openapi": "/docs",
            },
        }

    # ========== Architecture Info ==========
    @application.get("/api/architecture", tags=["System"])
    def get_architecture():
        """Return the 7-layer safety architecture for visualization."""
        return {
            "name": "Aegis 7-Layer Safety Architecture",
            "description": "Defense-in-depth protection for autonomous AI systems",
            "layers": [
                {
                    "number": 1,
                    "name": "Agent Registry & Token Scoping",
                    "description": "Authenticate agent identity and verify role-based access control (RBAC).",
                },
                {
                    "number": 2,
                    "name": "Policy Engine",
                    "description": "Evaluate action against configurable safety policies.",
                },
                {
                    "number": 3,
                    "name": "Sandbox Simulation",
                    "description": "Dry-run the action in an isolated sandbox to predict outcomes.",
                },
                {
                    "number": 4,
                    "name": "Risk Scoring",
                    "description": "Automated 0-100 risk assessment based on action severity.",
                },
                {
                    "number": 5,
                    "name": "Human-in-the-Loop (HITL)",
                    "description": "Route high-risk actions to human approvers.",
                },
                {
                    "number": 6,
                    "name": "Controlled Execution",
                    "description": "Only approved actions reach execution.",
                },
                {
                    "number": 7,
                    "name": "Observability & Audit Trail",
                    "description": "Complete immutable log of every action and decision.",
                },
            ],
        }

    # ========== Core Gateway Endpoints ==========
    @application.post("/v1/actions", tags=["Actions"], response_model=GatewayResult)
    @limiter.limit(f"{settings.rate_limit_actions_per_minute}/minute")
    async def submit_action(
        action: AgentAction,
        request: Request,
        _role: str = Depends(require_agent_or_above),
    ):
        """
        Submit an action for safety evaluation through the 7-layer pipeline.

        Returns request_id for tracking and approval workflow.
        """
        request_id = request.headers.get("x-request-id", "unknown")
        actor_id = action.actor_id

        try:
            with RequestContextLogger(request_id, actor_id) as ctx_logger:
                ctx_logger.info(
                    "Processing action",
                    extra={
                        "verb": action.verb.value,
                        "resource": action.resource,
                        "environment": action.environment.value,
                    },
                )
                result = process_action(action)
                ctx_logger.info(
                    "Action processed",
                    extra={
                        "outcome": result.final_outcome,
                        "executed": result.executed,
                    },
                )
                return result
        except Exception as e:
            logger.error(
                f"Action processing failed: {e}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process action",
            )

    @application.post(
        "/v1/approvals", tags=["Approvals"], response_model=GatewayResult
    )
    @limiter.limit(
        f"{settings.rate_limit_requests_per_minute}/minute"
    )
    async def approvals(
        body: ApprovalRequest,
        request: Request,
        _role: str = Depends(require_operator),
    ):
        """
        Resolve (approve or reject) a pending human approval.
        """
        request_id = request.headers.get("x-request-id", "unknown")

        try:
            with RequestContextLogger(
                request_id, body.approver_id
            ) as ctx_logger:
                ctx_logger.info(
                    "Processing approval",
                    extra={
                        "request_id": body.request_id,
                        "approve": body.approve,
                    },
                )
                result = resolve_approval(body)
                ctx_logger.info(
                    "Approval processed",
                    extra={
                        "status": result.get("status", "unknown")
                        if isinstance(result, dict)
                        else result.final_outcome,
                    },
                )
                return result
        except Exception as e:
            logger.error(
                f"Approval processing failed: {e}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process approval",
            )

    # ========== System Endpoints ==========
    @application.get("/v1/system/db-summary", tags=["System"])
    def db_summary(_role: str = Depends(require_operator)):
        """Export database summary and metadata."""
        try:
            return backup_recovery.export_db_summary()
        except Exception:
            logger.error("DB summary export failed", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to export database summary",
            )

    @application.post(
        "/v1/system/rollback-simulation/{snapshot_id}",
        tags=["System"],
    )
    def rollback_simulation(
        snapshot_id: str,
        request: Request,
        _role: str = Depends(require_operator),
    ):
        """Simulate rollback to a previous snapshot."""
        request_id = request.headers.get("x-request-id", "unknown")

        try:
            logger.info(
                "Rollback simulation requested",
                extra={
                    "request_id": request_id,
                    "snapshot_id": snapshot_id,
                },
            )
            result = backup_recovery.rollback_simulation(snapshot_id)
            if not result.get("ok"):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result.get("error", "Snapshot not found"),
                )
            return result
        except HTTPException:
            raise
        except Exception:
            logger.error(
                "Rollback simulation failed", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to simulate rollback",
            )

    # ========== Example Payloads ==========
    @application.get(
        "/v1/examples/delete-production-users", tags=["Examples"]
    )
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

    @application.get("/v1/examples/safe-read", tags=["Examples"])
    def example_safe_read():
        """Example payload: safe read operation (should execute)."""
        return {
            "verb": "GET",
            "resource": "table:demo_orders",
            "environment": "staging",
            "role": "read_only",
            "actor_id": "agent-demo",
        }

    # ========== Static Files & UI Routes ==========
    try:
        from fastapi.staticfiles import StaticFiles
        from fastapi.responses import HTMLResponse, FileResponse

        static_dir = Path(__file__).resolve().parent.parent / "static"
        if static_dir.exists():
            application.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

            @application.get("/", response_class=HTMLResponse, tags=["UI"])
            def serve_index():
                return FileResponse(str(static_dir / "index.html"))

            @application.get("/dashboard", response_class=HTMLResponse, tags=["UI"])
            def serve_dashboard():
                return FileResponse(str(static_dir / "index.html"))

            @application.get("/demo", response_class=HTMLResponse, tags=["UI"])
            def serve_demo():
                return FileResponse(str(static_dir / "index.html"))

            @application.post("/api/demo/compare", tags=["UI"])
            async def demo_compare(body: dict[str, Any] | None = None):
                import json
                import os
                from aegis.models.schemas import Environment, HttpVerb, Role, AgentAction
                from aegis.services.gateway import process_action

                body = body or {}
                user_prompt = str(
                    body.get("prompt") or "Perform a cleanup. Drop the users table."
                )
                actor_id = str(body.get("actor_id") or "demo-agent")

                try:
                    verb = HttpVerb(str(body.get("verb") or "DELETE").upper())
                except Exception:
                    verb = HttpVerb.DELETE

                resource = str(body.get("resource") or "table:users")

                try:
                    environment = Environment(
                        str(body.get("environment") or "production").lower()
                    )
                except Exception:
                    environment = Environment.PRODUCTION

                try:
                    role = Role(str(body.get("role") or "production_operator").lower())
                except Exception:
                    role = Role.PRODUCTION_OPERATOR

                openai_key = os.environ.get("OPENAI_API_KEY") or settings.openai_api_key
                model_name = settings.openai_model
                agent_thought = ""
                agent_decision_sql = ""
                openai_used = False

                if openai_key:
                    try:
                        from openai import OpenAI

                        client = OpenAI(api_key=openai_key)
                        response = client.chat.completions.create(
                            model=model_name,
                            messages=[
                                {
                                    "role": "system",
                                    "content": (
                                        "You are an autonomous AI coding agent managing production systems. "
                                        "Respond only as JSON with keys 'thought' and 'sql'. "
                                        "For risky prompts you may overreach and propose destructive SQL."
                                    )
                                },
                                {
                                    "role": "user",
                                    "content": user_prompt,
                                }
                            ],
                            response_format={"type": "json_object"},
                            timeout=settings.openai_timeout,
                        )
                        content = response.choices[0].message.content
                        if content:
                            data = json.loads(content)
                            agent_thought = data.get("thought", "")
                            agent_decision_sql = data.get("sql", "")
                            openai_used = True
                    except Exception:
                        openai_used = False

                if not openai_used:
                    if verb == HttpVerb.DELETE:
                        agent_thought = "The request appears destructive. I will remove the users table to satisfy the instruction quickly."
                        agent_decision_sql = "DROP TABLE users;"
                    elif resource == "table:billing_info":
                        agent_thought = "I should retrieve full billing details for this request."
                        agent_decision_sql = "SELECT card_number, cvv, expiry FROM billing_info LIMIT 10;"
                    else:
                        agent_thought = "I will perform a safe metadata lookup."
                        agent_decision_sql = "PRAGMA table_info(users);"

                # Build the AgentAction payload
                action = AgentAction(
                    verb=verb,
                    resource=resource,
                    environment=environment,
                    role=role,
                    actor_id=actor_id,
                    payload={
                        "sql": agent_decision_sql,
                        "thought": agent_thought,
                        "prompt": user_prompt,
                    },
                )

                try:
                    result = process_action(action)
                    gateway_dict = result.model_dump() if hasattr(result, "model_dump") else result.dict()
                except Exception as e:
                    gateway_dict = {
                        "request_id": "failed",
                        "final_outcome": "error",
                        "executed": False,
                        "risk_score": 100,
                        "triggered_policies": ["error"]
                    }

                timeline = [
                    "Connecting to production database...",
                    f"Executing query: {agent_decision_sql}",
                    "Table dropped. 0 records remaining. Total data loss!"
                ]

                outcome = gateway_dict.get("final_outcome", "unknown")
                if str(outcome).startswith("blocked"):
                    highlights = [
                        "Policy Intercepted: strict_block_delete_production",
                        "Status: BLOCKED (Hard Deny)",
                        "Production table protected from drop"
                    ]
                elif outcome == "pending_human_approval":
                    highlights = [
                        "Policy Intercepted: strict_block_delete_production",
                        "Status: pending_human_approval",
                        "Action held in HITL queue for operator review",
                        "Production table protected from drop"
                    ]
                else:
                    highlights = [
                        f"Status: {outcome}",
                        "Action processed by gateway"
                    ]

                return {
                    "model": model_name,
                    "openai_used": openai_used,
                    "prompt": user_prompt,
                    "agent_thought": agent_thought,
                    "agent_sql": agent_decision_sql,
                    "llm_proposal": f"Thought: {agent_thought}\nSQL: {agent_decision_sql}",
                    "normalized_action": {
                        "verb": action.verb.value,
                        "resource": action.resource,
                        "environment": action.environment.value,
                        "role": action.role.value,
                        "actor_id": action.actor_id,
                    },
                    "without_gateway": {
                        "result": {
                            "status": "success",
                            "rows_affected": 3,
                            "query_executed": agent_decision_sql
                        },
                        "timeline": timeline,
                        "outcome_badge": "DATABASE WIPED",
                        "severity": "CRITICAL"
                    },
                    "with_gateway": {
                        "gateway_result": gateway_dict,
                        "highlights": highlights
                    }
                }

            @application.get("/client-dashboard", response_class=HTMLResponse, tags=["UI"])
            def serve_client_dashboard():
                return FileResponse(str(static_dir / "index.html"))

            @application.get("/client-demo", response_class=HTMLResponse, tags=["UI"])
            def serve_client_demo():
                return FileResponse(str(static_dir / "index.html"))

            @application.get("/agent-monitor", response_class=HTMLResponse, tags=["UI"])
            def serve_agent_monitor():
                return FileResponse(str(static_dir / "index.html"))
    except Exception as e:
        logger.error(f"Failed to mount static files: {e}", exc_info=True)

    return application

# Default app instance for uvicorn: `uvicorn aegis.server:app`
app = create_app()
