# Aegis — Live Demo Guide

## Quick Start (5 Minutes)

### Prerequisites
- Python 3.11+
- OpenAI API key (free tier OK, $5 free credits)
- Docker (optional, recommended)

### Step 1: Get OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Copy your key (starts with `sk-`)

### Step 2: Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit .env and add your OpenAI API key
OPENAI_API_KEY=sk-your-actual-key-here
ASG_ENVIRONMENT=development  # Use development for demo
ASG_DEBUG=false
```

### Step 3: Start the Gateway

**Option A: Docker (Recommended)**
```bash
docker-compose up -d
curl http://localhost:8000/health/ready
```

**Option B: Local Python**
```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

### Step 4: Open Demo Dashboard

Open in your browser:
```
http://localhost:8000/agent-monitor.html
```

---

## Demo Walkthrough

### What the Demo Does

1. **Creates an AI agent** powered by GPT-4o mini
2. **Runs it TWICE:**
   - First WITH your safety gateway (protected)
   - Second WITHOUT safety gateway (unrestricted)
3. **Compares the results** side-by-side

### Demo Scenarios

#### Scenario 1: Safe Operations (Read-Only)

**Objective:** "Analyze customer data"

**Expected Result:**
- ✅ WITH gateway: All reads execute safely
- ✅ WITHOUT gateway: All reads execute freely
- Result: No difference (both allow reads)

#### Scenario 2: Dangerous Production DELETE

**Objective:** "Clean up old user records in production"

**Expected Result:**
- ✅ WITH gateway: DELETE blocked by policy
- ❌ WITHOUT gateway: DELETE executes freely
- Result: Safety gateway saved your data

#### Scenario 3: High-Risk Operations

**Objective:** "Modify billing data and access controls"

**Expected Result:**
- ✅ WITH gateway: High-risk ops require approval
- ❌ WITHOUT gateway: All ops execute immediately
- Result: Safety gateway added approval workflow

---

## Real-time Monitoring Features

### Dashboard Displays

1. **System Status**
   - OpenAI API connectivity
   - Service health check
   - Configuration status

2. **Agent Session Details**
   - Each step the agent takes
   - AI thought process (from GPT-4o mini)
   - Safety decision (ALLOW/BLOCK/REQUIRE_APPROVAL)
   - Execution result

3. **Metrics Comparison**
   - Operations blocked
   - Operations executed
   - Dangerous attempts
   - Protection effectiveness percentage

4. **Step-by-Step Transcript**
   - What agent wanted to do
   - What safety gateway decided
   - Why (safety reason)
   - What actually happened

---

## Understanding the Outputs

### Module Layer Outputs

Each request goes through 7 layers. Here's what you see in the dashboard:

```
1. Agent Registry
   → ✓ Agent "demo-safe" is registered with role "ai_agent"

2. Risk Scoring  
   → Risk Score: 87/100 (HIGH)
   → Factors: DELETE operation, production environment

3. Policy Engine
   → Decision: BLOCK
   → Reason: "DELETE in production blocked by strict policy"

4. Human Loop
   → Would be queued if REQUIRE_APPROVAL

5. Execution
   → Status: Blocked (nothing executed)

6. Audit & Observability
   → Logged to audit trail with full context

7. Dashboard
   → Real-time display of all above
```

### Real-time Data Display

As the agent runs, you'll see:

**Step 1:**
```
Thought: "Let me read the customer orders"
Action: GET table:orders (staging)
Decision: ✅ ALLOW
Risk: 10/100 (LOW)
Result: 42 rows returned
```

**Step 2:**
```
Thought: "I should delete inactive users to save space"
Action: DELETE table:users (production)
Decision: ❌ BLOCK
Risk: 92/100 (CRITICAL)
Result: Blocked by strict policy - DELETE in production not allowed
```

---

## API Endpoints for Demo

### Check Service Status
```bash
curl http://localhost:8000/v1/agent-demo/status
```

### Run WITH Safety Gateway
```bash
curl -X POST http://localhost:8000/v1/agent-demo/run-with-safety \
  -H "Content-Type: application/json" \
  -d '{
    "objective": "Manage customer data safely",
    "steps": 5
  }'
```

### Run WITHOUT Safety Gateway
```bash
curl -X POST http://localhost:8000/v1/agent-demo/run-without-safety \
  -H "Content-Type: application/json" \
  -d '{
    "objective": "Manage customer data (unrestricted)",
    "steps": 5
  }'
```

### Run Side-by-Side Comparison
```bash
curl -X POST http://localhost:8000/v1/agent-demo/compare \
  -H "Content-Type: application/json" \
  -d '{
    "objective": "Manage customer billing data",
    "steps": 5
  }'
```

---

## Understanding Each Module Output

### 1. **Agent Registry** (`agents/`)
**Output in Demo:**
```json
{
  "agent_id": "demo-safe",
  "role": "ai_agent",
  "enabled": true
}
```
✅ Confirms agent is registered and active

### 2. **Risk Scoring** (`risk_scoring/`)
**Output in Demo:**
```json
{
  "risk_score": 87,
  "risk_level": "HIGH",
  "factors": [
    "DELETE operation baseline",
    "production environment modifier"
  ]
}
```
🔴 HIGH = likely requires approval

### 3. **Policy Engine** (`policy_engine/`)
**Output in Demo:**
```json
{
  "decision": "BLOCK",
  "reason": "DELETE in production is blocked by policy",
  "source": "builtin"
}
```
⛔ BLOCK = operation prevented

### 4. **Human Loop** (`human_loop/`)
**Output in Demo:**
```json
{
  "approval_id": "appr_abc123",
  "status": "pending",
  "created_at": "2026-05-07T14:22:15Z"
}
```
⏳ PENDING = awaiting human review

### 5. **Execution** (`execution/`)
**Output in Demo:**
```json
{
  "ok": true,
  "rows": [
    {"id": 1, "label": "Demo Order"}
  ]
}
```
✅ OK = operation executed safely

### 6. **Backup & Recovery** (`backup_recovery/`)
**Output in Demo:**
```json
{
  "backup_id": "bk_20260507_142215",
  "size_bytes": 12345,
  "encrypted": true
}
```
💾 Backup created automatically

### 7. **Observability** (`observability/`)
**Output in Demo:**
```json
{
  "event_id": "evt_xyz123",
  "timestamp": "2026-05-07T14:22:15.123Z",
  "action": "DELETE",
  "decision": "BLOCK",
  "risk_score": 87
}
```
📊 Full audit trail recorded

---

## Interpreting Results

### Dashboard Comparison View

When you run `/compare` endpoint, you'll see:

**WITH Safety Gateway Column:**
- ✅ Blocked: 2 operations (dangerous)
- ✅ Executed: 3 operations (safe)
- ✅ Approval pending: 0
- 🛡️ Protection: 100%

**WITHOUT Safety Gateway Column:**
- ❌ Blocked: 0 operations
- ❌ Executed: 5 operations (including dangerous)
- ❌ Approval pending: 0
- 🚨 Risk: CRITICAL

**Analysis:**
```
Key Finding: Safety gateway prevented 2 dangerous 
operations that unrestricted agent executed freely.

Operations Prevented:
- DELETE table:users (production) - would delete users
- MODIFY table:payments (production) - would affect billing

Protection Rate: 100% (2 out of 2 dangerous attempts blocked)
```

---

## Production Database Integration

Currently the demo uses SQLite. When you integrate with production:

### Replace Execution Module

Update `app/modules/execution/service.py`:

```python
def execute(action: AgentAction) -> dict:
    """Replace with your production database connector."""
    
    # Instead of:
    # conn = sqlite3.connect(path)
    
    # Use your database:
    conn = production_db_pool.get_connection()
    
    # Execute action through your driver
    if action.verb == HttpVerb.GET:
        result = conn.query(action.resource)
    elif action.verb == HttpVerb.DELETE:
        result = conn.execute(f"DELETE FROM {action.resource}")
    
    return {"ok": True, "rows": result}
```

### Update Policy Engine

Replace policies with your actual rules:

```python
# Instead of built-in policies
# Load from your policy database:
policies = production_policy_db.get_all_policies()
```

---

## Troubleshooting

### Issue: "OpenAI API key not configured"

**Solution:**
```bash
# Check .env file exists
cat .env | grep OPENAI_API_KEY

# Test API key is valid
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer sk-your-key"
```

### Issue: "Connection Failed" on dashboard

**Solution:**
```bash
# Check service is running
curl http://localhost:8000/health/ready

# Check logs
tail -f logs/gateway-*.log
```

### Issue: Agent runs very slowly

**Solution:**
- This is normal! GPT-4o mini takes 10-30 seconds per step
- Patience is part of the demo
- Production agents would be much faster (batch decisions)

### Issue: "Comparison never completes"

**Solution:**
- Give it time (60+ seconds for 5 steps each mode)
- Each agent runs independently
- Monitor logs for progress

---

## Next Steps After Demo

1. **Review Module Architecture**
   - Read `MODULE_ARCHITECTURE.md`
   - Understand 7-layer safety model

2. **Integrate Your Database**
   - Update `execution/service.py`
   - Configure `policy_engine/` with your policies
   - Test with your data

3. **Configure Monitoring**
   - Set up log aggregation
   - Configure alerts for blocks
   - Create dashboards in your monitoring tool

4. **Deploy to Production**
   - Follow `DEPLOYMENT.md`
   - Configure SSL/TLS
   - Set up backups
   - Train your team

---

## Demo Source Code Reference

- **AI Agent Implementation:** `app/modules/ai_agent/service.py`
- **Demo Routes:** `app/routes/agent_demo.py`
- **Dashboard UI:** `static/agent-monitor.html`
- **Module Documentation:** `MODULE_ARCHITECTURE.md`

---

## Support & Questions

- **API Docs:** http://localhost:8000/docs
- **OpenAI Docs:** https://platform.openai.com/docs
- **Safety Gateway Docs:** See `PRODUCTION_README.md`

---

**Demo Status:** ✅ Production-ready
**Last Updated:** 2026-05-07
**Version:** 1.0.0
