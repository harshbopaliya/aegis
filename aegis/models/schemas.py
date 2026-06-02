from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class HttpVerb(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Role(str, Enum):
    READ_ONLY = "read_only"
    LIMITED_WRITE = "limited_write"
    NO_DELETE = "no_delete"
    # Escalated path for lab/demo: DELETE allowed at RBAC but downstream gates apply.
    PRODUCTION_OPERATOR = "production_operator"


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    REQUIRE_APPROVAL = "require_approval"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LayerDecision(BaseModel):
    layer: str
    allowed: bool
    detail: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentAction(BaseModel):
    """Action proposed by an AI agent (never executed raw)."""

    verb: HttpVerb
    resource: str = Field(
        ..., description="Logical resource, e.g. table:name or api:/orders"
    )
    environment: Environment = Environment.DEVELOPMENT
    role: Role
    actor_id: str = "agent-001"
    payload: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = None


class RiskScoreResult(BaseModel):
    risk_score: int = Field(ge=0, le=100)
    risk_level: RiskLevel
    factors: list[str] = Field(default_factory=list)


class SandboxResult(BaseModel):
    simulated: bool = True
    predicted_outcome: str
    would_affect_rows: int | None = None
    side_effects: list[str] = Field(default_factory=list)


class ApprovalRequest(BaseModel):
    request_id: str
    approver_id: str
    approve: bool
    reason: str | None = None


class PolicyEffect(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    REQUIRE_APPROVAL = "require_approval"


class PolicyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    priority: int = Field(default=100, ge=0, le=1_000_000)
    enabled: bool = True
    resource_pattern: str | None = Field(
        default=None,
        description="Glob pattern, e.g. table:payments or api:/admin/*",
    )
    verbs: list[str] | None = Field(
        default=None, description="If set, action verb must be in list."
    )
    environments: list[str] | None = Field(
        default=None, description="If set, environment must match."
    )
    effect: PolicyEffect


class PolicyUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    priority: int | None = Field(default=None, ge=0, le=1_000_000)
    enabled: bool | None = None
    resource_pattern: str | None = None
    verbs: list[str] | None = None
    environments: list[str] | None = None
    effect: PolicyEffect | None = None


class PolicyOut(BaseModel):
    id: int
    name: str
    description: str | None
    priority: int
    enabled: bool
    resource_pattern: str | None
    verbs: list[str] | None
    environments: list[str] | None
    effect: str
    created_at: str
    updated_at: str


class AgentCreate(BaseModel):
    agent_id: str = Field(..., min_length=1, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    role: Role
    enabled: bool = True
    labels: dict[str, str] | None = None


class AgentUpdate(BaseModel):
    display_name: str | None = None
    description: str | None = None
    role: Role | None = None
    enabled: bool | None = None
    labels: dict[str, str] | None = None


class AgentOut(BaseModel):
    agent_id: str
    display_name: str
    description: str | None
    role: str
    enabled: bool
    labels: dict[str, str] | None
    created_at: str
    updated_at: str


class AgentLogMessage(BaseModel):
    """Optional structured log line from an agent runtime (no raw prod payloads)."""

    agent_id: str
    level: str = "info"
    message: str = Field(..., max_length=4000)
    context: dict[str, str] | None = None


class GatewayResult(BaseModel):
    request_id: str
    final_outcome: str
    executed: bool
    approval_id: str | None = None
    layers: list[LayerDecision]
    policy_decision: PolicyDecision | None = None
    risk: RiskScoreResult | None = None
    sandbox: SandboxResult | None = None
    execution_result: dict[str, Any] | None = None
    backup_snapshot_id: str | None = None
    registry_metadata: dict[str, Any] | None = Field(
        default=None,
        description="Agent registry / token scope resolution metadata.",
    )
