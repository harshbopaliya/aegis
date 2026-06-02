"""Tests for pluggable backend adapters."""

from __future__ import annotations

import pytest

from aegis.adapters.memory import (
    MemoryApprovalQueue,
    MemoryExecutionBackend,
    MemoryStorageBackend,
)
from aegis.models.schemas import AgentAction, Environment, HttpVerb, Role


def test_memory_storage_agents():
    storage = MemoryStorageBackend()
    storage.init()

    # Empty list
    assert len(storage.list_agents()) == 0

    # Upsert
    agent = storage.upsert_agent(
        agent_id="test-mem-agent",
        display_name="Memory Agent",
        description="Testing memory storage",
        role="read_only",
        enabled=True,
        labels={"env": "test"},
    )
    assert agent["agent_id"] == "test-mem-agent"
    assert agent["display_name"] == "Memory Agent"
    assert agent["labels"] == {"env": "test"}

    # Get
    retrieved = storage.get_agent("test-mem-agent")
    assert retrieved is not None
    assert retrieved["display_name"] == "Memory Agent"

    # List
    agents = storage.list_agents()
    assert len(agents) == 1
    assert agents[0]["agent_id"] == "test-mem-agent"

    # Delete
    deleted = storage.delete_agent("test-mem-agent")
    assert deleted is True
    assert len(storage.list_agents()) == 0


def test_memory_storage_policies():
    storage = MemoryStorageBackend()
    storage.init()

    # Empty list
    assert len(storage.list_all_policies()) == 0

    # Create
    policy = storage.create_policy(
        name="Block Production Deletes",
        effect="block",
        description="Never delete on prod",
        priority=200,
        enabled=True,
        resource_pattern="table:*",
        verbs=["DELETE"],
        environments=["production"],
    )
    assert policy["id"] == 1
    assert policy["priority"] == 200

    # Get
    retrieved = storage.get_policy(1)
    assert retrieved is not None
    assert retrieved["name"] == "Block Production Deletes"

    # List enabled
    assert len(storage.list_enabled_policies_ordered()) == 1

    # Update
    updated = storage.update_policy(1, {"priority": 300})
    assert updated is not None
    assert updated["priority"] == 300

    # Delete
    deleted = storage.delete_policy(1)
    assert deleted is True
    assert len(storage.list_all_policies()) == 0


def test_memory_approval_queue():
    queue = MemoryApprovalQueue()

    # Empty list
    assert len(queue.list_pending()) == 0

    # Enqueue
    appr_id = queue.enqueue("req-123", "DELETE table:users risk=100")
    assert appr_id.startswith("appr_")
    assert len(queue.list_pending()) == 1
    assert queue.list_pending()[0]["request_id"] == "req-123"

    # Check state
    assert queue.is_approved("req-123") is None

    # Resolve
    resolved = queue.resolve("req-123", "operator-1", approve=True, reason="Looks fine")
    assert resolved is True
    assert len(queue.list_pending()) == 0
    assert queue.is_approved("req-123") is True

    # Reset
    queue.reset_state()
    assert queue.is_approved("req-123") is None


def test_memory_execution_backend():
    backend = MemoryExecutionBackend()
    action = AgentAction(
        verb=HttpVerb.GET,
        resource="table:orders",
        environment=Environment.DEVELOPMENT,
        role=Role.READ_ONLY,
    )
    result = backend.execute(action)
    assert result["ok"] is True
    assert result["mock"] is True
    assert result["executed_action"]["verb"] == "GET"
