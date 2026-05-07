"""Human-in-the-loop approval queue."""

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass, field


@dataclass
class PendingApproval:
    request_id: str
    approval_id: str
    summary: str
    created_at: float = field(default_factory=time.time)
    resolved: bool = False
    approved: bool | None = None
    approver_id: str | None = None


_lock = threading.Lock()
_pending: dict[str, PendingApproval] = {}
_decisions: dict[str, tuple[bool, str | None]] = {}


def enqueue(request_id: str, summary: str) -> str:
    approval_id = f"appr_{secrets.token_hex(6)}"
    with _lock:
        _pending[request_id] = PendingApproval(
            request_id=request_id,
            approval_id=approval_id,
            summary=summary,
        )
    return approval_id


def list_pending() -> list[dict]:
    with _lock:
        items = []
        for req_id, p in _pending.items():
            if p.resolved:
                continue
            items.append(
                {
                    "request_id": p.request_id,
                    "approval_id": p.approval_id,
                    "summary": p.summary,
                    "created_at": p.created_at,
                }
            )
        items.sort(key=lambda x: x["created_at"])
        return items


def resolve(request_id: str, approver_id: str, approve: bool, reason: str | None) -> bool:
    with _lock:
        p = _pending.get(request_id)
        if p is None:
            return False
        p.resolved = True
        p.approved = approve
        p.approver_id = approver_id
        _decisions[request_id] = (approve, reason)
        return True


def is_approved(request_id: str) -> bool | None:
    with _lock:
        d = _decisions.get(request_id)
        if d is None:
            return None
        return d[0]


def reset_state() -> None:
    with _lock:
        _pending.clear()
        _decisions.clear()
