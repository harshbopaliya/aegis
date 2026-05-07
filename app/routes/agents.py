"""Multi-agent registry and token scoping (per-agent role)."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from app.models.schemas import AgentCreate, AgentOut, AgentUpdate
from app.modules.agents import repository as agents_repo

router = APIRouter(prefix="/v1/agents", tags=["agents"])


def _to_out(row: dict) -> AgentOut:
    return AgentOut(
        agent_id=row["agent_id"],
        display_name=row["display_name"],
        description=row["description"],
        role=row["role"],
        enabled=row["enabled"],
        labels=row.get("labels"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("")
def list_agents(enabled_only: bool = False):
    rows = agents_repo.list_agents(enabled_only=enabled_only)
    return {"agents": [_to_out(r).model_dump() for r in rows]}


@router.post("", status_code=201)
def create_agent(body: AgentCreate):
    row = agents_repo.upsert(
        agent_id=body.agent_id.strip(),
        display_name=body.display_name,
        description=body.description,
        role=body.role.value,
        enabled=body.enabled,
        labels=body.labels or {},
    )
    return _to_out(row)


@router.patch("/{agent_id}")
def patch_agent(agent_id: str, body: AgentUpdate):
    fields = {}
    if body.display_name is not None:
        fields["display_name"] = body.display_name
    if body.description is not None:
        fields["description"] = body.description
    if body.role is not None:
        fields["role"] = body.role.value
    if body.enabled is not None:
        fields["enabled"] = body.enabled
    if body.labels is not None:
        fields["labels"] = body.labels
    row = agents_repo.update_partial(agent_id, fields)
    if not row:
        raise HTTPException(status_code=404, detail="agent not found")
    return _to_out(row)


@router.delete("/{agent_id}", status_code=204)
def delete_agent(agent_id: str):
    if not agents_repo.delete_agent(agent_id):
        raise HTTPException(status_code=404, detail="agent not found")


@router.get("/{agent_id}")
def get_agent(agent_id: str):
    row = agents_repo.get(agent_id)
    if not row:
        raise HTTPException(status_code=404, detail="agent not found")
    return _to_out(row).model_dump()
