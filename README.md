# AI Agent Safety Gateway

Production-style **FastAPI control plane** for AI agents: proposed actions flow through **token scoping**, **policy guardrails**, **sandbox simulation**, **risk scoring**, optional **human-in-the-loop**, a single **execution choke point** (SQLite demo / your adapters), **observability with SQLite + JSONL audit**, and **backup snapshot metadata** with rollback simulation.

**Client-facing surfaces**

- **Marketing / showcase site:** http://127.0.0.1:8000/ — what the product is, how clients integrate, access model, and **privacy boundary** (production data stays on the client side).
- **Operator dashboard (observability):** http://127.0.0.1:8000/dashboard — live agent pipelines, pending approvals, audit stream, snapshots.
- **OpenAPI:** http://127.0.0.1:8000/docs
- **LLM comparison demo:** http://127.0.0.1:8000/demo (requires `OPENAI_API_KEY`)
- **JSON discovery (for automation):** http://127.0.0.1:8000/api/info — links to the routes above.

**Dashboard JSON APIs (for your own UI or automation)**

- `GET /v1/dashboard/overview?hours=24` — KPIs, active agent requests, pending approvals, recent completions, snapshots, module list.
- `GET /v1/dashboard/events?limit=80&offset=0` — newest audit rows (same data mirrored to `logs/audit-YYYY-MM-DD.jsonl`).
- `GET /v1/dashboard/requests/{request_id}` — per-request audit timeline plus active pipeline state when applicable.

Agents should call **`POST /v1/actions`** only (never raw production APIs). Humans resolve **`POST /v1/approvals`** when the gateway returns `pending_human_approval`.

## Architecture (modules)

| Step | Module | Role |
|------|--------|------|
| 1 | Token scoping | RBAC / least privilege by role |
| 2 | Policy engine | Allow / block / require approval |
| 3 | Sandbox | Dry-run prediction (no prod side effects) |
| 4 | Risk scoring | 0–100 score and tier |
| 5 | Human-in-the-loop | Queue and approve/reject |
| — | Execution | Controlled mutations (gateway code paths only) |
| 6 | Observability | SQLite `audit_events` + JSONL files |
| 7 | Backup & recovery | Snapshot metadata + rollback simulation API |

## Setup

```powershell
cd ai-safety-gateway
pip install -r requirements.txt
```

## Run

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open the **showcase site** at http://127.0.0.1:8000/ , **dashboard** at http://127.0.0.1:8000/dashboard , and docs at http://127.0.0.1:8000/docs .

## Production hardening (first client checklist)

- Terminate **TLS** at your reverse proxy (nginx, Envoy, cloud LB).
- Restrict **`/dashboard`** and **`/v1/dashboard/*`** to trusted networks or SSO.
- Treat **`POST /v1/actions`** and **`POST /v1/approvals`** as authenticated admin APIs (wrap with API gateway auth or mutual TLS).
- Point **`ASG_SQLITE_PATH`** / **`ASG_DATA_DIR`** at durable disk; back up SQLite and **`logs/`** for compliance.
- Replace demo **execution** (`app/modules/execution.py`) with your real connectors while keeping the same gateway orchestration.

## Tests

```powershell
python -m pytest tests -v
```

## curl examples

Health:

```bash
curl -s http://127.0.0.1:8000/health
```

Example payload matching the destructive demo scenario (use as a body template):

```bash
curl -s http://127.0.0.1:8000/v1/examples/delete-production-users
```

Submit a safe read (should execute):

```bash
curl -s -X POST http://127.0.0.1:8000/v1/actions ^
  -H "Content-Type: application/json" ^
  -d "{\"verb\":\"GET\",\"resource\":\"table:demo_orders\",\"environment\":\"staging\",\"role\":\"read_only\",\"actor_id\":\"curl-demo\"}"
```

On Unix shells, replace `^` with `\` for line continuation or send one line.

Submit the demo DELETE on production (typically pending approval); then approve or reject using `request_id` and `approval_id` from the response:

```bash
curl -s -X POST http://127.0.0.1:8000/v1/actions -H "Content-Type: application/json" -d "{\"verb\":\"DELETE\",\"resource\":\"table:users\",\"environment\":\"production\",\"role\":\"production_operator\",\"actor_id\":\"curl-demo\"}"
```

```bash
curl -s -X POST http://127.0.0.1:8000/v1/approvals -H "Content-Type: application/json" -d "{\"request_id\":\"<REQUEST_ID>\",\"approver_id\":\"human-1\",\"approve\":false,\"reason\":\"reject demo\"}"
```

## Configuration

Settings load from the environment and from `.env` in the **project root** (`ai-safety-gateway/.env`), regardless of your current working directory when you start the server.

- **OpenAI (demo):** set a single variable `OPENAI_API_KEY` in `.env` or in the shell.
- **Other tunables:** use the `ASG_` prefix (for example `ASG_STRICT_BLOCK_DELETE_PRODUCTION=true`, `ASG_SQLITE_PATH`, `ASG_LOG_DIR`). See `app/config.py` for field names.
