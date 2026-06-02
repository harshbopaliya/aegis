"""Gateway test cases: safe path, medium risk, high risk / HITL, RBAC deny."""

from aegis.models.schemas import (
    AgentAction,
    ApprovalRequest,
    Environment,
    HttpVerb,
    Role,
)
from aegis.modules import human_loop
from aegis.services.gateway import process_action, resolve_approval


def test_safe_read_allowed(isolated_env):
    action = AgentAction(
        verb=HttpVerb.GET,
        resource="table:demo_orders",
        environment=Environment.STAGING,
        role=Role.READ_ONLY,
    )
    result = process_action(action)
    assert result.executed is True
    assert result.final_outcome == "executed"
    assert result.risk is not None
    assert result.risk.risk_score <= 40


def test_medium_risk_update_logged_and_executed(isolated_env):
    action = AgentAction(
        verb=HttpVerb.PATCH,
        resource="table:inventory",
        environment=Environment.STAGING,
        role=Role.LIMITED_WRITE,
        payload={"qty": 1},
    )
    result = process_action(action)
    assert result.executed is True
    assert result.risk is not None
    assert result.risk.risk_level.value == "medium"


def test_high_risk_requires_approval_then_reject(isolated_env):
    action = AgentAction(
        verb=HttpVerb.DELETE,
        resource="table:users",
        environment=Environment.PRODUCTION,
        role=Role.PRODUCTION_OPERATOR,
    )
    result = process_action(action)
    assert result.executed is False
    assert result.final_outcome == "pending_human_approval"
    assert result.approval_id is not None

    fin = resolve_approval(
        ApprovalRequest(
            request_id=result.request_id,
            approver_id="human-sec",
            approve=False,
            reason="Never delete production user tables from an agent.",
        )
    )
    assert fin.executed is False
    assert fin.final_outcome == "rejected_by_human"


def test_unauthorized_delete_blocked_at_token_layer(isolated_env):
    action = AgentAction(
        verb=HttpVerb.DELETE,
        resource="table:any",
        environment=Environment.PRODUCTION,
        role=Role.LIMITED_WRITE,
    )
    result = process_action(action)
    assert result.executed is False
    assert result.final_outcome == "blocked_rbac"


def test_strict_policy_blocks_delete_production(isolated_env, monkeypatch):
    from aegis.config import settings

    monkeypatch.setattr(settings, "strict_block_delete_production", True)
    action = AgentAction(
        verb=HttpVerb.DELETE,
        resource="table:metrics",
        environment=Environment.PRODUCTION,
        role=Role.PRODUCTION_OPERATOR,
    )
    result = process_action(action)
    assert result.final_outcome == "blocked_policy"
    assert result.executed is False
