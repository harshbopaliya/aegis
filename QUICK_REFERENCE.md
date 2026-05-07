# Quick Reference Card - Aegis

## Essential Commands

### Setup
```bash
cp .env.example .env                    # Configure environment
docker-compose up -d                    # Start all services
docker-compose logs -f gateway          # View logs
```

### Health & Monitoring
```bash
curl http://localhost:8000/health                # Basic health
curl http://localhost:8000/health/ready          # Readiness probe
curl http://localhost:8000/health/live           # Liveness probe
docker-compose ps                               # Service status
```

### API Testing
```bash
# Safe operation (should execute)
curl -X POST http://localhost:8000/v1/actions \
  -H "Content-Type: application/json" \
  -d '{"verb":"GET","resource":"table:orders","environment":"staging","role":"read_only","actor_id":"test"}'

# Dangerous operation (should require approval)
curl -X POST http://localhost:8000/v1/actions \
  -H "Content-Type: application/json" \
  -d '{"verb":"DELETE","resource":"table:users","environment":"production","role":"production_operator","actor_id":"test"}'
```

### Logs & Monitoring
```bash
tail -f logs/gateway-*.log          # Application logs
tail -f logs/gateway-error.log      # Error logs
curl http://localhost:9090          # Prometheus metrics
docker exec gateway sqlite3 /app/data/gateway.db "SELECT COUNT(*) FROM audit_events;"  # Database size
```

### Backup & Recovery
```bash
ls -lh data/backups/                # List backups
docker exec gateway sqlite3 /app/data/gateway.db ".backup /app/data/backups/backup-$(date +%s).db"  # Manual backup
```

### Development
```bash
make test                    # Run tests
make lint                    # Check code quality
make format                  # Format code
make docker-build           # Build Docker image
```

## Configuration Essentials

```bash
# .env file key settings
ASG_ENVIRONMENT=production              # production | staging | development
ASG_DEBUG=false                         # Never true in production
ASG_REQUIRE_HTTPS=true                  # Enforce HTTPS
ASG_FERNET_KEY=<your-key>              # Encryption key
ASG_AUDIT_PAYLOAD_MODE=redact          # redact | encrypt | full
ASG_RATE_LIMIT_ACTIONS_PER_MINUTE=100  # Per your scale
ASG_REQUIRE_AGENT_REGISTRATION=true    # Require agent registration
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Service Unavailable" | Check: `docker-compose logs gateway` \| Check DB: `curl http://localhost:8000/health/ready` |
| High latency | Check: `docker stats` \| Review: `logs/gateway-*.log` for slowdown patterns |
| Backup failures | Check disk: `df -h data/` \| Check perms: `ls -ld data/backups/` |
| Auth errors | Verify: `ASG_REQUIRE_AGENT_REGISTRATION` setting \| Check: headers `X-Actor-ID` |
| Rate limit hits | Increase: `ASG_RATE_LIMIT_*` settings OR implement queue \| Check: `X-RateLimit-*` headers |

## Response Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Executed | ✅ Action completed |
| 202 | Pending Approval | ⏳ Human approval required |
| 400 | Bad Request | ❌ Invalid parameters, check request |
| 401 | Unauthorized | ❌ Missing/invalid auth |
| 403 | Forbidden | ❌ Blocked by policy/RBAC |
| 429 | Rate Limited | ⏸️ Too many requests, wait |
| 500 | Server Error | 🔧 Check logs, contact support |

## Alert Thresholds

Monitor these metrics and alert when exceeded:

```
Error Rate > 5%                    → WARNING
Error Rate > 10%                   → CRITICAL
API Latency p99 > 5s              → WARNING
API Latency p99 > 10s             → CRITICAL
Policy Blocks > 20%               → INVESTIGATE
Pending Approvals > 50            → INVESTIGATE
Backup Failures                   → IMMEDIATE ACTION
Disk Space < 10%                  → WARNING
```

## Important Files

| File | Purpose |
|------|---------|
| `.env` | **NEVER** commit! Contains secrets |
| `data/gateway.db` | Main database - backup regularly |
| `logs/` | Application logs - rotate daily |
| `data/backups/` | Encrypted backups - verify working |
| `docker-compose.yml` | Service configuration |
| `nginx.conf` | Reverse proxy configuration |

## Emergency Procedures

### Database Corruption
```bash
docker-compose down
rm data/gateway.db
# Restore from backup or initialize fresh
docker-compose up -d
```

### Key Compromise
```bash
# 1. STOP service immediately
docker-compose down

# 2. Generate new key:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 3. Update .env with new key

# 4. Re-encrypt backups and sensitive data

# 5. Restart
docker-compose up -d

# 6. ALERT all stakeholders
# 7. AUDIT all access logs
```

### Service Failure
```bash
# Check status
docker-compose ps

# View logs
docker-compose logs gateway | tail -50

# Restart service
docker-compose restart gateway

# Verify
curl http://localhost:8000/health/ready
```

## Documentation Links

- **Quick Start**: PRODUCTION_README.md
- **API Docs**: API_DOCUMENTATION.md
- **Deployment**: DEPLOYMENT.md
- **Testing**: PRODUCTION_TESTING.md
- **Changes**: CHANGELOG.md

## Key Contacts

- **Platform Support**: support@yourdomain.com
- **Security Issues**: security@yourdomain.com
- **On-Call**: [insert contact]

---

**Version**: 1.0.0 | **Updated**: 2026-05-07 | **Status**: ✅ Ready
