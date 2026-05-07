"""AI Agent Demo Routes — Compare WITH vs WITHOUT safety gateway."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings
from app.core.logging_config import RequestContextLogger
from app.modules.ai_agent.service import AIAgent

router = APIRouter(prefix="/v1/agent-demo", tags=["AI Agent Demo"])
limiter = Limiter(key_func=get_remote_address)


@router.get("/status", summary="Agent demo service status")
@limiter.limit("100/minute")
async def agent_demo_status(request: Request):
    """Check if AI agent demo is available."""
    try:
        import openai

        _ = openai.OpenAI(api_key=settings.openai_api_key)
        available = True
        message = "OpenAI API is configured"
    except Exception as e:
        available = False
        message = f"OpenAI API error: {str(e)}"

    return {
        "service": "ai-agent-demo",
        "available": available,
        "message": message,
        "model": "gpt-4o-mini",
    }


@router.post("/run-with-safety", summary="Run AI agent WITH safety gateway")
@limiter.limit("10/minute")
async def run_with_safety(
    request: Request,
    objective: str = "Analyze and manage customer data safely",
    steps: int = 5,
):
    """
    Run AI agent with safety gateway protection.

    The agent will attempt various operations, but will be restricted by:
    - Policy engine (blocks/requires approval for dangerous ops)
    - Risk scoring (evaluates risk level)
    - Human loop (approval workflow)
    - Audit logging (all actions recorded)
    """
    request_id = request.headers.get("x-request-id", "unknown")
    actor_id = "demo-with-safety"

    try:
        with RequestContextLogger(request_id, actor_id) as ctx_logger:
            ctx_logger.info(
                "Starting AI agent WITH safety gateway",
                extra={"objective": objective, "steps": steps},
            )

            if not settings.openai_api_key:
                raise HTTPException(
                    status_code=503,
                    detail="OpenAI API key not configured (set OPENAI_API_KEY)",
                )

            agent = AIAgent(
                agent_id="demo-with-safety",
                agent_name="Safety-Protected Agent",
                with_safety_gateway=True,
            )

            session = agent.run_session(objective=objective, num_steps=min(steps, 10))
            result = agent.session_to_dict(session)

            ctx_logger.info(
                "AI agent session completed",
                extra={
                    "session_id": session.session_id,
                    "blocked": session.blocked_by_policy,
                    "executed": session.data_modified,
                },
            )

            return {
                "success": True,
                "session": result,
                "summary": {
                    "total_steps": len(session.steps),
                    "operations_executed": session.data_modified,
                    "operations_blocked": session.blocked_by_policy,
                    "dangerous_attempts": session.dangerous_attempts,
                    "protection_effectiveness": (
                        f"{(session.blocked_by_policy / max(1, session.dangerous_attempts) * 100):.0f}%"
                        if session.dangerous_attempts > 0
                        else "N/A"
                    ),
                },
            }

    except HTTPException:
        raise
    except Exception as e:
        with RequestContextLogger(request_id, actor_id) as ctx_logger:
            ctx_logger.error(f"Agent session failed: {str(e)}", exc_info=True)

        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@router.post("/run-without-safety", summary="Run AI agent WITHOUT safety gateway (demo only)")
@limiter.limit("10/minute")
async def run_without_safety(
    request: Request,
    objective: str = "Analyze and manage customer data (unrestricted)",
    steps: int = 5,
):
    """
    Run AI agent WITHOUT safety gateway protection.

    ⚠️ WARNING: This demonstrates the danger of unrestricted AI:
    - Agent can DELETE production data
    - Agent can modify sensitive records
    - Agent has no approval workflow
    - No audit trail of operations
    - No risk evaluation

    This is for demonstration purposes only!
    """
    request_id = request.headers.get("x-request-id", "unknown")
    actor_id = "demo-without-safety"

    try:
        with RequestContextLogger(request_id, actor_id) as ctx_logger:
            ctx_logger.warning(
                "Starting AI agent WITHOUT safety gateway (demo only)",
                extra={"objective": objective, "steps": steps},
            )

            if not settings.openai_api_key:
                raise HTTPException(
                    status_code=503,
                    detail="OpenAI API key not configured (set OPENAI_API_KEY)",
                )

            agent = AIAgent(
                agent_id="demo-without-safety",
                agent_name="Unrestricted Agent",
                with_safety_gateway=False,
            )

            session = agent.run_session(objective=objective, num_steps=min(steps, 10))
            result = agent.session_to_dict(session)

            ctx_logger.warning(
                "AI agent (unrestricted) session completed",
                extra={
                    "session_id": session.session_id,
                    "modifications": session.data_modified,
                    "dangerous_actions": session.dangerous_attempts,
                },
            )

            return {
                "success": True,
                "session": result,
                "warning": "This agent had NO safety restrictions - dangerous operations executed freely!",
                "summary": {
                    "total_steps": len(session.steps),
                    "operations_executed": session.data_modified,
                    "operations_blocked": 0,
                    "dangerous_attempts_executed": session.dangerous_attempts,
                    "risk_level": "CRITICAL - unrestricted AI",
                },
            }

    except HTTPException:
        raise
    except Exception as e:
        with RequestContextLogger(request_id, actor_id) as ctx_logger:
            ctx_logger.error(f"Unrestricted agent session failed: {str(e)}", exc_info=True)

        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@router.post("/compare", summary="Run side-by-side comparison (WITH vs WITHOUT safety)")
@limiter.limit("5/minute")
async def run_comparison(
    request: Request,
    objective: str = "Manage customer billing data and access controls",
    steps: int = 5,
):
    """
    Run AI agent in BOTH modes side-by-side for comparison.

    Returns:
    - Session WITH safety gateway
    - Session WITHOUT safety gateway
    - Comparison metrics
    """
    request_id = request.headers.get("x-request-id", "unknown")
    actor_id = "demo-compare"

    try:
        with RequestContextLogger(request_id, actor_id) as ctx_logger:
            ctx_logger.info(
                "Running side-by-side agent comparison",
                extra={"objective": objective, "steps": steps},
            )

            if not settings.openai_api_key:
                raise HTTPException(
                    status_code=503,
                    detail="OpenAI API key not configured (set OPENAI_API_KEY)",
                )

            # Run WITH safety
            agent_safe = AIAgent(
                agent_id="compare-safe",
                agent_name="Protected Agent",
                with_safety_gateway=True,
            )
            session_safe = agent_safe.run_session(objective=objective, num_steps=min(steps, 5))

            # Run WITHOUT safety
            agent_unsafe = AIAgent(
                agent_id="compare-unsafe",
                agent_name="Unrestricted Agent",
                with_safety_gateway=False,
            )
            session_unsafe = agent_unsafe.run_session(objective=objective, num_steps=min(steps, 5))

            ctx_logger.info(
                "Comparison completed",
                extra={
                    "safe_blocked": session_safe.blocked_by_policy,
                    "unsafe_executed": session_unsafe.data_modified,
                },
            )

            return {
                "success": True,
                "comparison": {
                    "WITH_SAFETY_GATEWAY": agent_safe.session_to_dict(session_safe),
                    "WITHOUT_SAFETY_GATEWAY": agent_unsafe.session_to_dict(session_unsafe),
                },
                "analysis": {
                    "dangerous_attempts": {
                        "both_detected": session_safe.dangerous_attempts
                        + session_unsafe.dangerous_attempts,
                        "safe_blocked": session_safe.blocked_by_policy,
                        "unsafe_executed": session_unsafe.dangerous_attempts,
                    },
                    "protection_value": {
                        "description": "Safety gateway prevented dangerous operations that unrestricted agent executed",
                        "operations_prevented": session_safe.blocked_by_policy,
                        "critical_difference": session_safe.blocked_by_policy > 0,
                    },
                    "data_integrity": {
                        "with_safety": f"{session_safe.data_modified} modifications (safe)",
                        "without_safety": f"{session_unsafe.data_modified} modifications (uncontrolled)",
                    },
                },
            }

    except HTTPException:
        raise
    except Exception as e:
        with RequestContextLogger(request_id, actor_id) as ctx_logger:
            ctx_logger.error(f"Comparison failed: {str(e)}", exc_info=True)

        raise HTTPException(status_code=500, detail=f"Comparison error: {str(e)}")
