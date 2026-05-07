"""Sandbox / simulation — no production side effects."""

from __future__ import annotations

import hashlib

from app.models.schemas import AgentAction, HttpVerb, SandboxResult


def simulate(action: AgentAction) -> SandboxResult:
    resource_key = f"{action.environment.value}:{action.resource}:{action.verb.value}"
    digest = int(hashlib.sha256(resource_key.encode()).hexdigest()[:8], 16)
    pseudo_rows = (digest % 50) + 1

    if action.verb == HttpVerb.DELETE:
        return SandboxResult(
            simulated=True,
            predicted_outcome=(
                f"Would DROP/TRUNCATE target derived from '{action.resource}' "
                f"in {action.environment.value}; estimated {pseudo_rows} rows affected."
            ),
            would_affect_rows=pseudo_rows,
            side_effects=["indexes would be invalidated", "dependent FK checks would run"],
        )
    if action.verb in (HttpVerb.POST, HttpVerb.PUT, HttpVerb.PATCH):
        return SandboxResult(
            simulated=True,
            predicted_outcome=f"Would apply mutation to '{action.resource}' (validated schema pass).",
            would_affect_rows=1,
            side_effects=["row-level lock simulation"],
        )
    return SandboxResult(
        simulated=True,
        predicted_outcome=f"Would read '{action.resource}' with no state change.",
        would_affect_rows=0,
        side_effects=[],
    )
