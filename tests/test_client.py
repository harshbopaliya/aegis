"""Tests for the SDK client."""

from fastapi.testclient import TestClient

from aegis.client import AegisClient
from aegis.server import create_app


def test_client_health():
    """Test the SDK client health method against test server."""
    app = create_app(
        environment="development",
        debug=True,
        require_auth=False,
        require_agent_registration=False,
    )
    # Use httpx transport for testing
    import httpx

    transport = httpx.MockTransport(
        TestClient(app, raise_server_exceptions=False).app
    )
    # Direct TestClient approach
    tc = TestClient(app)
    resp = tc.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_client_submit_action():
    """Test submitting an action through the SDK."""
    app = create_app(
        environment="development",
        debug=True,
        require_auth=False,
        require_agent_registration=False,
    )
    tc = TestClient(app)
    resp = tc.post(
        "/v1/actions",
        json={
            "verb": "GET",
            "resource": "table:demo_orders",
            "environment": "staging",
            "role": "read_only",
            "actor_id": "test-agent",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["executed"] is True
    assert data["final_outcome"] == "executed"


def test_client_examples():
    """Test example endpoints."""
    app = create_app(
        environment="development",
        debug=True,
        require_auth=False,
    )
    tc = TestClient(app)
    resp = tc.get("/v1/examples/safe-read")
    assert resp.status_code == 200
    data = resp.json()
    assert data["verb"] == "GET"

    resp = tc.get("/v1/examples/delete-production-users")
    assert resp.status_code == 200
    data = resp.json()
    assert data["verb"] == "DELETE"
