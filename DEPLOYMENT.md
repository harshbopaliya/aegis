# Production Deployment Guide - Aegis

## Table of Contents
1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Environment Setup](#environment-setup)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Security Hardening](#security-hardening)
6. [Monitoring & Observability](#monitoring--observability)
7. [Backup & Recovery](#backup--recovery)
8. [Troubleshooting](#troubleshooting)

## Pre-Deployment Checklist

### Security Review
- [ ] Review all environment variables in `.env`
- [ ] Generate secure encryption keys (see below)
- [ ] Verify HTTPS certificates are valid
- [ ] Enable authentication on `/dashboard` and admin endpoints
- [ ] Configure rate limiting appropriately for your scale
- [ ] Review audit mode (`full`, `redact`, or `encrypt`)
- [ ] Test backup encryption end-to-end
- [ ] Review firewall rules and network policies

### Infrastructure Requirements
- [ ] Minimum 2 CPU cores, 4GB RAM
- [ ] SSD storage for database and logs (at least 50GB recommended)
- [ ] Reliable network with low latency to LLM services
- [ ] Regular backup system (automated daily minimum)
- [ ] Log aggregation system (ELK, Splunk, etc.)
- [ ] Monitoring platform (Prometheus, Datadog, etc.)

### Compliance
- [ ] Data retention policy defined
- [ ] Audit trail storage configured
- [ ] Encryption at rest enabled
- [ ] TLS 1.2+ for all communications
- [ ] Backup verification process documented
- [ ] Incident response plan prepared

## Environment Setup

### Generate Encryption Key

Required if using `audit_payload_mode=encrypt` or `encrypt_backup_files=true`:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Store this key securely in your `.env` file as `ASG_FERNET_KEY`.

### Create .env File

Copy from `.env.example` and customize:

```bash
cp .env.example .env
# Edit .env with your values
# NEVER commit .env to version control!
chmod 600 .env
```

### Essential Environment Variables

```bash
# Production settings
ASG_ENVIRONMENT=production
ASG_DEBUG=false
ASG_REQUIRE_HTTPS=true

# Security
ASG_REQUIRE_AGENT_REGISTRATION=true
ASG_ENFORCE_AGENT_ROLES_FROM_REGISTRY=true
ASG_STRICT_BLOCK_DELETE_PRODUCTION=true
ASG_AUDIT_PAYLOAD_MODE=redact
ASG_FERNET_KEY=<your-generated-key>

# Encryption
ASG_ENCRYPT_BACKUP_FILES=true
ASG_ENCRYPT_DATABASE=false

# CORS (update for your domain)
ASG_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
ASG_TRUSTED_HOSTS=yourdomain.com,api.yourdomain.com

# OpenAI (for demo only)
OPENAI_API_KEY=<your-api-key>
```

## Docker Deployment

### Quick Start with Docker Compose

```bash
# 1. Copy and configure environment
cp .env.example .env
# Edit .env with your production settings

# 2. Build container
docker-compose build

# 3. Start services
docker-compose up -d

# 4. Verify health
curl https://localhost/health/ready

# 5. Check logs
docker-compose logs -f gateway
```

### Manual Docker Deployment

```bash
# Build image
docker build -t aegis:latest .

# Run container
docker run -d \
  --name gateway \
  --restart unless-stopped \
  -p 8000:8000 \
  -v /data:/app/data \
  -v /logs:/app/logs \
  --env-file .env \
  aegis:latest

# Check health
docker exec gateway curl http://localhost:8000/health
```

### Production Database Setup

For production, use a managed PostgreSQL instance (AWS RDS, Google Cloud SQL, etc.):

```bash
# Update ASG_SQLITE_PATH to PostgreSQL connection string
ASG_DATABASE_URL=postgresql://user:password@host:5432/gateway_db
```

## Kubernetes Deployment

### Create Namespace

```bash
kubectl create namespace ai-safety
```

### Create Secrets

```bash
kubectl create secret generic gateway-secrets \
  --from-literal=fernet-key='<your-key>' \
  --from-literal=openai-api-key='<your-key>' \
  -n ai-safety
```

### Deploy with Helm

```bash
# Install with Helm
helm install gateway ./helm-chart \
  -n ai-safety \
  -f values-prod.yaml
```

### Manual Deployment

See [k8s-deployment.yaml](./k8s-deployment.yaml) for complete manifest.

## Security Hardening

### TLS/HTTPS

1. **Generate Certificates**
   ```bash
   # Using Let's Encrypt
   certbot certonly --standalone -d yourdomain.com
   
   # Copy to nginx
   cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ./ssl/cert.pem
   cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ./ssl/key.pem
   ```

2. **Configure NGINX** (see [nginx.conf](./nginx.conf))
   - TLS 1.2+ only
   - Strong cipher suites
   - HSTS headers
   - Security headers

### Authentication

Add authentication to dashboard and admin endpoints:

```nginx
location /dashboard {
    auth_request /auth;
    auth_request_set $auth_status $upstream_status;
    ...
}
```

Implement your auth service (OAuth2, Okta, etc.).

### Network Security

```bash
# Firewall rules (example with ufw)
sudo ufw default deny incoming
sudo ufw allow 22/tcp          # SSH
sudo ufw allow 80/tcp          # HTTP redirect
sudo ufw allow 443/tcp         # HTTPS
sudo ufw allow from 10.0.0.0/8 # Internal network
```

### Regular Security Updates

```bash
# Update Docker base image
docker pull python:3.11-slim

# Rebuild and redeploy
docker-compose build --no-cache
docker-compose up -d
```

## Monitoring & Observability

### Prometheus Metrics

Access Prometheus at http://localhost:9090

Key metrics to monitor:
- `gateway_requests_total` - Total API requests
- `gateway_actions_processed` - Actions processed
- `gateway_approvals_pending` - Pending approvals
- `gateway_policy_blocks` - Blocked actions
- `gateway_risk_score_histogram` - Risk score distribution

### Structured Logging

All logs are JSON-formatted with request IDs:

```bash
tail -f logs/gateway-*.log | jq .
```

### Alert Rules

Create alerts for:
- High error rates (> 5%)
- High policy block rate
- Pending approvals queue growing
- Database backup failures
- Disk space warnings

See [alerts.yml](./alerts.yml) for Prometheus alert rules.

### Log Aggregation

Forward logs to your aggregation system:

```bash
# Example: Ship to Datadog
docker run -d \
  --name datadog-agent \
  -e DD_API_KEY=<your-key> \
  -v /var/log:/host/var/log:ro \
  datadog/agent:latest
```

## Backup & Recovery

### Automated Backups

Configure in `.env`:

```bash
ASG_ENABLE_AUTO_BACKUP=true
ASG_BACKUP_INTERVAL_HOURS=6
ASG_BACKUP_RETENTION_DAYS=30
```

### Manual Backup

```bash
# Backup database
docker exec gateway sqlite3 /app/data/gateway.db ".backup '/app/data/backups/backup-$(date +%s).db'"

# Backup logs
tar czf logs-backup-$(date +%Y%m%d).tar.gz logs/
```

### Offsite Backup

```bash
# Example: AWS S3
aws s3 sync ./data/backups s3://my-bucket/backups/ --sse AES256

# Example: Google Cloud Storage
gsutil -m cp -r ./data/backups gs://my-bucket/backups/
```

### Recovery Testing

Monthly recovery drills:

```bash
# Test restore procedure
1. Restore database from backup
2. Verify audit logs integrity
3. Test snapshot rollback
4. Validate all data is accessible
```

## Monitoring Checklist

- [ ] Set up log aggregation (ELK, Splunk, etc.)
- [ ] Configure Prometheus monitoring
- [ ] Set up alerts for critical events
- [ ] Configure backup monitoring
- [ ] Set up synthetic monitoring/uptime checks
- [ ] Implement error tracking (Sentry, etc.)
- [ ] Configure log retention policies
- [ ] Set up automated log rotation

## Scaling Considerations

### Horizontal Scaling

```bash
# Multiple instances behind load balancer
docker-compose up -d --scale gateway=3
```

### Database Optimization

For high-volume deployments:

```bash
# Switch to PostgreSQL
# Configure connection pooling
# Add database indexes
# Set up read replicas
```

### Caching

Implement caching for:
- Policy rules
- Agent registry
- Risk scoring models
- Dashboard queries

## Troubleshooting

### Common Issues

**Issue**: "Service unavailable"
```bash
# Check container health
docker ps
docker logs gateway

# Verify database
docker exec gateway sqlite3 /app/data/gateway.db "SELECT 1;"
```

**Issue**: "High memory usage"
```bash
# Check for memory leaks
docker stats gateway

# Increase log rotation
# Clear old logs
find logs/ -mtime +30 -delete
```

**Issue**: "Slow responses"
```bash
# Check database performance
# Monitor network latency to LLM services
# Review request logs for patterns
```

### Emergency Procedures

**Database Corruption**:
```bash
# Restore from backup
docker-compose down
rm data/gateway.db
aws s3 cp s3://my-bucket/backups/latest.db data/gateway.db
docker-compose up -d
```

**Compromised Encryption Keys**:
```bash
# 1. Rotate keys immediately
# 2. Re-encrypt all backups
# 3. Alert all stakeholders
# 4. Review audit logs for suspicious activity
```

## Support & Documentation

- API Documentation: https://yourdomain.com/docs
- GitHub Issues: [report bugs]
- Email: support@yourdomain.com

## Version Information

- **Version**: 1.0.0
- **Python**: 3.11+
- **FastAPI**: 0.109+
- **Last Updated**: 2026-05-07
