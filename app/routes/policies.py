"""Customer-managed policy rules (policy machine)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import PolicyCreate, PolicyOut, PolicyUpdate
from app.modules.policy_engine import repository as policy_repo

router = APIRouter(prefix="/v1/policies", tags=["policies"])


def _to_out(row: dict) -> PolicyOut:
    return PolicyOut(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        priority=row["priority"],
        enabled=row["enabled"],
        resource_pattern=row["resource_pattern"],
        verbs=row["verbs"],
        environments=row["environments"],
        effect=row["effect"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("")
def list_policies(include_disabled: bool = True):
    rows = policy_repo.list_policies(include_disabled=include_disabled)
    return {"policies": [_to_out(r).model_dump() for r in rows]}


@router.post("", status_code=201)
def create_policy(body: PolicyCreate):
    row = policy_repo.create_policy(
        name=body.name,
        description=body.description,
        priority=body.priority,
        enabled=body.enabled,
        resource_pattern=body.resource_pattern,
        verbs=[v.upper() for v in body.verbs] if body.verbs else None,
        environments=[e.lower() for e in body.environments] if body.environments else None,
        effect=body.effect.value,
    )
    return _to_out(row)


@router.patch("/{policy_id}")
def patch_policy(policy_id: int, body: PolicyUpdate):
    fields: dict = {}
    if body.name is not None:
        fields["name"] = body.name
    if body.description is not None:
        fields["description"] = body.description
    if body.priority is not None:
        fields["priority"] = body.priority
    if body.enabled is not None:
        fields["enabled"] = body.enabled
    if body.resource_pattern is not None:
        fields["resource_pattern"] = body.resource_pattern
    if body.verbs is not None:
        fields["verbs"] = [v.upper() for v in body.verbs]
    if body.environments is not None:
        fields["environments"] = [e.lower() for e in body.environments]
    if body.effect is not None:
        fields["effect"] = body.effect.value
    row = policy_repo.update_policy(policy_id, fields)
    if not row:
        raise HTTPException(status_code=404, detail="policy not found")
    return _to_out(row)


@router.delete("/{policy_id}", status_code=204)
def delete_policy(policy_id: int):
    if not policy_repo.delete_policy(policy_id):
        raise HTTPException(status_code=404, detail="policy not found")
