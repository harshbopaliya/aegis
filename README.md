# Aegis - Production Edition v2.0.0

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-00a393.svg)](https://fastapi.tiangolo.com)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**AEGIS** stands for **AI Environment Guard & Inspection System**. Like the mythical shield, it serves as an impenetrable protective layer between autonomous AI agents and your production databases, APIs, and infrastructure.

It is a production-grade installable Python package providing a **FastAPI safety gateway** control plane for AI agents. Proposed actions flow through **token scoping**, **policy guardrails**, **sandbox simulation**, **risk scoring**, optional **human-in-the-loop**, a single **execution choke point** with pluggable backend adapters, **observability with JSONL + database audit**, and **backup snapshot metadata** with rollback simulation.

**Status**: ✅ **Production Ready** - Fully tested and hardened for enterprise deployment

---

## Quick Start for Production

**👉 New to this project?** Start with [PRODUCTION_README.md](PRODUCTION_README.md) for a 5-minute deployment guide.

**📚 API Users?** See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for complete endpoint reference.

**🚀 Deploying to Production?** Read [DEPLOYMENT.md](DEPLOYMENT.md) for full procedures.

**🧪 Testing?** Check [PRODUCTION_TESTING.md](PRODUCTION_TESTING.md) for validation checklists.

---

## Client-Facing Surfaces

- **Marketing / showcase site:** http://127.0.0.1:8000/ — what the product is, how clients integrate, access model, and **privacy boundary** (production data stays on the client side).
- **Operator dashboard (observability):** http://127.0.0.1:8000/dashboard — includes **Agent Live Monitor** tab for active pipelines, events, request inspection, snapshots, and module coverage.
- **OpenAPI:** http://127.0.0.1:8000/docs
- **LLM comparison simulator:** http://127.0.0.1:8000/demo (uses OpenAI `gpt-4o-mini` when `OPENAI_API_KEY` is configured)
- **JSON discovery (for automation):** http://127.0.0.1:8000/api/info — links to the routes above.

## Dashboard JSON APIs (for your own UI or automation)

- `GET /v1/dashboard/overview?hours=24` — KPIs, active agent requests, pending approvals, recent completions, snapshots, module list.
- `GET /v1/dashboard/events?limit=80&offset=0` — newest audit rows.
- `GET /v1/dashboard/requests/{request_id}` — per-request audit timeline plus active pipeline state when applicable.

Agents should call **`POST /v1/actions`** only (never raw production APIs). Humans resolve **`POST /v1/approvals`** when the gateway returns `pending_human_approval`.

---

## Pluggable Backend Adapters

Aegis abstracts storage, human loop queueing, and action execution into three base adapter classes defined in `aegis.adapters.base`:

1. **`StorageBackend`**: Persists agent registration, policy rules, audit events, and backup snapshots.
2. **`ApprovalQueue`**: Manages human-in-the-loop pending approval queues.
3. **`ExecutionBackend`**: Connects approved actions to the destination systems (SQL databases, HTTP services, shell commands, etc.).

By default, Aegis ships with a local `SQLite` adapter. You can create your own backend classes and plug them in using the application factory:

```python
from aegis import create_app
from my_custom_adapters import MyPostgreSQLStorage, MyRedisQueue, MyDockerSandboxExecutor

app = create_app(
    storage=MyPostgreSQLStorage(),
    approval_queue=MyRedisQueue(),
    execution=MyDockerSandboxExecutor()
)
# Run app using: uvicorn my_app:app --host 0.0.0.0 --port 8000
```

---

## Setup

### Installation

```powershell
# Clone repository
git clone https://github.com/harshbopaliya/aegis.git
cd aegis

# Copy configuration
cp .env.example .env
# Edit .env with your values

# Option 1: Docker (Recommended for Production)
docker-compose up -d

# Option 2: Local development
pip install -e ".[server,dev]"
```

### Command Line Interface (CLI)

The package installs a command line utility `aegis` for server management and utility tasks:

```bash
# Start server
aegis serve --host 0.0.0.0 --port 8000

# Start server in debug reload mode
aegis serve --debug

# Equivalent direct uvicorn command (recommended when using reload/workers explicitly)
uvicorn aegis.server:app --host 0.0.0.0 --port 8000 --reload

# Generate default configuration
aegis init-config > .env

# Check server health
aegis health --url http://localhost:8000

# Generate API Key
aegis generate-key admin

# Generate Encryption Fernet Key
aegis generate-fernet-key
```

> If you run `python main.py serve` and see:
> `WARNING: You must pass the application as an import string to enable 'reload' or 'workers'`,
> use `aegis serve --debug` or `uvicorn aegis.server:app --reload` instead.

### OpenAI Setup for Real Agent Simulator

To enable real AI behavior in the simulator (`/demo` and `/api/demo/compare`), set:

```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
```

### Python SDK Client

Aegis provides a built-in HTTP client for easy integration into your agent frameworks:

```python
from aegis.client import AegisClient
from aegis.models.schemas import HttpVerb, Environment, Role

client = AegisClient("http://localhost:8000", api_key="your-key-here")

# Check health
health = client.health()

# Submit action
result = client.submit_action(
    verb=HttpVerb.GET,
    resource="table:orders",
    environment=Environment.STAGING,
    role=Role.READ_ONLY,
    actor_id="my-agent-id",
    payload={"query": "limit 10"}
)

print(result.final_outcome)  # 'executed' or 'pending_human_approval' or 'blocked_rbac'
```

---

## Tests

```powershell
# Run all tests
pytest

# With coverage report
pytest --cov=aegis --cov-report=html

# Minimum coverage: 80%
pytest --cov=aegis --cov-fail-under=80
```

---

## Documentation

| Document | Purpose |
|----------|---------|
| [PRODUCTION_README.md](PRODUCTION_README.md) | **→ START HERE** Quick start guide for production |
| [API_DOCUMENTATION.md](API_DOCUMENTATION.md) | Complete API reference with examples |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Full deployment procedures and infrastructure |
| [PRODUCTION_TESTING.md](PRODUCTION_TESTING.md) | Testing checklist and validation strategies |
| [CHANGELOG.md](CHANGELOG.md) | Version history and migration guides |

## Files of Interest

### Core Application
- [aegis/server.py](file:///c:/code%20playground/personal/ai_safety_now/aegis/aegis/server.py) — Production FastAPI application factory
- [aegis/config.py](file:///c:/code%20playground/personal/ai_safety_now/aegis/aegis/config.py) — Settings configuration with validation
- [aegis/services/gateway.py](file:///c:/code%20playground/personal/ai_safety_now/aegis/aegis/services/gateway.py) — Safety pipeline orchestration
- [aegis/client.py](file:///c:/code%20playground/personal/ai_safety_now/aegis/aegis/client.py) — Python SDK client
- [aegis/cli.py](file:///c:/code%20playground/personal/ai_safety_now/aegis/aegis/cli.py) — CLI management tool

### Pluggable Backend Adapters
- [aegis/adapters/base.py](file:///c:/code%20playground/personal/ai_safety_now/aegis/aegis/adapters/base.py) — Abstract Base Classes for adapters
- [aegis/adapters/sqlite.py](file:///c:/code%20playground/personal/ai_safety_now/aegis/aegis/adapters/sqlite.py) — Default SQLite adapter
- [aegis/adapters/memory.py](file:///c:/code%20playground/personal/ai_safety_now/aegis/aegis/adapters/memory.py) — Mock in-memory adapter (tests / quick starts)

---

## License

Apache License 2.0 - See [LICENSE](LICENSE) file
