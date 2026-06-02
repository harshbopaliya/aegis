"""Agent registry — persistent storage for registered agents."""

from aegis.modules.agents.repository import (
    clear_all_for_tests,
    delete_agent,
    get,
    list_agents,
    update_partial,
    upsert,
)

__all__ = [
    "clear_all_for_tests",
    "delete_agent",
    "get",
    "list_agents",
    "update_partial",
    "upsert",
]
