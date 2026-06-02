"""
Abstract Base Classes for pluggable Aegis storage and execution backends.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from aegis.models.schemas import AgentAction


class StorageBackend(ABC):
    """Abstract interface for all persistent gateway storage.

    Handles agent registry, policies, audit events, and backup manifest.
    """

    @abstractmethod
    def init(self) -> None:
        """Initialize database, tables, and setup schemas."""
        ...

    # Agent registry
    @abstractmethod
    def get_agent(self, agent_id: str) -> dict[str, Any] | None:
        """Retrieve agent by ID."""
        ...

    @abstractmethod
    def list_agents(self, enabled_only: bool = False) -> list[dict[str, Any]]:
        """List registered agents."""
        ...

    @abstractmethod
    def upsert_agent(
        self,
        agent_id: str,
        display_name: str,
        description: str | None,
        role: str,
        enabled: bool,
        labels: dict[str, str] | None,
    ) -> dict[str, Any]:
        """Insert or update agent."""
        ...

    @abstractmethod
    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent."""
        ...

    @abstractmethod
    def clear_agents(self) -> None:
        """Clear all agents (used in tests)."""
        ...

    # Policy rules
    @abstractmethod
    def get_policy(self, policy_id: int) -> dict[str, Any] | None:
        """Retrieve policy by ID."""
        ...

    @abstractmethod
    def list_all_policies(self) -> list[dict[str, Any]]:
        """List all policies."""
        ...

    @abstractmethod
    def list_enabled_policies_ordered(self) -> list[dict[str, Any]]:
        """List enabled policies ordered by priority descending."""
        ...

    @abstractmethod
    def create_policy(
        self,
        name: str,
        effect: str,
        description: str | None = None,
        priority: int = 100,
        enabled: bool = True,
        resource_pattern: str | None = None,
        verbs: list[str] | None = None,
        environments: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new policy."""
        ...

    @abstractmethod
    def update_policy(
        self, policy_id: int, fields: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Update fields on a policy."""
        ...

    @abstractmethod
    def delete_policy(self, policy_id: int) -> bool:
        """Delete a policy."""
        ...

    @abstractmethod
    def clear_policies(self) -> None:
        """Clear all policies (used in tests)."""
        ...

    # Observability & Audit Events
    @abstractmethod
    def store_audit_event(
        self,
        ts: str,
        event_type: str,
        request_id: str,
        actor_id: str | None,
        payload_json: str,
        payload_encrypted: int,
    ) -> None:
        """Store a serialized audit event."""
        ...

    @abstractmethod
    def recent_events(self, limit: int, offset: int) -> list[dict[str, Any]]:
        """Retrieve recent audit events."""
        ...

    @abstractmethod
    def events_for_request(self, request_id: str) -> list[dict[str, Any]]:
        """Retrieve audit events for a request ID."""
        ...

    @abstractmethod
    def dashboard_stats(self, hours: int) -> dict[str, Any]:
        """Query statistics for dashboard."""
        ...

    # BackupManifest
    @abstractmethod
    def store_backup_snapshot(
        self,
        snap_id: str,
        reason: str,
        request_id: str,
        created_at: float,
        source_db: str,
        backup_path: str,
        encrypted: int,
        sha256_hex: str,
        size_bytes: int,
    ) -> None:
        """Store a backup snapshot metadata record."""
        ...

    @abstractmethod
    def get_backup_snapshot(self, snapshot_id: str) -> dict[str, Any] | None:
        """Retrieve snapshot metadata by ID."""
        ...

    @abstractmethod
    def list_snapshots(self) -> list[dict[str, Any]]:
        """List snapshots ordered by creation time descending."""
        ...

    @abstractmethod
    def clear_snapshots(self) -> None:
        """Clear snapshot metadata (used in tests)."""
        ...

    # Demo summary metrics
    @abstractmethod
    def get_gateway_mirror_count(self) -> int:
        """Return row count of gateway mirror table (for demo)."""
        ...

    @abstractmethod
    def get_demo_orders_count(self) -> int:
        """Return row count of demo orders table (for demo)."""
        ...


class ApprovalQueue(ABC):
    """Abstract interface for approval state tracking (Human-in-the-Loop)."""

    @abstractmethod
    def enqueue(self, request_id: str, summary: str) -> str:
        """Enqueue request for approval. Returns approval_id."""
        ...

    @abstractmethod
    def list_pending(self) -> list[dict[str, Any]]:
        """List pending approvals."""
        ...

    @abstractmethod
    def resolve(
        self,
        request_id: str,
        approver_id: str,
        approve: bool,
        reason: str | None,
    ) -> bool:
        """Resolve a pending approval. Returns True if found and resolved."""
        ...

    @abstractmethod
    def is_approved(self, request_id: str) -> bool | None:
        """Check if request is approved (True), rejected (False), or pending (None)."""
        ...

    @abstractmethod
    def reset_state(self) -> None:
        """Reset internal queue state (used in tests)."""
        ...


class ExecutionBackend(ABC):
    """Abstract interface for executing approved action payloads."""

    @abstractmethod
    def execute(self, action: AgentAction) -> dict[str, Any]:
        """Execute the action and return results."""
        ...
