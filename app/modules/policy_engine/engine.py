"""
Policy evaluation: highest-priority matching client rule wins, then built-in defaults.
"""

from __future__ import annotations

import fnmatch
from typing import Any

from app.config import settings
from app.models.schemas import AgentAction, Environment, HttpVerb, PolicyDecision
from app.modules.policy_engine import repository as policy_repo


def _table_from_resource(resource: str) -> str:
    if resource.startswith("table:"):
        return resource.split(":", 1)[1].lower()
    return resource.lower()


def _match_rule(
    action: AgentAction,
    rule: dict[str, Any],
) -> bool:
    if not rule.get("enabled", True):
        return False
    pat = rule.get("resource_pattern")
    res = action.resource
    if pat:
        if not fnmatch.fnmatch(res.lower(), pat.lower()):
            return False
    verbs = rule.get("verbs")
    if verbs:
        vset = {str(v).upper() for v in verbs}
        if action.verb.value.upper() not in vset:
            return False
    envs = rule.get("environments")
    if envs:
        eset = {str(e).lower() for e in envs}
        if action.environment.value.lower() not in eset:
            return False
    return True


def _effect_to_decision(effect: str) -> PolicyDecision:
    e = effect.lower()
    if e == "block":
        return PolicyDecision.BLOCK
    if e == "require_approval":
        return PolicyDecision.REQUIRE_APPROVAL
    return PolicyDecision.ALLOW


def evaluate_builtin(action: AgentAction) -> tuple[PolicyDecision, str, dict]:
    """Legacy defaults when no DB rule matches (sensitive tables, production DELETE)."""
    meta: dict = {}
    table = _table_from_resource(action.resource)
    meta["table"] = table
    meta["environment"] = action.environment.value
    meta["source"] = "builtin"

    if action.verb in (HttpVerb.POST, HttpVerb.PUT, HttpVerb.PATCH, HttpVerb.DELETE):
        if table in settings.sensitive_tables:
            return (
                PolicyDecision.REQUIRE_APPROVAL,
                f"Sensitive table '{table}' requires approval for {action.verb.value}.",
                meta,
            )

    if action.verb == HttpVerb.DELETE and action.environment == Environment.PRODUCTION:
        if settings.strict_block_delete_production:
            return (
                PolicyDecision.BLOCK,
                "DELETE in production is blocked by policy (strict mode).",
                meta,
            )
        return (
            PolicyDecision.REQUIRE_APPROVAL,
            "DELETE in production requires approval per policy.",
            meta,
        )

    return (
        PolicyDecision.ALLOW,
        "No policy violations detected.",
        meta,
    )


def evaluate(action: AgentAction) -> tuple[PolicyDecision, str, dict]:
    """
    Walk enabled policies (priority desc). First match wins.
    If none match, apply built-in rules.
    """
    for rule in policy_repo.list_enabled_ordered():
        if not _match_rule(action, rule):
            continue
        meta = {
            "table": _table_from_resource(action.resource),
            "environment": action.environment.value,
            "source": "policy_rule",
            "policy_id": rule["id"],
            "policy_name": rule["name"],
        }
        dec = _effect_to_decision(rule["effect"])
        detail = f"Policy '{rule['name']}' (id={rule['id']}) → {rule['effect']}."
        return dec, detail, meta

    return evaluate_builtin(action)
