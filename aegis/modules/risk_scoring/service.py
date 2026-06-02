"""Risk scoring 0–100."""

from __future__ import annotations

from aegis.config import settings
from aegis.models.schemas import (
    AgentAction,
    Environment,
    HttpVerb,
    RiskLevel,
    RiskScoreResult,
)


def score(action: AgentAction) -> RiskScoreResult:
    factors: list[str] = []
    base = 10

    if action.verb == HttpVerb.GET:
        base = 10
        factors.append("READ operation baseline")
    elif action.verb in (HttpVerb.POST, HttpVerb.PUT, HttpVerb.PATCH):
        base = 50
        factors.append("UPDATE-class operation baseline")
    elif action.verb == HttpVerb.DELETE:
        base = 92
        factors.append("DELETE operation baseline (critical)")

    if action.environment == Environment.PRODUCTION:
        base = min(100, base + 5)
        factors.append("production environment modifier")

    resource_lower = action.resource.lower()
    if any(s in resource_lower for s in ("user", "payment", "prod")):
        base = min(100, base + 3)
        factors.append("sensitive resource hint")

    if "payments" in resource_lower or "users" in resource_lower:
        base = min(100, base + 5)
        factors.append("high-value data surface")

    risk_score = max(0, min(100, base))
    if risk_score < 40:
        level = RiskLevel.LOW
    elif risk_score < settings.risk_threshold_approval:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.HIGH

    return RiskScoreResult(
        risk_score=risk_score, risk_level=level, factors=factors
    )
