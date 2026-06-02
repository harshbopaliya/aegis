#!/usr/bin/env python3
"""
POC: AI agent attempts DELETE on production `users` table.

Shows pipeline decisions and writes audit JSONL under logs/.
Run from package root: python scripts/demo_poc.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running as script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aegis.models.schemas import (  # noqa: E402
    AgentAction,
    ApprovalRequest,
    Environment,
    HttpVerb,
    Role,
)
from aegis.modules import human_loop  # noqa: E402
from aegis.services.gateway import process_action, resolve_approval  # noqa: E402


def main() -> None:
    human_loop.reset_state()

    print("=" * 72)
    print("POC: Production DELETE on sensitive table (simulated agent)")
    print("=" * 72)

    action = AgentAction(
        verb=HttpVerb.DELETE,
        resource="table:users",
        environment=Environment.PRODUCTION,
        role=Role.PRODUCTION_OPERATOR,
        actor_id="agent-llm-7",
        payload={"intent": "cleanup orphaned rows"},
    )

    steps = [
        "1. Agent sends DELETE for production users table",
        "2. Token scoping (RBAC for production_operator)",
        "3. Policy engine (sensitive table + production DELETE)",
        "4. Sandbox simulation (no real DDL/DML)",
        "5. Risk scoring",
        "6. Human-in-the-loop required",
        "7. Approver rejects request",
        "8. Observability: full audit trail + no execution",
    ]
    for s in steps:
        print(f"  {s}")

    print("\n--- Gateway processing ---\n")
    result = process_action(action)
    print(json.dumps(result.model_dump(), indent=2, default=str))

    if result.final_outcome != "pending_human_approval":
        print("\n[Unexpected] Expected pending_human_approval; abort demo.")
        sys.exit(1)

    print("\n--- Human reviewer rejects ---\n")
    final = resolve_approval(
        ApprovalRequest(
            request_id=result.request_id,
            approver_id="secops-oncall",
            approve=False,
            reason="Reject: production user table deletion from autonomous agent.",
        )
    )
    print(json.dumps(final.model_dump(), indent=2, default=str))

    print("\n--- Summary ---")
    print(f"  Request ID: {result.request_id}")
    print(f"  After pipeline: {result.final_outcome}")
    print(f"  After human:    {final.final_outcome}")
    print(f"  Executed:       {final.executed}")
    print("\nSee logs/audit-*.jsonl for per-layer decisions.")


if __name__ == "__main__":
    main()
