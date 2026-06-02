"""Agent registry API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from aegis.core.auth import require_admin
from aegis.models.schemas import AgentCreate, AgentOut, AgentUpdate
from aegis.modules.agents import repository as agent_repo

router = APIRouter()


@router.get("/", response_model=list[AgentOut])
def list_agents(_role: str = Depends(require_admin)):
    """List all registered agents."""
    return agent_repo.list_agents()


@router.post("/", response_model=AgentOut, status_code=status.HTTP_201_CREATED)
def register_agent(body: AgentCreate, _role: str = Depends(require_admin)):
    """Register a new agent or update existing."""
    return agent_repo.upsert(
        agent_id=body.agent_id,
        display_name=body.display_name,
        description=body.description,
        role=body.role.value,
        enabled=body.enabled,
        labels=body.labels,
    )


@router.get("/{agent_id}", response_model=AgentOut)
def get_agent(agent_id: str, _role: str = Depends(require_admin)):
    """Get a specific agent."""
    row = agent_repo.get(agent_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )
    return row


@router.patch("/{agent_id}", response_model=AgentOut)
def update_agent(
    agent_id: str,
    body: AgentUpdate,
    _role: str = Depends(require_admin),
):
    """Partially update an agent."""
    fields = body.model_dump(exclude_unset=True)
    updated = agent_repo.update_partial(agent_id, fields)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )
    return updated


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(agent_id: str, _role: str = Depends(require_admin)):
    """Delete an agent."""
    ok = agent_repo.delete_agent(agent_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )
