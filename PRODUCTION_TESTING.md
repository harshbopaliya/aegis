# Production Testing & Verification Guide

## Pre-Deployment Verification Checklist

### 1. Unit Tests

```bash
# Run all unit tests
pytest tests/ -v --cov=app --cov-report=html

# Minimum coverage requirement
pytest tests/ --cov=app --cov-fail-under=80
```

**Coverage Requirements**:
- Overall: 80% minimum
- Gateway service: 90% minimum
- Policy engine: 85% minimum
- Critical paths: 100%

### 2. Integration Tests

```bash
# Test with real database
pytest tests/integration/ -v

# Test with Docker
docker-compose -f docker-compose.test.yml up
```

### 3. API Endpoint Tests

#### Health Checks

```bash
# Basic health
curl -v http://localhost:8000/health

# Readiness check
curl -v http://localhost:8000/health/ready

# Liveness check
curl -v http://localhost:8000/health/live
```

#### Safe Operations

```bash
# GET request (should execute)
curl -X POST http://localhost:8000/v1/actions \
  -H "Content-Type: application/json" \
  -d '{
    "verb": "GET",
    "resource": "table:orders",
    "environment": "staging",
    "role": "read_only",
    "actor_id": "test-agent"
  }'
```

#### Dangerous Operations

```bash
# DELETE on production (should require approval)
curl -X POST http://localhost:8000/v1/actions \
  -H "Content-Type: application/json" \
  -d '{
    "verb": "DELETE",
    "resource": "table:users",
    "environment": "production",
    "role": "production_operator",
    "actor_id": "test-agent"
  }'
```

### 4. Performance Testing

#### Load Testing with Apache Bench

```bash
# 1000 requests, 10 concurrent
ab -n 1000 -c 10 http://localhost:8000/health
```

#### Load Testing with wrk

```bash
wrk -t4 -c100 -d30s http://localhost:8000/v1/actions \
  --script=load-test.lua
```

#### Expected Performance

- P50 latency: < 100ms
- P95 latency: < 500ms
- P99 latency: < 1000ms
- Throughput: > 100 actions/second

### 5. Security Testing

#### HTTPS/TLS

```bash
# Test TLS version
openssl s_client -connect localhost:443 -tls1_2

# Check certificate
openssl s_client -connect localhost:443 | openssl x509 -text -noout
```

#### Security Headers

```bash
curl -I https://localhost/ | grep -E "Security|X-"
```

Expected headers:
- `Strict-Transport-Security`: max-age=31536000
- `X-Content-Type-Options`: nosniff
- `X-Frame-Options`: DENY
- `Content-Security-Policy`: default-src 'self'

#### SQL Injection Testing

```bash
# Should be rejected (validation error)
curl -X POST http://localhost:8000/v1/actions \
  -H "Content-Type: application/json" \
  -d '{
    "verb": "GET",
    "resource": "table:users WHERE 1=1",
    "environment": "production",
    "role": "read_only",
    "actor_id": "test"
  }'
```

#### Rate Limiting

```bash
# Should be rate limited after threshold
for i in {1..150}; do
  curl -X POST http://localhost:8000/v1/actions \
    -H "Content-Type: application/json" \
    -d '{"verb":"GET","resource":"table:users","environment":"staging","role":"read_only","actor_id":"test"}' &
done
wait
```

### 6. Database & Backup Testing

#### Database Integrity

```bash
# Verify database integrity
sqlite3 data/gateway.db "PRAGMA integrity_check;"

# Check database size
du -h data/gateway.db
```

#### Backup Creation

```bash
# Trigger backup manually
curl -X POST http://localhost:8000/v1/system/backup

# Verify backup exists
ls -lh data/backups/
```

#### Backup Restoration

```bash
# Test restore process
1. Copy backup file
2. Stop application
3. Restore database from backup
4. Start application
5. Verify all data is accessible
```

### 7. Configuration Testing

#### Environment Variables

```bash
# Verify all required variables are set
python -c "from app.config import settings; print(settings)"

# Test with different environments
ASG_ENVIRONMENT=staging python -c "from app.config import settings; print(settings.environment)"
```

#### Configuration Validation

```bash
# Should fail: missing encryption key with encrypt mode
ASG_AUDIT_PAYLOAD_MODE=encrypt python -m app.main
# Expected: ValueError: fernet_key required

# Should succeed: valid configuration
ASG_ENVIRONMENT=production ASG_DEBUG=false python -m app.main
```

### 8. Logging & Audit Testing

#### Log Output

```bash
# Check structured logs
tail -f logs/gateway-*.log | jq .

# Search for errors
grep "ERROR" logs/gateway-*.log
```

#### Audit Trail

```bash
# Query audit events
curl http://localhost:8000/v1/dashboard/events?limit=10
```

### 9. Failover & Disaster Recovery

#### Simulated Failure

```bash
# Kill container
docker kill aegis

# Verify auto-restart
docker ps | grep aegis

# Check recovery logs
docker logs aegis | tail -20
```

#### Database Failure

```bash
# Simulate database corruption
mv data/gateway.db data/gateway.db.bak

# Start application (should use backup)
docker-compose restart gateway

# Verify recovery
curl http://localhost:8000/v1/dashboard/overview
```

### 10. Monitoring & Alerting

#### Prometheus Metrics

```bash
# Scrape metrics
curl http://localhost:9090/api/v1/targets

# Query specific metric
curl 'http://localhost:9090/api/v1/query?query=gateway_requests_total'
```

#### Alert Testing

```bash
# Test alert rule
curl -X POST http://localhost:9090/api/v1/alerts/test
```

## Production Deployment Validation

### Pre-Deployment

```bash
#!/bin/bash
set -e

echo "========== Pre-Deployment Validation =========="

# 1. Run all tests
echo "Running tests..."
pytest tests/ --cov=app --cov-fail-under=80 || exit 1

# 2. Code quality checks
echo "Running linters..."
black --check app/
isort --check-only app/
flake8 app/ || true
mypy app/ || true

# 3. Security checks
echo "Security scanning..."
# Add security scanning tools (bandit, safety, etc.)

# 4. Build Docker image
echo "Building Docker image..."
docker build -t aegis:prod .

# 5. Test Docker image
echo "Testing Docker image..."
docker run --rm aegis:prod python -m pytest --version

echo "========== Pre-Deployment Validation PASSED =========="
```

### Post-Deployment

```bash
#!/bin/bash

echo "========== Post-Deployment Validation =========="

ENDPOINT="https://api.yourdomain.com"

# 1. Health check
echo "Checking health endpoints..."
curl -f "$ENDPOINT/health" || exit 1
curl -f "$ENDPOINT/health/ready" || exit 1
curl -f "$ENDPOINT/health/live" || exit 1

# 2. API endpoint test
echo "Testing API endpoints..."
curl -f -X POST "$ENDPOINT/v1/actions" \
  -H "Content-Type: application/json" \
  -d '{"verb":"GET","resource":"table:test","environment":"staging","role":"read_only","actor_id":"test"}' \
  || exit 1

# 3. Dashboard access
echo "Verifying dashboard..."
curl -f "$ENDPOINT/dashboard" || exit 1

# 4. Check logs for errors
echo "Checking logs for errors..."
if grep -i "ERROR\|CRITICAL" logs/gateway-*.log; then
  echo "WARNING: Errors found in logs"
fi

echo "========== Post-Deployment Validation PASSED =========="
```

## Continuous Monitoring

### Key Metrics to Monitor

```
- Request latency (p50, p95, p99)
- Error rate (errors / total requests)
- Policy block rate (blocks / total)
- Pending approvals count
- Average risk score
- Database size growth
- Backup success rate
- Uptime percentage
```

### Alert Thresholds

```
- Error rate > 5%: WARNING
- Error rate > 10%: CRITICAL
- Latency p99 > 5s: WARNING
- Latency p99 > 10s: CRITICAL
- Policy blocks > 20%: INVESTIGATE
- Pending approvals > 50: INVESTIGATE
- Backup failures: IMMEDIATE ACTION
- Disk space < 10%: WARNING
```

## Testing Automation

### GitHub Actions Example

```yaml
name: Pre-Deployment Validation

on: [pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest tests/ --cov=app --cov-fail-under=80
      - name: Code quality
        run: black --check app/ && isort --check-only app/
      - name: Security scan
        run: |
          pip install bandit safety
          bandit -r app/
          safety check
```

## Performance Baselines

Update these after each deployment:

- Throughput: ___ req/sec
- P50 Latency: ___ ms
- P95 Latency: ___ ms
- Error Rate: ___%
- Uptime: __%
- Database Size: ___ MB
- Memory Usage: ___ MB
