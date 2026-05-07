# Aegis - Production Edition v1.0.0

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-00a393.svg)](https://fastapi.tiangolo.com)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**AEGIS** stands for **AI Environment Guard & Inspection System**. Like the mythical shield, it serves as an impenetrable protective layer between autonomous AI agents and your production databases, APIs, and infrastructure.

Production-style **FastAPI control plane** for AI agents: proposed actions flow through **token scoping**, **policy guardrails**, **sandbox simulation**, **risk scoring**, optional **human-in-the-loop**, a single **execution choke point** (SQLite demo / your adapters), **observability with SQLite + JSONL audit**, and **backup snapshot metadata** with rollback simulation.

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
- **Operator dashboard (observability):** http://127.0.0.1:8000/dashboard — live agent pipelines, pending approvals, audit stream, snapshots.
- **OpenAPI:** http://127.0.0.1:8000/docs
- **LLM comparison demo:** http://127.0.0.1:8000/demo (requires `OPENAI_API_KEY`)
- **JSON discovery (for automation):** http://127.0.0.1:8000/api/info — links to the routes above.

## Dashboard JSON APIs (for your own UI or automation)

- `GET /v1/dashboard/overview?hours=24` — KPIs, active agent requests, pending approvals, recent completions, snapshots, module list.
- `GET /v1/dashboard/events?limit=80&offset=0` — newest audit rows (same data mirrored to `logs/audit-YYYY-MM-DD.jsonl`).
- `GET /v1/dashboard/requests/{request_id}` — per-request audit timeline plus active pipeline state when applicable.

Agents should call **`POST /v1/actions`** only (never raw production APIs). Humans resolve **`POST /v1/approvals`** when the gateway returns `pending_human_approval`.

## Architecture (Layers)

| Step | Module | Role |
|------|--------|------|
| 1 | Token scoping | RBAC / least privilege by role |
| 2 | Policy engine | Allow / block / require approval |
| 3 | Sandbox | Dry-run prediction (no prod side effects) |
| 4 | Risk scoring | 0–100 score and tier |
| 5 | Human-in-the-loop | Queue and approve/reject |
| — | Execution | Controlled mutations (gateway code paths only) |
| 6 | Observability | SQLite `audit_events` + JSONL files + JSON API |
| 7 | Backup & recovery | Snapshot metadata + rollback simulation API |

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
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Generate Encryption Key (Required for Production)

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Store output in .env as ASG_FERNET_KEY
```

## Run

### Docker (Production Recommended)

```powershell
docker-compose up -d

# Verify
curl http://localhost:8000/health/ready
docker-compose logs -f gateway
```

### Local Development

```powershell
pip install -r requirements.txt
make run
# or
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open the **showcase site** at http://127.0.0.1:8000/ , **dashboard** at http://127.0.0.1:8000/dashboard , and docs at http://127.0.0.1:8000/docs .

## Configuration

Settings load from the environment and from `.env` in the **project root** (`aegis/.env`), regardless of your current working directory when you start the server.

### Essential Settings

```bash
# Production
ASG_ENVIRONMENT=production
ASG_DEBUG=false
ASG_REQUIRE_HTTPS=true

# Security
ASG_REQUIRE_AGENT_REGISTRATION=true
ASG_ENFORCE_AGENT_ROLES_FROM_REGISTRY=true
ASG_STRICT_BLOCK_DELETE_PRODUCTION=true
ASG_AUDIT_PAYLOAD_MODE=redact  # or encrypt

# Encryption Key (required if audit_payload_mode=encrypt)
ASG_FERNET_KEY=<your-generated-key>

# OpenAI (for demo only)
OPENAI_API_KEY=sk-...
```

**See [.env.example](.env.example)** for all 50+ configurable parameters.

## Production Hardening

- ✅ Terminate **TLS** at your reverse proxy (nginx, Envoy, cloud LB) — Nginx config included
- ✅ Restrict **`/dashboard`** and **`/v1/dashboard/*`** to trusted networks or SSO
- ✅ Treat **`POST /v1/actions`** and **`POST /v1/approvals`** as authenticated admin APIs (wrap with API gateway auth or mutual TLS)
- ✅ Point **`ASG_SQLITE_PATH`** / **`ASG_DATA_DIR`** at durable disk; back up SQLite and **`logs/`** for compliance
- ✅ Replace demo **execution** (`app/modules/execution.py`) with your real connectors while keeping the same gateway orchestration
- ✅ Set up monitoring (Prometheus config included)
- ✅ Configure automated backups (6-hour intervals recommended)
- ✅ Review and enforce rate limiting per your scale

## Tests

```powershell
# Run all tests
python -m pytest tests -v

# With coverage report
python -m pytest tests -v --cov=app --cov-report=html

# Minimum coverage: 80%
python -m pytest tests --cov=app --cov-fail-under=80
```

## Make Commands (Convenience)

```bash
make help              # Show all commands
make test             # Run tests with coverage
make lint             # Run linters
make format           # Format code
make security         # Security checks
make docker-up        # Start Docker stack
make docker-down      # Stop Docker stack
make health           # Check health endpoints
make logs             # Tail logs
make deploy           # Deploy to production
```

See [Makefile](Makefile) for all available commands.

## API Examples

### Health Check

```bash
curl -s http://127.0.0.1:8000/health
```

### Safe Read (Should Execute)

```bash
curl -s -X POST http://127.0.0.1:8000/v1/actions \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: $(uuidgen)" \
  -d '{
    "verb": "GET",
    "resource": "table:demo_orders",
    "environment": "staging",
    "role": "read_only",
    "actor_id": "agent-001"
  }'
```

### Dangerous Operation (Pending Approval)

```bash
REQUEST_ID=$(uuidgen)

curl -s -X POST http://127.0.0.1:8000/v1/actions \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: $REQUEST_ID" \
  -d '{
    "verb": "DELETE",
    "resource": "table:users",
    "environment": "production",
    "role": "production_operator",
    "actor_id": "agent-001"
  }'

# Extract approval_id from response, then:

curl -s -X POST http://127.0.0.1:8000/v1/approvals \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "'$REQUEST_ID'",
    "approver_id": "human-1",
    "approve": true,
    "reason": "Verified legitimate deletion"
  }'
```

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
- `app/main.py` — Production FastAPI app with middleware, error handling
- `app/config.py` — 100+ configurable parameters with validation
- `app/services/gateway.py` — Safety pipeline orchestration

### Infrastructure
- `Dockerfile` — Multi-stage optimized production image
- `docker-compose.yml` — Complete stack (gateway + Nginx + Prometheus)
- `nginx.conf` — Reverse proxy with TLS, rate limiting, security headers
- `.env.example` — All configuration parameters documented

### Logging & Monitoring
- `app/core/logging_config.py` — Structured JSON logging
- `app/core/middleware.py` — Security middleware (CORS, rate limiting, tracking)
- `app/core/exceptions.py` — Production exception hierarchy
- `prometheus.yml` — Monitoring configuration

### Deployment
- `aegis.service` — Systemd service file
- `Makefile` — Common operations
- `.gitignore` — Comprehensive ignore patterns
- `pyproject.toml` — Python packaging and tool configuration

## Open Source & Community

We believe in building secure AI systems together. Aegis is an open-source project and we welcome contributions!

- **[Contributing Guide](CONTRIBUTING.md)** - How to get started with contributing (setup, pull requests, code style).
- **[Code of Conduct](CODE_OF_CONDUCT.md)** - Our community standards and expectations.
- **[Security Policy](SECURITY.md)** - How to responsibly report security vulnerabilities.
- **[Contributors](CONTRIBUTORS.md)** - List of people who helped build this gateway.

We encourage you to open issues for bugs and feature requests, and to submit pull requests.

## Version

- **Current Version**: 1.0.0
- **Release Date**: 2026-05-07
- **Status**: ✅ Production Ready
- **Python**: 3.11+
- **FastAPI**: 0.109+

## Support

- **Documentation**: See links above
- **API Docs**: http://localhost:8000/docs (when running)
- **GitHub**: [harshbopaliya/aegis](https://github.com/harshbopaliya/aegis)
- **Email**: support@yourdomain.com
- **Security Issues**: security@yourdomain.com

## License

Apache License 2.0 - See [LICENSE](LICENSE) file

---

**Ready to deploy?** → [PRODUCTION_README.md](PRODUCTION_README.md)

**Questions?** → [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
