"""Policy rule persistence."""

from __future__ import annotations

from typing import Any

from aegis.adapters import get_storage


def list_all() -> list[dict[str, Any]]:
    return get_storage().list_all_policies()


def list_enabled_ordered() -> list[dict[str, Any]]:
    return get_storage().list_enabled_policies_ordered()


def get(policy_id: int) -> dict[str, Any] | None:
    return get_storage().get_policy(policy_id)


def create(
    name: str,
    effect: str,
    description: str | None = None,
    priority: int = 100,
    enabled: bool = True,
    resource_pattern: str | None = None,
    verbs: list[str] | None = None,
    environments: list[str] | None = None,
) -> dict[str, Any]:
    return get_storage().create_policy(
        name=name,
        effect=effect,
        description=description,
        priority=priority,
        enabled=enabled,
        resource_pattern=resource_pattern,
        verbs=verbs,
        environments=environments,
    )


def update(policy_id: int, fields: dict[str, Any]) -> dict[str, Any] | None:
    return get_storage().update_policy(policy_id, fields)


def delete_policy(policy_id: int) -> bool:
    return get_storage().delete_policy(policy_id)


def clear_all_for_tests() -> None:
    get_storage().clear_policies()
