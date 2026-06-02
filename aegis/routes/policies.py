"""Policy management API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from aegis.core.auth import require_admin
from aegis.models.schemas import PolicyCreate, PolicyOut, PolicyUpdate
from aegis.modules.policy_engine import repository as policy_repo

router = APIRouter()


@router.get("/", response_model=list[PolicyOut])
def list_policies(_role: str = Depends(require_admin)):
    """List all policies."""
    return policy_repo.list_all()


@router.post("/", response_model=PolicyOut, status_code=status.HTTP_201_CREATED)
def create_policy(body: PolicyCreate, _role: str = Depends(require_admin)):
    """Create a new policy."""
    return policy_repo.create(
        name=body.name,
        effect=body.effect.value,
        description=body.description,
        priority=body.priority,
        enabled=body.enabled,
        resource_pattern=body.resource_pattern,
        verbs=body.verbs,
        environments=body.environments,
    )


@router.get("/{policy_id}", response_model=PolicyOut)
def get_policy(policy_id: int, _role: str = Depends(require_admin)):
    """Get a specific policy."""
    row = policy_repo.get(policy_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy {policy_id} not found",
        )
    return row


@router.patch("/{policy_id}", response_model=PolicyOut)
def update_policy(
    policy_id: int,
    body: PolicyUpdate,
    _role: str = Depends(require_admin),
):
    """Partially update a policy."""
    fields = body.model_dump(exclude_unset=True)
    updated = policy_repo.update(policy_id, fields)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy {policy_id} not found",
        )
    return updated


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy(
    policy_id: int, _role: str = Depends(require_admin)
):
    """Delete a policy."""
    ok = policy_repo.delete_policy(policy_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy {policy_id} not found",
        )
