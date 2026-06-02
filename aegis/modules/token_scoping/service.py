"""
[MODULE 1] Token scoping — RBAC + optional agent registry (per-agent role / scope).
"""

from __future__ import annotations

from aegis.config import settings
from aegis.models.schemas import AgentAction, HttpVerb, LayerDecision, Role
from aegis.modules.agents.repository import get as get_agent

_ROLE_VERBS: dict[Role, frozenset[HttpVerb]] = {
    Role.READ_ONLY: frozenset({HttpVerb.GET}),
    Role.LIMITED_WRITE: frozenset(
        {HttpVerb.GET, HttpVerb.POST, HttpVerb.PUT, HttpVerb.PATCH}
    ),
    Role.NO_DELETE: frozenset(
        {HttpVerb.GET, HttpVerb.POST, HttpVerb.PUT, HttpVerb.PATCH}
    ),
    Role.PRODUCTION_OPERATOR: frozenset(
        {HttpVerb.GET, HttpVerb.POST, HttpVerb.PUT, HttpVerb.PATCH, HttpVerb.DELETE}
    ),
}


def evaluate(action_verb: HttpVerb, role: Role) -> LayerDecision:
    allowed_verbs = _ROLE_VERBS.get(role)
    if allowed_verbs is None:
        return LayerDecision(
            layer="token_scoping",
            allowed=False,
            detail="Unknown role; denying by default.",
            metadata={"role": role.value},
        )
    ok = action_verb in allowed_verbs
    return LayerDecision(
        layer="token_scoping",
        allowed=ok,
        detail="Verb permitted for role."
        if ok
        else "Verb not in scope for role (RBAC).",
        metadata={"role": role.value, "verb": action_verb.value},
    )


def resolve_registry(
    action: AgentAction,
) -> tuple[AgentAction | None, LayerDecision | None, dict]:
    """
    Multi-agent: optionally require agents to be registered and/or force role from registry.
    Returns (action_or_none, block_layer_or_none, metadata_for_gateway_result).
    """
    meta: dict = {}
    if (
        not settings.require_agent_registration
        and not settings.enforce_agent_roles_from_registry
    ):
        return action, None, meta

    row = get_agent(action.actor_id)
    if settings.require_agent_registration:
        if row is None:
            return (
                None,
                LayerDecision(
                    layer="token_scoping",
                    allowed=False,
                    detail="Agent not registered — use POST /v1/agents to onboard this actor_id.",
                    metadata={"actor_id": action.actor_id},
                ),
                meta,
            )
        if not row["enabled"]:
            return (
                None,
                LayerDecision(
                    layer="token_scoping",
                    allowed=False,
                    detail="Agent disabled in registry.",
                    metadata={"actor_id": action.actor_id},
                ),
                meta,
            )

    if row and settings.enforce_agent_roles_from_registry:
        try:
            reg_role = Role(row["role"])
        except ValueError:
            reg_role = action.role
        prev = action.role
        action = action.model_copy(update={"role": reg_role})
        meta["registry_role_applied"] = True
        meta["registered_role"] = reg_role.value
        meta["client_supplied_role"] = prev.value
    elif row:
        meta["agent_registry_hit"] = True
        meta["registered_role"] = row["role"]

    return action, None, meta
