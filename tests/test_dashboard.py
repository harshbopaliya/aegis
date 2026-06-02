"""Dashboard endpoint tests."""

from fastapi.testclient import TestClient

from aegis.server import create_app


def test_health_check():
    app = create_app(environment="development", debug=True, require_auth=False)
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_readiness_check():
    app = create_app(environment="development", debug=True, require_auth=False)
    client = TestClient(app)
    resp = client.get("/health/ready")
    assert resp.status_code == 200


def test_api_info():
    app = create_app(environment="development", debug=True, require_auth=False)
    client = TestClient(app)
    resp = client.get("/api/info")
    assert resp.status_code == 200
    data = resp.json()
    assert "endpoints" in data
    assert data["service"] == "Aegis"


def test_architecture():
    app = create_app(environment="development", debug=True, require_auth=False)
    client = TestClient(app)
    resp = client.get("/api/architecture")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["layers"]) == 7
