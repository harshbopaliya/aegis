# AI Agent Demo Dashboard — Complete Reference

## Dashboard URL

```
http://localhost:8000/agent-monitor.html
```

---

## Interface Overview

### Header Section
- **Title:** "🤖 AI Agent Safety Demo"
- **Subtitle:** "Real-time monitoring: Compare behavior WITH vs WITHOUT safety gateway"
- **Status Indicator:** Shows OpenAI API connectivity status

### Control Panel

**Input Fields:**
```
┌─ Objective Input ────────────────────────────┐
│ "Manage customer data safely"                │
└──────────────────────────────────────────────┘

┌─ Steps Input ─┐
│ 5             │
└───────────────┘
```

**Action Buttons:**

| Button | Function | Duration |
|--------|----------|----------|
| ▶ **Run WITH Safety Gateway** | Execute agent with all safety controls | 30-50s (5 steps) |
| ▶ **Run WITHOUT Safety Gateway** | Execute agent unrestricted (⚠️ demo only) | 30-50s (5 steps) |
| ⚖ **Side-by-Side Comparison** | Run both modes and compare results | 60-100s (5 steps each) |

### System Status Panel

**Shows:**
```
System Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🟢 OpenAI API Ready
   (Updates every 30 seconds)
```

**Color Meanings:**
- 🟢 **Green:** API is accessible, keys valid
- 🔴 **Red:** API error or key invalid
- ⏳ **Checking:** Initial status check in progress

---

## Step-by-Step Example Output

### When You Click "Run WITH Safety Gateway"

**Real-time Display:**

```
────────────────────────────────────────────────────
Step 1
────────────────────────────────────────────────────
"Let me check the customer orders table"
GET table:orders (staging)
│
├─ Risk Score: 10/100
├─ Safety Decision: ✅ ALLOW
├─ Reason: "No policy violations detected"
│
└─ Result: 42 rows returned successfully
```

```
────────────────────────────────────────────────────
Step 2
────────────────────────────────────────────────────
"I should update the order statuses"
POST table:orders (staging)
│
├─ Risk Score: 50/100
├─ Safety Decision: ✅ ALLOW
├─ Reason: "No policy violations detected"
│
└─ Result: Insert executed (10 records modified)
```

```
────────────────────────────────────────────────────
Step 3
────────────────────────────────────────────────────
"Let me delete old user accounts in production"
DELETE table:users (production)
│
├─ Risk Score: 92/100 ⚠️ CRITICAL
├─ Safety Decision: ❌ BLOCK
├─ Reason: "DELETE in production is blocked by policy"
│
└─ Result: Blocked by safety policy (nothing executed)
```

**Summary After Completion:**

```
🛡️ WITH Safety Gateway — Complete Session
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Steps         5
Blocked by Policy   2  ✅ Protected
Executed            3  ✅ Executed safely
Dangerous Attempts  3  ✅ Dangerous attempts blocked
Protection Rate    66.7% ✅ Effective protection
```

---

## Metrics Panel Display

### KPI Grid (4x4 Layout)

```
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│                 │                 │                 │                 │
│  Total Steps    │  Operations     │  Operations     │ Dangerous       │
│                 │  Executed       │  Blocked        │ Attempts        │
│                 │                 │                 │                 │
│       5         │        3        │        2        │        3        │
│                 │                 │                 │                 │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

**Color Coding:**
- Green metrics: ✅ Operations succeeded
- Orange metrics: ⏳ Operations pending
- Red metrics: ❌ Operations blocked

---

## Step Details View

Each step shows:

### Step Header
```
Step 3: DELETE table:users
┌──────────────────────────────┬────────────┐
│ Agent Thought                │ BLOCK ❌   │
└──────────────────────────────┴────────────┘
```

### Agent Thought (from GPT-4o mini)
```
"Let me delete inactive users to optimize storage"
(italic, muted text)
```

### Action Details
```
DELETE table:users (production)
(monospace, dark background)
```

### Risk Assessment
```
Risk Score: 92/100 (CRITICAL)
Factors:
- DELETE operation baseline (critical)
- production environment modifier
- high-value data surface
```

### Safety Decision Explanation
```
"DELETE in production is blocked by policy (strict mode)"
(colored background: red for BLOCK, green for ALLOW, yellow for PENDING)
```

### Execution Result
```
Status: ❌ Blocked by safety policy
(Shows why operation didn't execute)
```

---

## Side-by-Side Comparison View

When you click "⚖ Side-by-Side Comparison":

```
⚖️ Side-by-Side Comparison: WITH vs WITHOUT Safety Gateway
═══════════════════════════════════════════════════════════

Key Finding: Safety gateway prevented 2 dangerous operations 
that the unrestricted agent executed freely.

┌────────────────────────────┬────────────────────────────┐
│  ✅ WITH Safety Gateway    │  ⚠️ WITHOUT Safety Gateway │
├────────────────────────────┼────────────────────────────┤
│                            │                            │
│ Total Steps: 5             │ Total Steps: 5             │
│ Operations Executed: 3     │ Operations Executed: 5     │
│ Operations Blocked: 2      │ Operations Blocked: 0      │
│ Dangerous Attempts: 3      │ Dangerous Attempts: 3      │
│ Protection: 100%           │ Risk Level: CRITICAL       │
│                            │                            │
├────────────────────────────┼────────────────────────────┤
│ Step-by-Step:              │ Step-by-Step:              │
│                            │                            │
│ ✅ Step 1: GET (ALLOW)     │ ✅ Step 1: GET (ALLOW)     │
│ ✅ Step 2: POST (ALLOW)    │ ✅ Step 2: POST (EXECUTE)  │
│ ❌ Step 3: DELETE (BLOCK)  │ ❌ Step 3: DELETE (EXEC)   │
│ ⏳ Step 4: UPDATE (PENDING)│ ✅ Step 4: UPDATE (EXEC)   │
│ ✅ Step 5: GET (ALLOW)     │ ✅ Step 5: GET (EXECUTE)   │
│                            │                            │
└────────────────────────────┴────────────────────────────┘

Analysis & Impact
═══════════════════════════════════════════════════════════

Dangerous Attempts Blocked:     2  ✅ Prevented
Uncontrolled Executions:        3  ❌ Executed
Protection Rate:              100% ✅ Effective
```

---

## Color & Status Indicators

### Decision Badges

```
✅ ALLOW      Green background     Operation allowed to execute
⏳ PENDING     Yellow background    Awaiting human approval
❌ BLOCK      Red background       Operation blocked
```

### Risk Score Colors

```
🟢 GREEN:    0-39   (LOW)       → Auto-execute with audit
🟡 YELLOW:  40-69  (MEDIUM)    → May require approval
🔴 RED:     70-100 (HIGH)      → Almost always blocked/approval
```

### Step Type Indicators

```
Step with border-left:
├─ 🟢 Green: Executed successfully
├─ 🔴 Red: Blocked by policy
└─ 🟡 Yellow: Pending approval
```

---

## Understanding Real-Time Updates

As agent runs, dashboard updates in real-time:

**Timeline:**
```
[0s]   Click button
       ↓
[2s]   Status: "Running agent WITH safety gateway..."
       ↓
[5s]   Step 1 appears in dashboard
       ↓
[10s]  Step 2 appears in dashboard
       ↓
[15s]  Step 3 appears in dashboard
       ↓
...continue for 5 steps...
       ↓
[50s]  Final summary appears
       ↓
[51s]  Status: "✅ Session completed"
```

---

## Data Fields in Each Step

When you see a step, it shows:

```
{
  "step_number": 1,
  "timestamp": "2026-05-07T14:22:15.123Z",
  "thought": "What GPT thinks it should do",
  "proposed_action": {
    "verb": "GET|POST|PUT|PATCH|DELETE",
    "resource": "table:name or entity:id",
    "environment": "staging|production"
  },
  "safety_decision": "ALLOW|REQUIRE_APPROVAL|BLOCK",
  "safety_reason": "Explanation of decision",
  "execution_result": {
    "success": true/false,
    "rows": [...],              // For GET
    "message": "What happened"
  },
  "risk_score": 0-100,
  "with_safety_gateway": true/false
}
```

---

## API Response Format

Dashboard receives JSON like:

```json
{
  "success": true,
  "session": {
    "session_id": "sess_1715096520_demo-safe",
    "agent_name": "Safety-Protected Agent",
    "objective": "Manage customer data safely",
    "with_safety_gateway": true,
    "steps": [
      {
        "step_number": 1,
        "thought": "Let me analyze customer data",
        "proposed_action": {
          "verb": "GET",
          "resource": "table:orders",
          "environment": "staging"
        },
        "safety_decision": "ALLOW",
        "safety_reason": "No policy violations detected",
        "execution_result": {
          "ok": true,
          "rows": [{"id": 1, "label": "Order 1"}]
        },
        "risk_score": 10
      }
    ],
    "data_accessed": 42,
    "data_modified": 3,
    "dangerous_attempts": 1,
    "blocked_by_policy": 1
  },
  "summary": {
    "total_steps": 5,
    "operations_executed": 3,
    "operations_blocked": 2,
    "dangerous_attempts": 3,
    "protection_effectiveness": "100%"
  }
}
```

---

## Customizing the Demo

### Change Default Objective

Edit input field:
```
Current: "Manage customer data safely"

Try:
- "Delete inactive users in production"
- "Export all customer payment records"
- "Modify admin access controls"
- "Analyze customer behavior patterns"
```

### Change Number of Steps

Edit steps field:
```
Current: 5 steps

Try:
- 1 step (quick test)
- 3 steps (fast demo)
- 10 steps (comprehensive)
```

### Observe Different Behaviors

1. **First Run:**
   - WITH safety: Operations blocked
   - WITHOUT safety: All operations execute

2. **Second Run:**
   - Same objectives get same decisions
   - Different objectives get different outcomes
   - Comparison shows consistent protection

3. **Third Run:**
   - Try specific dangerous scenario
   - Observe how safety gateway prevents it
   - Note the audit trail

---

## Troubleshooting Dashboard

| Issue | Solution |
|-------|----------|
| Button disabled | Wait for previous run to finish |
| "Checking..." status | API check in progress, wait 5s |
| Steps not appearing | Check browser console (F12) for errors |
| No data in results | Verify OpenAI API key in .env |
| Dashboard blank | Refresh page (Ctrl+R) |
| Slow updates | Normal for GPT, be patient |

---

## Browser Compatibility

**Tested On:**
- ✅ Chrome 120+
- ✅ Firefox 120+
- ✅ Safari 16+
- ✅ Edge 120+

**Requirements:**
- JavaScript enabled
- Modern CSS support (Grid, Flexbox)
- Fetch API support

---

## Saving Results

Currently results display live but don't persist. To save:

1. **Screenshot:**
   - Take screenshot of results
   - Save as image

2. **Copy JSON:**
   - Open browser DevTools (F12)
   - Copy response from Network tab
   - Save as .json file

3. **Export:**
   - Note: Feature for future versions
   - Currently manual export recommended

---

## Performance Notes

**Expected Timings:**
```
Run WITH Safety:        30-50 seconds
Run WITHOUT Safety:     30-50 seconds
Side-by-Side Compare:   60-100 seconds

Per Step:               10-30 seconds (GPT thinking)
Dashboard Update:       <100ms
API Response:           <500ms (excluding GPT)
```

**Why it takes time:**
- GPT-4o mini needs 10-30s to think per step
- Multiple steps = multiple API calls
- Network latency adds up
- This is expected and normal

---

## Next Steps

1. **Run the demo** (5 min)
   - Side-by-side comparison shows the value

2. **Review results** (5 min)
   - Look at blocked operations
   - Understand why they were blocked

3. **Explore code** (15 min)
   - `app/routes/agent_demo.py` - API endpoints
   - `app/modules/ai_agent/service.py` - Agent logic
   - `static/agent-monitor.html` - Dashboard code

4. **Read docs** (15 min)
   - `MODULE_ARCHITECTURE.md` - Each layer
   - `DEMO.md` - Complete walkthrough

5. **Integrate** (ongoing)
   - Replace SQLite with production DB
   - Load your policies
   - Connect to your agents

---

**Dashboard Status:** ✅ Production-Ready
**Version:** 1.0.0
**Last Updated:** 2026-05-07
