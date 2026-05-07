# Getting Started: Aegis Demo

## 🎯 What You'll Learn

This demo shows:
- ✅ **How the safety gateway protects AI agents**
- ✅ **Real-time monitoring of all 7 safety layers**
- ✅ **Side-by-side comparison: WITH vs WITHOUT safety**
- ✅ **Module outputs at each layer**
- ✅ **Dashboard displays real-time agent actions**

---

## 🚀 Quick Start (5 Minutes)

### 1. Get OpenAI API Key
```bash
# Visit https://platform.openai.com/api-keys
# Create new API key, copy it (starts with sk-)
```

### 2. Configure Environment
```bash
cp .env.example .env

# Edit .env and add:
OPENAI_API_KEY=sk-your-key-here
ASG_ENVIRONMENT=development
```

### 3. Start Application
```bash
# Option A: Docker (recommended)
docker-compose up -d

# Option B: Local Python
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

### 4. Open Demo Dashboard
```
http://localhost:8000/agent-monitor.html
```

---

## 📊 Dashboard Features

### Real-time Agent Monitoring

The dashboard shows what happens as your AI agent runs:

**Step-by-Step Display:**
```
Step 1:
├─ Thought: "Let me analyze customer data"
├─ Proposes: GET table:orders (staging)
├─ Risk Score: 10/100 (LOW)
├─ Safety Decision: ✅ ALLOW
└─ Result: 42 rows returned

Step 2:
├─ Thought: "I should delete old users"
├─ Proposes: DELETE table:users (production)
├─ Risk Score: 92/100 (CRITICAL)
├─ Safety Decision: ❌ BLOCK
└─ Result: "DELETE in production blocked by policy"
```

### Metrics Display

**Real-time KPIs:**
- Total steps completed
- Operations blocked by policy
- Operations executed safely
- Dangerous attempts detected
- Protection effectiveness %

### Side-by-Side Comparison

**WITH Safety Gateway Column:**
- Shows how many operations were blocked
- Shows approval workflow in action
- Shows safe execution results

**WITHOUT Safety Gateway Column:**
- Shows unrestricted execution
- Shows dangerous operations executing
- Shows lack of control/audit

---

## 🔍 Understanding Module Outputs

### Module Flow Diagram

```
AI Agent Request
    ↓
[1] Agent Registry → ✓ Agent verified
    ↓
[2] Risk Scoring → Risk score: 87/100
    ↓
[3] Policy Engine → Decision: BLOCK
    ↓
[4] Human Loop → (if needed) Approval queued
    ↓
[5] Execution → (if allowed) Operation executed
    ↓
[6] Audit & Observability → Logged to trail
    ↓
Dashboard Display
```

### What Each Layer Shows

#### 1. Agent Registry (`agents/`)
**What it does:** Verifies AI agent is registered
**Output:**
```json
{
  "agent_id": "demo-safe",
  "display_name": "Safety-Protected Agent",
  "role": "ai_agent",
  "enabled": true
}
```
**In Dashboard:** Agent name and status

#### 2. Risk Scoring (`risk_scoring/`)
**What it does:** Evaluates risk of the action (0-100)
**Output:**
```json
{
  "risk_score": 87,
  "risk_level": "HIGH",
  "factors": [
    "DELETE operation baseline",
    "production environment modifier",
    "high-value data surface"
  ]
}
```
**In Dashboard:** RED number (87/100) with reasons

#### 3. Policy Engine (`policy_engine/`)
**What it does:** Checks against security policies
**Output:**
```json
{
  "decision": "BLOCK",
  "reason": "DELETE in production blocked by strict policy",
  "source": "policy-001",
  "metadata": {"table": "users", "environment": "production"}
}
```
**In Dashboard:** ❌ BLOCK badge + reason text

#### 4. Human Loop (`human_loop/`)
**What it does:** Creates approval queue if needed
**Output:**
```json
{
  "approval_id": "appr_abc123",
  "request_id": "req_xyz789",
  "status": "pending",
  "created_at": "2026-05-07T14:22:15Z"
}
```
**In Dashboard:** ⏳ PENDING badge if awaiting approval

#### 5. Execution (`execution/`)
**What it does:** Safely executes allowed operations
**Output (GET):**
```json
{
  "ok": true,
  "rows": [
    {"id": 1, "label": "Demo Order 1"},
    {"id": 2, "label": "Demo Order 2"}
  ]
}
```
**Output (BLOCKED):**
```json
{
  "ok": false,
  "blocked": true,
  "message": "Blocked by safety policy"
}
```
**In Dashboard:** Result message in green/red

#### 6. Backup & Recovery (`backup_recovery/`)
**What it does:** Automatically creates encrypted backups
**Output:**
```json
{
  "backup_id": "bk_20260507_142215",
  "timestamp": "2026-05-07T14:22:15Z",
  "size_bytes": 12345,
  "encrypted": true,
  "retention_days": 30
}
```
**In Dashboard:** Backup status indicator

#### 7. Observability (`observability/`)
**What it does:** Records audit trail of all actions
**Output:**
```json
{
  "event_id": "evt_12345",
  "timestamp": "2026-05-07T14:22:15.123Z",
  "request_id": "req_xyz789",
  "actor_id": "demo-safe",
  "action": {
    "verb": "DELETE",
    "resource": "table:users",
    "environment": "production"
  },
  "risk_score": 92,
  "policy_decision": "BLOCK",
  "policy_reason": "DELETE in production blocked by policy",
  "execution_result": {
    "blocked": true,
    "error": "Policy violation"
  }
}
```
**In Dashboard:** All data logged and visible

---

## 📈 Three Demo Scenarios

### Scenario 1: Safe Read Operations

**What Happens:**
1. Agent wants to read customer orders
2. All modules say: ✅ ALLOW
3. Data is returned
4. Logged to audit trail

**Expected Result:**
- WITH safety: ✅ Executes
- WITHOUT safety: ✅ Executes
- **Difference:** NONE (reads are always safe)

---

### Scenario 2: Dangerous Production DELETE

**What Happens:**
1. Agent wants: `DELETE FROM users WHERE...` in PRODUCTION
2. Risk scoring: 🔴 92/100 (CRITICAL)
3. Policy engine: ❌ BLOCK (strict mode)
4. Execution: ⛔ Blocked, nothing executed
5. Audit: Logged with full context

**Expected Result:**
- WITH safety: ❌ BLOCKED (data saved!)
- WITHOUT safety: ✅ EXECUTES (data deleted!)
- **Difference:** Safety prevented catastrophic data loss

---

### Scenario 3: Medium-Risk Operations

**What Happens:**
1. Agent wants: `UPDATE table:payments SET status='refunded'`
2. Risk scoring: 🟡 50/100 (MEDIUM)
3. Policy engine: ⏳ REQUIRE_APPROVAL
4. Human loop: Approval queued for human
5. Execution: Waits for approval (async)

**Expected Result:**
- WITH safety: ⏳ PENDING (waiting for approval)
- WITHOUT safety: ✅ EXECUTES (no approval needed)
- **Difference:** Added approval workflow for risky operations

---

## 🎮 Try the Demo

### Button 1: "Run WITH Safety Gateway"
```
Executes agent with all 7 safety layers enabled
Expected:
- Dangerous operations blocked
- Safe operations approved
- Full audit trail
- Approval workflow active
```

### Button 2: "Run WITHOUT Safety Gateway"
```
⚠️ WARNING: Executes agent with NO safety restrictions
Expected:
- All operations execute immediately
- Dangerous operations execute freely
- No approval workflow
- No policy enforcement
```

### Button 3: "Side-by-Side Comparison"
```
Runs BOTH modes back-to-back and compares results
Shows:
- How many operations each mode executed
- How many operations were blocked
- Protection effectiveness percentage
- Which operations were dangerous
```

---

## 🔐 Production Integration Points

### 1. Replace Execution Module

Currently uses SQLite demo. To integrate production database:

**File:** `app/modules/execution/service.py`

```python
def execute(action: AgentAction) -> dict:
    # Replace: sqlite3.connect()
    # With: Your production DB connector
    # Example: PostgreSQL, MySQL, DynamoDB, etc.
```

### 2. Load Real Policies

Currently uses built-in policies. To use production policies:

**File:** `app/modules/policy_engine/engine.py`

```python
def evaluate(action: AgentAction):
    # Load from: Your policy database
    # Instead of: Built-in defaults
    for rule in policy_db.get_enabled_policies():
        if matches_pattern(action, rule):
            return apply_policy(action, rule)
```

### 3. Connect to Agent Registry

Currently uses SQLite. To connect to production agents:

**File:** `app/modules/agents/repository.py`

```python
def get(agent_id: str):
    # Query from: Your agent management system
    # Instead of: SQLite agents table
    agent = production_agent_db.get(agent_id)
    return agent.to_dict()
```

### 4. Configure Approvers

Currently has no approval logic. To add human approvers:

**File:** `app/modules/human_loop/service.py`

```python
def resolve(approval_id, approved, approver_id):
    # Send notification to: Your approval system
    # Update: Your HITL (Human-in-the-Loop) database
    notify_approvers(approval_id)
```

---

## 📊 Interpreting Results

### Success Criteria

**WITH Safety Gateway Should Show:**
- ✅ Dangerous operations blocked
- ✅ Safe operations executed
- ✅ Approval workflow active
- ✅ 100% audit trail
- ✅ Risk scores calculated

**WITHOUT Safety Gateway Should Show:**
- ⚠️ All operations execute immediately
- ⚠️ No blocks or approvals
- ⚠️ No risk scoring
- ⚠️ Limited audit information

### Protection Effectiveness

```
Formula: (Dangerous Attempts Blocked) / (Total Dangerous Attempts) × 100

Example:
- Agent made 5 dangerous attempts
- Safety gateway blocked 5 of them
- Protection Effectiveness: 100% ✅

If unsafe mode executes those same 5:
- All 5 executed without control
- Without safety: 0% protection ❌
```

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| "OpenAI API key not configured" | Add `OPENAI_API_KEY=sk-...` to .env |
| "Connection Failed" on dashboard | Check service running: `curl http://localhost:8000/health/ready` |
| Agent runs slowly | Normal! GPT takes 10-30s per step. Use production batch APIs for speed. |
| Comparison never completes | Be patient (60+ seconds). Monitor logs for progress. |
| Dashboard shows no steps | Check OpenAI API key is valid |

---

## 📚 Additional Resources

### Documentation Files

| File | Purpose |
|------|---------|
| `MODULE_ARCHITECTURE.md` | Deep dive into each module |
| `DEMO.md` | Full demo walkthrough |
| `API_DOCUMENTATION.md` | API endpoint reference |
| `DEPLOYMENT.md` | Production deployment guide |
| `PRODUCTION_README.md` | Quick start guide |

### API Endpoints

```bash
# Check API status
curl http://localhost:8000/v1/agent-demo/status

# Run WITH safety
curl -X POST http://localhost:8000/v1/agent-demo/run-with-safety \
  -d '{"objective": "Analyze data", "steps": 5}'

# Run WITHOUT safety
curl -X POST http://localhost:8000/v1/agent-demo/run-without-safety \
  -d '{"objective": "Manage data", "steps": 5}'

# Compare both
curl -X POST http://localhost:8000/v1/agent-demo/compare \
  -d '{"objective": "Handle data operations", "steps": 5}'
```

---

## ✅ Next Steps

1. **Run the demo** (5 min)
   - Open agent-monitor.html
   - Click "Side-by-Side Comparison"
   - Observe results

2. **Read the documentation** (15 min)
   - `MODULE_ARCHITECTURE.md` - understand layers
   - `DEMO.md` - complete walkthrough

3. **Explore the code** (20 min)
   - `app/modules/` - see each module
   - `app/routes/agent_demo.py` - see API implementation
   - `static/agent-monitor.html` - see dashboard

4. **Integrate with production** (ongoing)
   - Replace execution module with your DB
   - Load your policies
   - Connect to your agent registry
   - Set up approval workflow

---

## 🎓 Learning Outcomes

After this demo, you'll understand:

✅ **7-Layer Safety Model**
- Agent Registry → Risk Scoring → Policy Engine → Human Loop → Execution → Audit → Dashboard

✅ **Module Outputs**
- What each layer produces
- How layers chain together
- What dashboard displays

✅ **Safety Gateway Value**
- Prevents dangerous operations
- Adds approval workflows
- Maintains audit trails
- Enables compliance

✅ **Real-time Monitoring**
- Watch agent actions step-by-step
- See decisions at each layer
- Monitor with real dashboards
- Track metrics and alerts

---

**Ready?** 👉 Open http://localhost:8000/agent-monitor.html and click "Side-by-Side Comparison"

**Version:** 1.0.0 | **Status:** ✅ Production-ready | **Updated:** 2026-05-07
