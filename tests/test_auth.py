"""Tests for API key authentication."""

from fastapi.testclient import TestClient

from aegis.core.auth import generate_api_key, _hash_key
from aegis.server import create_app


def test_auth_disabled_allows_all():
    """When ASG_REQUIRE_AUTH=false, all endpoints are accessible."""
    app = create_app(
        environment="development",
        debug=True,
        require_auth=False,
    )
    tc = TestClient(app)
    resp = tc.get("/health")
    assert resp.status_code == 200


def test_auth_enabled_blocks_without_key():
    """When ASG_REQUIRE_AUTH=true, endpoints require API key."""
    raw_key, key_hash = generate_api_key("admin")
    app = create_app(
        environment="development",
        debug=True,
        require_auth=True,
        api_keys=f"admin:{raw_key}",
    )
    tc = TestClient(app)

    # Health is always public
    resp = tc.get("/health")
    assert resp.status_code == 200

    # Actions require auth
    resp = tc.post(
        "/v1/actions",
        json={
            "verb": "GET",
            "resource": "table:demo_orders",
            "environment": "staging",
            "role": "read_only",
        },
    )
    assert resp.status_code == 401


def test_auth_with_valid_key():
    """Valid API key grants access."""
    raw_key, _ = generate_api_key("admin")
    app = create_app(
        environment="development",
        debug=True,
        require_auth=True,
        api_keys=f"admin:{raw_key}",
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
        headers={"X-API-Key": raw_key},
    )
    assert resp.status_code == 200
    assert resp.json()["executed"] is True


def test_generate_key():
    """Test key generation."""
    raw, hash_val = generate_api_key("operator")
    assert raw.startswith("aegis_operator_")
    assert len(hash_val) == 64  # SHA-256 hex
