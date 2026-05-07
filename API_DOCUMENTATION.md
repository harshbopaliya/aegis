# Aegis - Complete API Documentation & Best Practices

## Overview

The Aegis is a production-grade control plane for AI agents that enforces multi-layer safety checks before any action execution. All agent actions must flow through this gateway.

**Base URL**: `https://api.yourdomain.com/v1`

## Authentication & Authorization

### Request Headers

All requests must include standard headers:

```http
X-Request-ID: <uuid>        # Unique request identifier
X-Actor-ID: <agent-name>    # Agent or user identifier
Content-Type: application/json
Authorization: Bearer <token>  # If using OAuth2/JWT
```

### Example Headers

```bash
curl -X POST https://api.yourdomain.com/v1/actions \
  -H "X-Request-ID: 550e8400-e29b-41d4-a716-446655440000" \
  -H "X-Actor-ID: agent-v2-production" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbG..."
```

## Core Endpoints

### 1. Submit Action for Evaluation

**Endpoint**: `POST /v1/actions`

**Rate Limit**: 100 actions/minute

**Description**: Submit a proposed action for safety evaluation. The action flows through 7 layers of protection.

**Request Body**:

```json
{
  "verb": "GET|POST|PUT|PATCH|DELETE",
  "resource": "string",
  "environment": "development|staging|production",
  "role": "read_only|limited_write|no_delete|production_operator",
  "actor_id": "string",
  "payload": {}
}
```

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `verb` | HttpVerb | Yes | HTTP method |
| `resource` | string | Yes | Target resource (e.g., `table:users`, `api:/v1/orders`) |
| `environment` | Environment | No | Target environment (default: `development`) |
| `role` | Role | Yes | Actor's role for RBAC |
| `actor_id` | string | Yes | Unique agent/user identifier |
| `payload` | object | No | Action-specific data |
| `request_id` | string | No | Custom request ID (auto-generated if omitted) |

**Response** (Success - 200):

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "final_outcome": "executed|pending_human_approval|blocked_*",
  "executed": true,
  "layers": [
    {
      "layer": "agent_registry",
      "allowed": true,
      "detail": "Agent registered and valid"
    },
    {
      "layer": "token_scoping",
      "allowed": true,
      "detail": "Role permits operation"
    },
    {
      "layer": "policy_engine",
      "allowed": true,
      "detail": "Policy check passed"
    },
    {
      "layer": "sandbox",
      "allowed": true,
      "detail": "Simulation successful"
    },
    {
      "layer": "risk_scoring",
      "allowed": true,
      "detail": "Risk score: 15 (low)"
    }
  ],
  "risk_score": 15,
  "risk_level": "low",
  "approval_id": null,
  "registry_metadata": {}
}
```

**Response** (Pending Approval - 202):

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "final_outcome": "pending_human_approval",
  "executed": false,
  "approval_id": "appr_123abc",
  "approval_required_reason": "High-risk operation: DELETE on production",
  "risk_score": 85,
  "risk_level": "high"
}
```

**Response** (Blocked - 403):

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "final_outcome": "blocked_policy_violation",
  "executed": false,
  "blocking_layer": "policy_engine",
  "blocking_reason": "DELETE operations on production table:users are blocked",
  "risk_score": 95,
  "risk_level": "high"
}
```

**Examples**:

```bash
# Safe read operation (should execute)
curl -X POST https://api.yourdomain.com/v1/actions \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: $(uuidgen)" \
  -d '{
    "verb": "GET",
    "resource": "table:orders",
    "environment": "production",
    "role": "read_only",
    "actor_id": "agent-001"
  }'

# Sensitive write operation (likely pending approval)
curl -X POST https://api.yourdomain.com/v1/actions \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: $(uuidgen)" \
  -d '{
    "verb": "DELETE",
    "resource": "table:users",
    "environment": "production",
    "role": "production_operator",
    "actor_id": "agent-001",
    "payload": {"reason": "user_account_deletion"}
  }'
```

### 2. Resolve Human Approval

**Endpoint**: `POST /v1/approvals`

**Rate Limit**: 1000 requests/minute

**Description**: Approve or reject a pending action that requires human review.

**Request Body**:

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "approver_id": "human-ops-1",
  "approve": true,
  "reason": "Verified user deletion request"
}
```

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `request_id` | string | Yes | Original request ID |
| `approver_id` | string | Yes | Human approver identifier |
| `approve` | boolean | Yes | Approval decision |
| `reason` | string | No | Explanation for decision |

**Response** (Approved - 200):

```json
{
  "status": "approved",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "executed": true,
  "execution_result": {
    "outcome": "success",
    "affected_rows": 1
  }
}
```

**Response** (Rejected - 200):

```json
{
  "status": "rejected",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "executed": false,
  "rejection_reason": "Verified user deletion request"
}
```

**Example**:

```bash
curl -X POST https://api.yourdomain.com/v1/approvals \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "approver_id": "human-ops-1",
    "approve": true,
    "reason": "User confirmed deletion request"
  }'
```

## Monitoring & Dashboard Endpoints

### Get Dashboard Overview

**Endpoint**: `GET /v1/dashboard/overview`

**Query Parameters**:

```
hours=24 (default: 24)
```

**Response**:

```json
{
  "timestamp": "2026-05-07T10:30:00Z",
  "summary": {
    "total_actions": 1250,
    "executed_actions": 1100,
    "blocked_actions": 50,
    "pending_approvals": 20,
    "approval_rate": "95%"
  },
  "risk_distribution": {
    "low": 900,
    "medium": 200,
    "high": 150
  },
  "active_agents": 12,
  "uptime_percent": 99.95
}
```

### Get Audit Events

**Endpoint**: `GET /v1/dashboard/events`

**Query Parameters**:

```
limit=80 (default)
offset=0 (default)
type=all|approved|rejected|blocked
```

**Response**:

```json
{
  "total": 1250,
  "limit": 80,
  "offset": 0,
  "events": [
    {
      "request_id": "550e8400-e29b-41d4-a716-446655440000",
      "timestamp": "2026-05-07T10:30:00Z",
      "actor_id": "agent-001",
      "verb": "DELETE",
      "resource": "table:users",
      "environment": "production",
      "outcome": "pending_human_approval",
      "risk_score": 85,
      "blocking_layer": null
    }
  ]
}
```

### Get Request Details

**Endpoint**: `GET /v1/dashboard/requests/{request_id}`

**Response**:

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-05-07T10:30:00Z",
  "actor_id": "agent-001",
  "status": "pending_human_approval",
  "action": {
    "verb": "DELETE",
    "resource": "table:users",
    "environment": "production",
    "role": "production_operator",
    "payload": {}
  },
  "evaluation_pipeline": [
    {
      "layer": "agent_registry",
      "status": "passed",
      "detail": "Agent registered",
      "timestamp": "2026-05-07T10:30:00Z"
    },
    {
      "layer": "policy_engine",
      "status": "passed",
      "detail": "Policy allows with approval",
      "timestamp": "2026-05-07T10:30:01Z"
    }
  ],
  "approvals": [
    {
      "approval_id": "appr_123abc",
      "status": "pending",
      "required_by": "2026-05-07T11:30:00Z"
    }
  ]
}
```

## Error Handling

### Standard Error Response

```json
{
  "code": "ERROR_CODE",
  "message": "Human-readable error message",
  "detail": "Detailed technical information",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-05-07T10:30:00Z",
  "path": "/v1/actions"
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|------------|-------------|
| `VALIDATION_ERROR` | 422 | Invalid request payload |
| `AUTHENTICATION_ERROR` | 401 | Missing/invalid auth |
| `AUTHORIZATION_ERROR` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `POLICY_VIOLATION` | 403 | Action blocked by policy |
| `APPROVAL_REQUIRED` | 202 | Waiting for human approval |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily down |
| `INTERNAL_SERVER_ERROR` | 500 | Unexpected error |

### Example Error Response

```json
{
  "code": "POLICY_VIOLATION",
  "message": "Action blocked by policy",
  "detail": "DELETE operations on production table:users are blocked. Contact security team to request exemption.",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-05-07T10:30:00Z",
  "path": "/v1/actions"
}
```

## Best Practices

### 1. Request IDs

Always provide unique request IDs for traceability:

```bash
REQUEST_ID=$(uuidgen)
curl -X POST ... -H "X-Request-ID: $REQUEST_ID"
```

### 2. Error Handling

Implement exponential backoff for retries:

```python
import time

def submit_with_retry(action, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = submit_action(action)
            return response
        except RateLimitError:
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            time.sleep(wait_time)
            continue
        except Exception as e:
            logger.error(f"Unrecoverable error: {e}")
            raise
```

### 3. Approval Workflow

Poll for approval status:

```python
def wait_for_approval(request_id, timeout=3600, poll_interval=5):
    start_time = time.time()
    while time.time() - start_time < timeout:
        details = get_request_details(request_id)
        if details['status'] != 'pending_human_approval':
            return details
        time.sleep(poll_interval)
    raise TimeoutError(f"Approval timeout for {request_id}")
```

### 4. Logging

Include request context in logs:

```python
logger.info(
    "Submitting action",
    extra={
        "request_id": request_id,
        "actor_id": actor_id,
        "resource": resource,
    }
)
```

### 5. Monitoring

Set up alerts for:
- High block rate (> 10%)
- Pending approvals queue > 50
- Average risk score > 70
- API latency > 5s
- Error rate > 5%

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/v1/actions` | 100 | 1 minute |
| `/v1/approvals` | 1000 | 1 minute |
| General API | 1000 | 1 minute |

Rate limit headers in response:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 42
X-RateLimit-Reset: 1620000000
```

## Troubleshooting

### Common Issues

**Q: "Service Unavailable" errors**
- A: Check database connectivity and server health
  ```bash
  curl https://api.yourdomain.com/health/ready
  ```

**Q: High latency on action submissions**
- A: Check rate limit, review policy complexity, monitor database performance

**Q: Pending approvals not executing**
- A: Verify approval timeout settings, check human approval system

## Support

- **Documentation**: https://docs.yourdomain.com
- **Status Page**: https://status.yourdomain.com
- **Support Email**: support@yourdomain.com
- **Slack Channel**: #aegis
