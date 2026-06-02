"""
Execution layer — single choke point for controlled data access.

Replace this module with your production connectors; keep the gateway contract.
Users should implement ``aegis.adapters.base.ExecutionBackend`` for custom backends.
"""

from __future__ import annotations

from typing import Any

from aegis.adapters import get_execution
from aegis.models.schemas import AgentAction


def execute(action: AgentAction) -> dict[str, Any]:
    """
    Controlled execution: delegating to the active execution backend.
    """
    return get_execution().execute(action)
