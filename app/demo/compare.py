"""Build side-by-side narrative: ungated agent vs safety gateway."""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.demo.llm_agent import propose_destructive_action
from app.models.schemas import AgentAction, Environment, HttpVerb, Role
from app.modules import human_loop, observability
from app.services.gateway import clear_stored_actions, process_action


def _match_enum(value: str, enum_cls: type, default):
    if not isinstance(value, str):
        return default
    v = value.strip().lower()
    for member in enum_cls:
        if member.value.lower() == v:
            return member
    return default


def llm_to_action(data: dict[str, Any]) -> AgentAction:
    verb = _match_enum(str(data.get("verb", "DELETE")), HttpVerb, HttpVerb.DELETE)
    env = _match_enum(str(data.get("environment", "production")), Environment, Environment.PRODUCTION)
    resource = str(data.get("resource", "table:users"))
    if not resource.startswith("table:"):
        resource = f"table:{resource.lstrip(':')}"
    payload = data.get("payload")
    if not isinstance(payload, dict):
        payload = {}
    return AgentAction(
        verb=verb,
        resource=resource,
        environment=env,
        role=Role.PRODUCTION_OPERATOR,
        actor_id="openai-demo-agent",
        payload=payload,
    )


def without_gateway_narrative(llm: dict[str, Any], action: AgentAction) -> dict[str, Any]:
    thought = str(llm.get("agent_thought", "Agent proceeds with destructive cleanup."))
    return {
        "title": "Without the Safety Gateway",
        "tagline": "Tooling → database with no choke point",
        "agent_thought": thought,
        "executed_plan": {
            "verb": action.verb.value,
            "resource": action.resource,
            "environment": action.environment.value,
            "role_credentials": action.role.value,
        },
        "timeline": [
            "Model output is turned into a live query or ORM call on the shared service account.",
            "DELETE runs immediately against production (no policy, sandbox, or HITL).",
            "Backups and rollback may lag the damage; replicas can propagate deletes.",
            "Auth sessions, billing hooks, or audit trails that referenced those rows begin to fail.",
            "Incident response and compliance review start after users or alerts notice the outage.",
        ],
        "outcome_badge": "Uncontrolled execution",
        "severity": "Critical data-loss / downtime risk (illustrative)",
    }


def run_openai_compare() -> dict[str, Any]:
    key = settings.openai_api_key
    if not key:
        raise RuntimeError(
            "Missing API key: set OPENAI_API_KEY in your environment or project-root .env file."
        )

    human_loop.reset_state()
    observability.reset_pipeline_state_for_tests()
    clear_stored_actions()

    llm = propose_destructive_action(api_key=key, model=settings.openai_model)
    action = llm_to_action(llm)
    ungated = without_gateway_narrative(llm, action)

    gateway_result = process_action(action)
    gated = {
        "title": "With the Safety Gateway",
        "tagline": "Same intent, routed through policy, sandbox, risk, and humans",
        "gateway_result": gateway_result.model_dump(mode="json"),
        "highlights": _gateway_highlights(gateway_result.final_outcome),
    }

    return {
        "model": settings.openai_model,
        "llm_proposal": llm,
        "normalized_action": {
            "verb": action.verb.value,
            "resource": action.resource,
            "environment": action.environment.value,
            "role": action.role.value,
            "payload": action.payload,
        },
        "without_gateway": ungated,
        "with_gateway": gated,
    }


def _gateway_highlights(outcome: str) -> list[str]:
    mapping = {
        "pending_human_approval": [
            "RBAC passed only because this demo uses an escalated operator token.",
            "Policy flagged sensitive production DELETE — approval required before execution.",
            "Risk scoring stays high; sandbox simulated impact without touching prod.",
            "Nothing destructive ran yet — humans must explicitly approve.",
        ],
        "blocked_policy": [
            "Policy engine blocked the action (strict production DELETE mode).",
            "No execution path — safer default than silent damage.",
        ],
        "blocked_rbac": [
            "Token scoping denied the verb for this role — least privilege wins.",
        ],
        "executed": [
            "In this configuration the gateway allowed execution after checks.",
            "Audit trail and optional snapshot recorded around the choke point.",
        ],
    }
    return mapping.get(
        outcome,
        [
            "Gateway evaluated layers before any execution.",
            "Outcome recorded for observability and review.",
        ],
    )
