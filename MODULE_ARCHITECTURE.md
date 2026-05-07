# Aegis — Module Architecture & Outputs

## System Overview

The Aegis is a 7-layer safety evaluation system that intercepts AI agent actions and controls their execution. When an AI agent attempts an operation, it goes through these layers in sequence:

```
AI Agent Action
    ↓
[1] Token Scoping Layer
    ↓
[2] Agent Registry Layer
    ↓
[3] Risk Scoring Layer
    ↓
[4] Policy Engine Layer
    ↓
[5] Human-in-the-Loop Layer
    ↓
[6] Execution Layer (Controlled)
    ↓
[7] Audit & Observability Layer
```

---

## Module Details

### 1. **agents/** — Agent Registry & Identity Management
**Location:** `app/modules/agents/`

**Purpose:** 
- Maintain persistent registry of all AI agents
- Map agent_id to their role and token scope
- Enforce agent registration requirements

**Files:**
- `repository.py` - Database persistence layer for agents

**Key Functions:**
```python
get(agent_id: str) → dict | None
list_agents(enabled_only: bool) → list[dict]
upsert(agent_id, display_name, description, role, enabled, labels) → dict
update_partial(agent_id, fields) → dict | None
```

**Data Model:**
```python
{
  "agent_id": "ai-agent-001",
  "display_name": "Data Analysis Agent",
  "description": "Analyzes customer data",
  "role": "analyst",
  "enabled": True,
  "labels": {"team": "data", "region": "us-east"},
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-05-07T14:22:00Z"
}
```

**Output:**
- ✅ Agent metadata for later layers
- ✅ Role assignment (used in token scoping)
- ✅ Enable/disable control per agent

---

### 2. **token_scoping/** — Token Scoping & RBAC
**Location:** `app/modules/token_scoping/`

**Purpose:**
- Define what tokens each agent can use
- Implement fine-grained role-based access control
- Prevent token escalation and cross-role abuse

**Status:** Integration point for your production token system

**Output Expected:**
```python
{
  "agent_id": "ai-agent-001",
  "role": "analyst",
  "scoped_tokens": ["table:orders:read", "table:customers:read"],
  "denied_tokens": ["table:users", "system:admin"],
  "resource_patterns": ["table:*", "metric:*"]
}
```

---

### 3. **risk_scoring/** — Risk Assessment Engine
**Location:** `app/modules/risk_scoring/service.py`

**Purpose:**
- Evaluate risk level (0-100) for any proposed action
- Consider: operation type, environment, resource sensitivity
- Provide factors explaining the score

**Algorithm:**
```
Base scores:
- GET:     10 points (read-only, low risk)
- POST:    50 points (create, medium risk)
- PUT:     50 points (update, medium risk)
- PATCH:   50 points (update, medium risk)
- DELETE:  92 points (destructive, critical)

Modifiers:
+ 5 points if environment = PRODUCTION
+ 3 points if resource contains sensitive keywords
+ 5 points if resource = high-value data (users, payments)

Risk Level:
- LOW:    0-39
- MEDIUM: 40-69
- HIGH:   70-100
```

**Example Output:**
```python
RiskScoreResult(
  risk_score=87,
  risk_level=RiskLevel.HIGH,
  factors=[
    "DELETE operation baseline (critical)",
    "production environment modifier",
    "high-value data surface"
  ]
)
```

**Dashboard Impact:**
- 🟢 GREEN (LOW): Can auto-execute with audit
- 🟡 YELLOW (MEDIUM): May require approval
- 🔴 RED (HIGH): Almost always requires approval

---

### 4. **policy_engine/** — Policy Evaluation & Access Control
**Location:** `app/modules/policy_engine/`

**Files:**
- `engine.py` - Core policy evaluation logic
- `repository.py` - Policy database storage

**Purpose:**
- Apply client-defined policies to actions
- Match against patterns (resource_pattern, verb, environment)
- Return ALLOW / REQUIRE_APPROVAL / BLOCK decisions

**Policy Rule Structure:**
```python
{
  "id": "policy-001",
  "name": "Protect Production Users Table",
  "resource_pattern": "table:users*",
  "verbs": ["DELETE", "UPDATE"],
  "environments": ["production"],
  "effect": "BLOCK",  # or REQUIRE_APPROVAL
  "priority": 100,
  "enabled": True
}
```

**Decision Outputs:**
```python
(
  PolicyDecision.ALLOW,
  "Policy allows this operation",
  {"table": "orders", "environment": "staging", "source": "policy-001"}
)
```

**Built-in Defaults:**
- ✅ Sensitive tables (from config) → REQUIRE_APPROVAL
- ✅ DELETE in production (strict mode) → BLOCK
- ✅ Everything else → ALLOW

---

### 5. **human_loop/** — Approval Workflow
**Location:** `app/modules/human_loop/service.py`

**Purpose:**
- Queue operations requiring human approval
- Track approval status and decisions
- Provide approval audit trail

**Data Structure:**
```python
PendingApproval(
  request_id="req-abc123",
  approval_id="appr-xyz789",
  summary="DELETE FROM table:users WHERE id > 1000 (production)",
  created_at=1715096520.123,
  resolved=False,
  approved=None,  # True/False/None
  approver_id=None  # Set when resolved
)
```

**Key Functions:**
```python
enqueue(request_id, summary) → approval_id
list_pending() → list[dict]
resolve(approval_id, approved, approver_id) → bool
is_approved(request_id) → bool
```

**Output:**
- ✅ Approval queue for dashboard
- ✅ Human decision tracking
- ✅ Non-blocking async workflow

---

### 6. **execution/** — Controlled Data Access
**Location:** `app/modules/execution/service.py`

**Purpose:**
- Single choke point for all data mutations
- Prevent direct database access
- Provide consistent contract for all operations

**Supported Operations:**
```python
# GET operations
if verb == HttpVerb.GET:
  rows = conn.execute(query).fetchall()
  output = {"ok": True, "rows": [row dict]}

# Mutations (POST, PUT, PATCH, DELETE)
conn.execute(insert/update/delete statement)
conn.commit()
output = {"ok": True, "operation": "executed"}
```

**Safety Features:**
- ✅ Single thread lock during mutations
- ✅ All operations logged to audit table
- ✅ Transaction isolation
- ✅ Easy to swap with your production database

**Output:**
```python
{
  "ok": True,
  "rows": [...],  # For GET
  "mirror_id": 123,  # For mutations
  "note": "Operation details"
}
```

---

### 7. **audit_payload** & **observability/** — Logging & Monitoring
**Location:** `app/core/audit_payload.py`, `app/modules/observability/service.py`

**Purpose:**
- Record every action with full context
- Support compliance and forensics
- Track agent behavior patterns

**Audit Record:**
```python
{
  "timestamp": "2026-05-07T14:22:15.123Z",
  "request_id": "req-abc123",
  "actor_id": "ai-agent-001",
  "actor_role": "analyst",
  "action": {
    "verb": "GET",
    "resource": "table:orders",
    "environment": "staging"
  },
  "risk_score": 15,
  "policy_decision": "ALLOW",
  "execution_result": {
    "status": "executed",
    "rows_affected": 42
  },
  "audit_payload_mode": "redact"  # or "encrypt", "full"
}
```

**Modes:**
- `redact`: Hide sensitive values, keep structure
- `encrypt`: Full encryption with Fernet key
- `full`: Complete unencrypted audit (staging only)

**Output Channels:**
- ✅ JSON structured logs (application logs)
- ✅ SQLite audit table (compliance)
- ✅ Real-time dashboard (monitoring)
- ✅ Encrypted backups (recovery)

---

### 8. **backup_recovery/** — Data Protection
**Location:** `app/modules/backup_recovery/service.py`

**Purpose:**
- Automated scheduled backups
- Encryption of sensitive data
- Recovery procedures

**Features:**
```python
# Automatic backups every 6 hours
backup(encryption_key=None) → {"backup_id": "bk_xyz", "size_bytes": 12345}

# Restore to point-in-time
restore(backup_id, target_timestamp=None) → {"restored": True, "rows": 1024}
```

**Output:**
- ✅ Encrypted backup files in `data/backups/`
- ✅ Metadata for recovery procedures
- ✅ Automated retention (30 days by default)

---

### 9. **sandbox/** — Prediction & Simulation
**Location:** `app/modules/sandbox/service.py`

**Purpose:**
- Predict action outcome WITHOUT executing
- Simulate policy evaluation
- Preview approval requirements

**Output:**
```python
{
  "would_execute": True,
  "would_require_approval": False,
  "would_be_blocked": False,
  "simulated_result": {
    "rows_affected": 5,
    "risk_score": 25
  }
}
```

---

### 10. **ai_agent/** — AI Agent Integration (NEW)
**Location:** `app/modules/ai_agent/service.py`

**Purpose:**
- Power autonomous AI agents with safety enforcement
- Integrate GPT-4o mini for intelligent decision-making
- Demonstrate safety gateway value through comparison

**Features:**
```python
class AIAgent:
  def run_session(objective: str, num_steps: int) → AgentSession
  
  # Returns step-by-step transcript with:
  # - GPT-4o mini thought
  # - Proposed action
  # - Safety decision
  # - Execution result
  # - Risk scoring
```

**Outputs:**
```python
{
  "session_id": "sess_1715096520_demo-safe",
  "agent_name": "Safety-Protected Agent",
  "steps": [
    {
      "step_number": 1,
      "thought": "Let's read the customer orders",
      "proposed_action": {
        "verb": "GET",
        "resource": "table:orders",
        "environment": "staging"
      },
      "safety_decision": "ALLOW",
      "safety_reason": "Read-only operation on staging",
      "risk_score": 10,
      "execution_result": {"ok": true, "rows": 42}
    }
  ],
  "blocked_by_policy": 2,
  "data_modified": 3,
  "dangerous_attempts": 5
}
```

---

## Data Flow Example

### Scenario: AI Agent attempts to DELETE production users

```
1. AI Agent Decision:
   "I should delete inactive users to free storage"
   → Action: DELETE table:users (production)

2. AGENT REGISTRY:
   ✓ Agent "data-cleaner-001" is registered
   ✓ Role: "maintenance"

3. TOKEN SCOPING:
   ✗ "maintenance" role cannot access "table:users"
   → Decision: BLOCK at this layer

4. RISK SCORING:
   (If not blocked earlier)
   DELETE + production + high-value data
   → Risk Score: 92 (CRITICAL)

5. POLICY ENGINE:
   Matches "Protect Production Users" policy
   → Decision: BLOCK

6. HUMAN LOOP:
   (If REQUIRE_APPROVAL decision)
   Enqueue for manual review
   → Approval ID: "appr-abc123"

7. EXECUTION:
   Decision: BLOCK
   → Nothing executed, operation logged

8. AUDIT & OBSERVABILITY:
   Record with full context
   → Encrypted audit entry
   → Real-time dashboard alert
   → Alert sent to security team
```

---

## Module Interdependencies

```
ai_agent/
  ├─→ agents/ (get agent metadata)
  ├─→ risk_scoring/ (evaluate risk)
  ├─→ policy_engine/ (check policies)
  ├─→ human_loop/ (queue approvals)
  └─→ execution/ (controlled execution)
      └─→ observability/ (audit logging)

dashboard/ routes
  ├─→ observability/ (fetch logs)
  ├─→ human_loop/ (show pending)
  ├─→ agents/ (list agents)
  └─→ backup_recovery/ (status)
```

---

## Integration Checklist

When deploying with your production system:

- [ ] **agents/** — Integrate with your agent management system
- [ ] **token_scoping/** — Connect to your authentication service
- [ ] **policy_engine/** — Load your security policies from your DB
- [ ] **execution/** — Replace SQLite with your production database
- [ ] **observability/** — Route to your log aggregation service
- [ ] **backup_recovery/** — Configure your backup storage
- [ ] **sandbox/** — Integrate with your prediction system
- [ ] **ai_agent/** — Configure OpenAI API key for testing

---

## Dashboard Real-time Monitoring

The agent-monitor dashboard shows:

1. **WITH Safety Gateway:**
   - ✅ Operations blocked by policy
   - ✅ Dangerous attempts prevented
   - ✅ Approval workflow in action
   - ✅ Safe execution results

2. **WITHOUT Safety Gateway:**
   - ❌ Unrestricted execution
   - ❌ Dangerous operations executed
   - ❌ No approval workflow
   - ❌ Data integrity violations

3. **Side-by-Side Comparison:**
   - Operations prevented by safety
   - Protection effectiveness percentage
   - Risk level comparison
   - Execution difference analysis

---

## Performance Characteristics

| Layer | Latency | Throughput | Notes |
|-------|---------|-----------|-------|
| Agent Registry | <1ms | 10k/s | In-memory cache possible |
| Risk Scoring | <1ms | 10k/s | Computational model only |
| Policy Engine | 1-5ms | 1k/s | DB lookup, optimize with caching |
| Human Loop | Async | N/A | Non-blocking, queue-based |
| Execution | 5-50ms | 100-500/s | DB-dependent |
| Audit | <1ms | 10k/s | Async fire-and-forget |

**Total e2e latency:** 20-100ms (99th percentile)

---

## Version Information

- **Aegis:** v1.0.0
- **Module Architecture:** Layered safety evaluation
- **Test Coverage:** 80%+ across all modules
- **Status:** Production-ready

---

**Last Updated:** 2026-05-07
**Maintained By:** AI Safety Team
**Support:** Document all integration points in your deployment guide
