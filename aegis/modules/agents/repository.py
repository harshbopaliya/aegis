"""Persistent agent registry — maps agent_id → bound Role (token scope at identity layer)."""

from __future__ import annotations

from typing import Any

from aegis.adapters import get_storage


def get(agent_id: str) -> dict[str, Any] | None:
    return get_storage().get_agent(agent_id)


def list_agents(enabled_only: bool = False) -> list[dict[str, Any]]:
    return get_storage().list_agents(enabled_only)


def upsert(
    agent_id: str,
    display_name: str,
    description: str | None,
    role: str,
    enabled: bool,
    labels: dict[str, str] | None,
) -> dict[str, Any]:
    return get_storage().upsert_agent(
        agent_id=agent_id,
        display_name=display_name,
        description=description,
        role=role,
        enabled=enabled,
        labels=labels,
    )


def update_partial(
    agent_id: str, fields: dict[str, Any]
) -> dict[str, Any] | None:
    row = get(agent_id)
    if not row:
        return None
    display_name = fields.get("display_name", row["display_name"])
    description = fields.get("description", row["description"])
    role = fields.get("role", row["role"])
    enabled = fields.get("enabled", row["enabled"])
    labels = fields.get("labels", row["labels"])
    role_str = role.value if hasattr(role, "value") else str(role)
    return upsert(
        agent_id,
        str(display_name),
        description,
        role_str,
        bool(enabled),
        labels if isinstance(labels, dict) else row["labels"],
    )


def delete_agent(agent_id: str) -> bool:
    return get_storage().delete_agent(agent_id)


def clear_all_for_tests() -> None:
    get_storage().clear_agents()
