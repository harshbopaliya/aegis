"""
Aegis SDK Client — Python client for interacting with the safety gateway.

Usage::

    from aegis.client import AegisClient

    client = AegisClient("http://localhost:8000", api_key="your-key")

    # Submit an action for safety evaluation
    result = client.submit_action(
        verb="GET",
        resource="table:orders",
        environment="staging",
        role="read_only",
        actor_id="my-agent",
    )
    print(result["final_outcome"])  # "executed"

    # Approve a pending action
    client.approve(
        request_id="...",
        approver_id="human-1",
        approve=True,
        reason="Verified safe",
    )
"""

from __future__ import annotations

from typing import Any, Optional


class AegisClient:
    """Python SDK for interacting with the Aegis safety gateway.

    Parameters
    ----------
    base_url
        Base URL of the Aegis server (e.g. ``http://localhost:8000``).
    api_key
        Optional API key for authentication.
    timeout
        Request timeout in seconds.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str | None = None,
        timeout: int = 30,
    ):
        import httpx

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            headers["X-API-Key"] = api_key
        self._client = httpx.Client(
            base_url=self.base_url,
            headers=headers,
            timeout=timeout,
        )

    def close(self):
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        """Make an HTTP request and return JSON response."""
        response = self._client.request(
            method, path, json=json, params=params
        )
        response.raise_for_status()
        return response.json()

    # ========== Health ==========

    def health(self) -> dict[str, Any]:
        """Check gateway health."""
        return self._request("GET", "/health")

    def ready(self) -> dict[str, Any]:
        """Check gateway readiness (Kubernetes probe)."""
        return self._request("GET", "/health/ready")

    def info(self) -> dict[str, Any]:
        """Get service discovery information."""
        return self._request("GET", "/api/info")

    # ========== Actions ==========

    def submit_action(
        self,
        verb: str,
        resource: str,
        role: str,
        actor_id: str = "agent-001",
        environment: str = "development",
        payload: dict | None = None,
    ) -> dict[str, Any]:
        """Submit an action for safety evaluation.

        Parameters
        ----------
        verb
            HTTP verb: GET, POST, PUT, PATCH, DELETE
        resource
            Logical resource (e.g. ``table:orders``, ``api:/users``)
        role
            Agent role: read_only, limited_write, no_delete, production_operator
        actor_id
            Unique identifier for the agent
        environment
            Target environment: development, staging, production
        payload
            Optional action payload
        """
        body: dict[str, Any] = {
            "verb": verb.upper(),
            "resource": resource,
            "environment": environment.lower(),
            "role": role,
            "actor_id": actor_id,
        }
        if payload:
            body["payload"] = payload
        return self._request("POST", "/v1/actions", json=body)

    # ========== Approvals ==========

    def approve(
        self,
        request_id: str,
        approver_id: str,
        approve: bool = True,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Approve or reject a pending action.

        Parameters
        ----------
        request_id
            The request ID from the original action submission
        approver_id
            Unique identifier for the human approver
        approve
            True to approve, False to reject
        reason
            Optional reason for the decision
        """
        body: dict[str, Any] = {
            "request_id": request_id,
            "approver_id": approver_id,
            "approve": approve,
        }
        if reason:
            body["reason"] = reason
        return self._request("POST", "/v1/approvals", json=body)

    def reject(
        self,
        request_id: str,
        approver_id: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Convenience method to reject a pending action."""
        return self.approve(
            request_id=request_id,
            approver_id=approver_id,
            approve=False,
            reason=reason,
        )

    # ========== Agents ==========

    def register_agent(
        self,
        agent_id: str,
        display_name: str,
        role: str = "limited_write",
        description: str | None = None,
        enabled: bool = True,
        labels: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Register an AI agent."""
        body: dict[str, Any] = {
            "agent_id": agent_id,
            "display_name": display_name,
            "role": role,
            "enabled": enabled,
        }
        if description:
            body["description"] = description
        if labels:
            body["labels"] = labels
        return self._request("POST", "/v1/agents/", json=body)

    def list_agents(self) -> list[dict[str, Any]]:
        """List all registered agents."""
        return self._request("GET", "/v1/agents/")

    def get_agent(self, agent_id: str) -> dict[str, Any]:
        """Get a specific agent."""
        return self._request("GET", f"/v1/agents/{agent_id}")

    def delete_agent(self, agent_id: str) -> None:
        """Delete an agent."""
        self._client.delete(f"/v1/agents/{agent_id}").raise_for_status()

    # ========== Policies ==========

    def create_policy(
        self,
        name: str,
        effect: str,
        description: str | None = None,
        priority: int = 100,
        resource_pattern: str | None = None,
        verbs: list[str] | None = None,
        environments: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a safety policy."""
        body: dict[str, Any] = {
            "name": name,
            "effect": effect,
        }
        if description:
            body["description"] = description
        if priority != 100:
            body["priority"] = priority
        if resource_pattern:
            body["resource_pattern"] = resource_pattern
        if verbs:
            body["verbs"] = verbs
        if environments:
            body["environments"] = environments
        return self._request("POST", "/v1/policies/", json=body)

    def list_policies(self) -> list[dict[str, Any]]:
        """List all policies."""
        return self._request("GET", "/v1/policies/")

    # ========== Dashboard ==========

    def dashboard_overview(
        self, hours: int = 24
    ) -> dict[str, Any]:
        """Get dashboard overview."""
        return self._request(
            "GET",
            "/v1/dashboard/overview",
            params={"hours": hours},
        )

    def dashboard_events(
        self, limit: int = 80, offset: int = 0
    ) -> list[dict[str, Any]]:
        """Get recent audit events."""
        return self._request(
            "GET",
            "/v1/dashboard/events",
            params={"limit": limit, "offset": offset},
        )

    def get_request_detail(
        self, request_id: str
    ) -> dict[str, Any]:
        """Get detailed info for a specific request."""
        return self._request(
            "GET", f"/v1/dashboard/requests/{request_id}"
        )
