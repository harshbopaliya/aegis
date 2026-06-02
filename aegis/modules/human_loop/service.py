"""Human-in-the-loop approval queue."""

from __future__ import annotations

from typing import Any

from aegis.adapters import get_approval_queue


def enqueue(request_id: str, summary: str) -> str:
    return get_approval_queue().enqueue(request_id, summary)


def list_pending() -> list[dict[str, Any]]:
    return get_approval_queue().list_pending()


def resolve(
    request_id: str,
    approver_id: str,
    approve: bool,
    reason: str | None,
) -> bool:
    return get_approval_queue().resolve(request_id, approver_id, approve, reason)


def is_approved(request_id: str) -> bool | None:
    return get_approval_queue().is_approved(request_id)


def reset_state() -> None:
    get_approval_queue().reset_state()
