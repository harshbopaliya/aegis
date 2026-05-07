"""
Orchestrates the safety pipeline: registry → token → policy → sandbox → risk → HITL → execution.

Fail-safe: deny execution when any layer blocks or human rejects.
"""

from __future__ import annotations

import threading
from typing import Any

from app.config import settings
from app.models.schemas import (
    AgentAction,
    ApprovalRequest,
    GatewayResult,
    HttpVerb,
    LayerDecision,
    PolicyDecision,
)
from app.modules import (
    backup_recovery,
    execution,
    human_loop,
    observability,
    policy_engine,
    risk_scoring,
    sandbox,
    token_scoping,
)

_ACTION_STORE: dict[str, AgentAction] = {}
_store_lock = threading.Lock()


def _store_action(request_id: str, action: AgentAction) -> None:
    with _store_lock:
        _ACTION_STORE[request_id] = action


def pop_action(request_id: str) -> AgentAction | None:
    with _store_lock:
        return _ACTION_STORE.pop(request_id, None)


def clear_stored_actions() -> None:
    with _store_lock:
        _ACTION_STORE.clear()


def process_action(action: AgentAction) -> GatewayResult:
    request_id = action.request_id or observability.new_request_id()
    action = action.model_copy(update={"request_id": request_id})
    actor = action.actor_id

    resolved, reg_block, reg_meta = token_scoping.resolve_registry(action)
    if reg_block:
        observability.pipeline_start(
            request_id,
            actor_id=actor,
            verb=action.verb.value,
            resource=action.resource,
            environment=action.environment.value,
        )
        observability.emit(
            "registry_gate",
            request_id,
            {"blocked": True, "detail": reg_block.detail},
            actor_id=actor,
        )
        observability.pipeline_advance(request_id, "agent_registry", reg_block.detail)
        observability.pipeline_set_status(request_id, "blocked_unregistered_agent")
        return GatewayResult(
            request_id=request_id,
            final_outcome="blocked_agent_registry",
            executed=False,
            layers=[reg_block],
            registry_metadata=reg_meta or None,
        )

    action = resolved

    observability.pipeline_start(
        request_id,
        actor_id=actor,
        verb=action.verb.value,
        resource=action.resource,
        environment=action.environment.value,
    )

    layers: list[LayerDecision] = []
    observability.emit(
        "request_received",
        request_id,
        {
            "verb": action.verb.value,
            "resource": action.resource,
            "role": action.role.value,
            "registry": reg_meta,
        },
        actor_id=actor,
    )

    # [1] Token scoping
    td = token_scoping.evaluate(action.verb, action.role)
    layers.append(td)
    observability.pipeline_advance(request_id, "token_scoping", td.detail)
    observability.emit("layer_token_scoping", request_id, td.model_dump(), actor_id=actor)
    if not td.allowed:
        observability.pipeline_set_status(request_id, "blocked_rbac")
        return GatewayResult(
            request_id=request_id,
            final_outcome="blocked_rbac",
            executed=False,
            layers=layers,
            registry_metadata=reg_meta or None,
        )

    # [2] Policy engine (DB rules + built-ins)
    pol_decision, pol_detail, pol_meta = policy_engine.evaluate(action)
    layers.append(
        LayerDecision(
            layer="policy_engine",
            allowed=pol_decision != PolicyDecision.BLOCK,
            detail=pol_detail,
            metadata={**pol_meta, "decision": pol_decision.value},
        )
    )
    observability.pipeline_advance(request_id, "policy_engine", pol_detail)
    observability.emit(
        "layer_policy",
        request_id,
        {"decision": pol_decision.value, "detail": pol_detail, "meta": pol_meta},
        actor_id=actor,
    )

    if pol_decision == PolicyDecision.BLOCK:
        observability.pipeline_set_status(request_id, "blocked_policy")
        return GatewayResult(
            request_id=request_id,
            final_outcome="blocked_policy",
            executed=False,
            layers=layers,
            policy_decision=pol_decision,
            registry_metadata=reg_meta or None,
        )

    # [3] Sandbox
    sb = sandbox.simulate(action)
    layers.append(
        LayerDecision(
            layer="sandbox",
            allowed=True,
            detail="Simulation complete (no side effects).",
            metadata=sb.model_dump(),
        )
    )
    observability.pipeline_advance(request_id, "sandbox_simulation", sb.predicted_outcome[:280])
    observability.emit("layer_sandbox", request_id, sb.model_dump(), actor_id=actor)

    # [4] Risk scoring
    risk = risk_scoring.score(action)
    layers.append(
        LayerDecision(
            layer="risk_scoring",
            allowed=True,
            detail=f"risk_score={risk.risk_score} level={risk.risk_level.value}",
            metadata=risk.model_dump(),
        )
    )
    observability.pipeline_advance(
        request_id,
        "risk_scoring",
        f"score={risk.risk_score} level={risk.risk_level.value}",
    )
    observability.emit("layer_risk", request_id, risk.model_dump(), actor_id=actor)

    needs_hitl = pol_decision == PolicyDecision.REQUIRE_APPROVAL or (
        risk.risk_score >= settings.risk_threshold_approval
    )

    # [5] Human-in-the-loop
    if needs_hitl:
        summary = (
            f"{action.verb.value} {action.resource} env={action.environment.value} "
            f"risk={risk.risk_score} policy={pol_decision.value}"
        )
        approval_id = human_loop.enqueue(request_id, summary)
        _store_action(request_id, action)
        observability.pipeline_touch_approval_wait(request_id, summary)
        observability.emit(
            "human_approval_required",
            request_id,
            {"approval_id": approval_id, "summary": summary},
            actor_id=actor,
        )
        return GatewayResult(
            request_id=request_id,
            final_outcome="pending_human_approval",
            executed=False,
            approval_id=approval_id,
            layers=layers,
            policy_decision=pol_decision,
            risk=risk,
            sandbox=sb,
            registry_metadata=reg_meta or None,
        )

    backup_id: str | None = None
    if action.verb != HttpVerb.GET:
        backup_id = backup_recovery.snapshot(
            reason=f"before_{action.verb.value}", request_id=request_id
        )
        observability.pipeline_advance(request_id, "backup_snapshot", backup_id)
        observability.emit("backup_snapshot", request_id, {"snapshot_id": backup_id}, actor_id=actor)

    observability.pipeline_advance(request_id, "execution", "invoking_execution_layer")
    ex: dict[str, Any] = execution.execute(action)
    observability.emit(
        "executed",
        request_id,
        {"result": ex, "backup_snapshot_id": backup_id},
        actor_id=actor,
    )
    observability.pipeline_set_status(request_id, "executed")

    return GatewayResult(
        request_id=request_id,
        final_outcome="executed",
        executed=True,
        layers=layers,
        policy_decision=pol_decision,
        risk=risk,
        sandbox=sb,
        execution_result=ex,
        backup_snapshot_id=backup_id,
        registry_metadata=reg_meta or None,
    )


def resolve_approval(body: ApprovalRequest) -> GatewayResult:
    ok = human_loop.resolve(body.request_id, body.approver_id, body.approve, body.reason)
    if not ok:
        observability.emit("approval_unknown_request", body.request_id, {}, actor_id=body.approver_id)
        return GatewayResult(
            request_id=body.request_id,
            final_outcome="approval_request_not_found",
            executed=False,
            layers=[],
        )

    observability.emit(
        "human_decision",
        body.request_id,
        {"approve": body.approve, "approver": body.approver_id, "reason": body.reason},
        actor_id=body.approver_id,
    )

    if not body.approve:
        pop_action(body.request_id)
        observability.pipeline_set_status(body.request_id, "rejected_by_human")
        return GatewayResult(
            request_id=body.request_id,
            final_outcome="rejected_by_human",
            executed=False,
            layers=[],
        )

    action = pop_action(body.request_id)
    if action is None:
        observability.pipeline_set_status(body.request_id, "action_expired")
        return GatewayResult(
            request_id=body.request_id,
            final_outcome="action_expired",
            executed=False,
            layers=[],
        )

    actor = action.actor_id
    backup_id = None
    if action.verb != HttpVerb.GET:
        backup_id = backup_recovery.snapshot(
            reason=f"approved_before_{action.verb.value}", request_id=body.request_id
        )

    observability.pipeline_advance(body.request_id, "backup_snapshot", backup_id or "skipped_read_only")
    observability.pipeline_advance(body.request_id, "execution", "post_human_approval")
    ex = execution.execute(action)
    observability.emit(
        "executed_after_approval",
        body.request_id,
        {"result": ex, "snapshot_id": backup_id},
        actor_id=actor,
    )
    observability.pipeline_set_status(body.request_id, "executed_after_approval")

    return GatewayResult(
        request_id=body.request_id,
        final_outcome="executed_after_approval",
        executed=True,
        layers=[],
        execution_result=ex,
        backup_snapshot_id=backup_id,
    )
