"""Dashboard APIs and audit persistence."""

from fastapi.testclient import TestClient

from app.main import app


def test_marketing_site_and_api_info(isolated_env):
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert b"Safety Gateway" in r.content

    info = client.get("/api/info").json()
    assert info["service"] == "ai-agent-safety-gateway"
    assert info["dashboard"] == "/dashboard"
from app.models.schemas import AgentAction, Environment, HttpVerb, Role


def test_dashboard_overview_shape(isolated_env):
    client = TestClient(app)
    r = client.get("/v1/dashboard/overview?hours=24")
    assert r.status_code == 200
    body = r.json()
    assert "stats" in body
    assert "active_agent_requests" in body
    assert "pending_approvals" in body
    assert "pipeline_modules" in body
    assert body["stats"]["window_hours"] == 24


def test_dashboard_records_audit_after_action(isolated_env):
    client = TestClient(app)
    before = client.get("/v1/dashboard/events?limit=5").json()["events"]
    action = AgentAction(
        verb=HttpVerb.GET,
        resource="table:demo_orders",
        environment=Environment.STAGING,
        role=Role.READ_ONLY,
        actor_id="test-dashboard-actor",
    )
    client.post("/v1/actions", json=action.model_dump(mode="json"))
    after = client.get("/v1/dashboard/events?limit=20").json()["events"]
    assert len(after) >= len(before)
    types = {e["event_type"] for e in after}
    assert "request_received" in types
    assert "executed" in types


def test_request_detail_includes_pipeline_or_audit(isolated_env):
    client = TestClient(app)
    action = AgentAction(
        verb=HttpVerb.GET,
        resource="table:demo_orders",
        environment=Environment.STAGING,
        role=Role.READ_ONLY,
        actor_id="trace-actor",
    )
    res = client.post("/v1/actions", json=action.model_dump(mode="json"))
    rid = res.json()["request_id"]
    detail = client.get(f"/v1/dashboard/requests/{rid}").json()
    assert detail["request_id"] == rid
    assert isinstance(detail["audit_events"], list)
    assert len(detail["audit_events"]) >= 1
