# Rung - Operational Guide

## Quick Start

### Prerequisites
- AWS CLI configured with appropriate IAM role
- Docker (for container builds)
- Python 3.11+
- Terraform 1.5+ (for infrastructure)

### Local Development Setup

```bash
# Clone and setup
cd ~/projects/Rung
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Environment variables
cp .env.example .env
# Edit .env with your credentials (NEVER commit .env)

# Run database migrations
make migrate
```

### Running Tests

```bash
# All tests with coverage (recommended)
make test

# Quick tests (no coverage)
make test-quick

# Specific test suites
pytest tests/unit/ -v              # Unit tests
pytest tests/integration/ -v       # Integration tests
pytest tests/e2e/ -v               # End-to-end pipeline tests
pytest tests/security/ -v --strict # Security/isolation tests (CRITICAL)

# Coverage report
make test  # Generates htmlcov/index.html
```

### Infrastructure Deployment

```bash
# Validate Terraform syntax
make tf-validate

# Plan changes
make tf-plan

# Apply (creates AWS resources - requires confirmation)
make tf-apply

# View outputs (ECR URL, ECS cluster, etc.)
make tf-output
```

### Docker & ECS Deployment

```bash
# Build Docker image locally
make build

# Run container locally (requires .env file)
make run-local

# Build, push to ECR, and deploy to ECS
make deploy

# Check deployment status
make deployment-status

# View logs from ECS
make logs
```

## Development Workflow

### Branch Naming
- `feature/{description}` - New features
- `fix/{issue-description}` - Bug fixes
- `security/{issue}` - Security-related changes
- `docs/{description}` - Documentation updates

### Commit Messages
```
feat(agent): add Rung framework extraction logic
fix(encryption): correct KMS key reference in S3 upload
security(isolation): add context clearing before Beth call
docs: update ARCHITECTURE.md with couples merge flow
```

### Pre-Commit Checklist
- [ ] All tests pass
- [ ] No PHI in logs or comments
- [ ] Agent isolation maintained
- [ ] Encryption verified for new data flows
- [ ] `decisions.log` updated if architectural change

## Testing Pipelines

### Pre-Session Pipeline

```bash
# Unit tests
pytest tests/unit/test_pre_session_pipeline.py -v

# Integration test (requires AWS/mocks)
pytest tests/integration/test_pre_session.py -v

# End-to-end test
pytest tests/e2e/test_pre_session.py -v
```

### Post-Session Pipeline

```bash
# Unit tests
pytest tests/unit/test_post_session_pipeline.py -v

# Integration test
pytest tests/integration/test_post_session.py -v

# End-to-end test
pytest tests/e2e/test_post_session.py -v
```

### Couples Merge Pipeline

```bash
# CRITICAL: Isolation tests must pass
pytest tests/security/test_couples_isolation.py -v --strict

# Unit tests
pytest tests/unit/test_couples_merge.py -v

# End-to-end test
pytest tests/e2e/test_couples_merge.py -v
```

### Services

```bash
# Encryption service
pytest tests/unit/test_encryption.py -v

# Audit service
pytest tests/unit/test_audit.py -v

# Progress analytics
pytest tests/unit/test_progress_analytics.py -v
```

## Monitoring

### CloudWatch Dashboards
- `Rung-Pipelines`: Pipeline execution metrics (duration, failures)
- `Rung-API`: API latency and errors
- `Rung-Security`: Authentication failures, PHI access logs

### Alerts
- Failed authentication (3+ in 5 minutes)
- PHI access outside business hours
- Workflow failure rate > 5%
- Couples merge without proper isolation

### Log Queries

```bash
# Failed auth attempts
aws logs filter-log-events \
  --log-group-name /rung/auth \
  --filter-pattern "{ $.status = 401 }"

# PHI access events
aws logs filter-log-events \
  --log-group-name /rung/audit \
  --filter-pattern "{ $.event_type = PHI_ACCESS }"
```

## Troubleshooting

### Common Issues

**Pipeline fails silently**
```bash
# Check ECS logs
make logs

# Check specific pipeline status
curl -H "Authorization: Bearer $TOKEN" \
  https://api.rung.health/v1/sessions/{id}/pre-session/status
```

**Bedrock timeout**
- Check VPC endpoint configuration
- Verify IAM role has bedrock:InvokeModel permission
- Review token budget (may exceed limit)

**Pipeline timeout**
- Check ECS task timeout (default: 10 minutes)
- Review CloudWatch logs for bottleneck stage
- Consider increasing task timeout or optimizing stage

**Encryption/decryption failure**
- Verify KMS key permissions
- Check key alias references
- Confirm encryption context matches

## Security Procedures

### Incident Response
1. Immediately revoke compromised credentials
2. Document timeline of events
3. Notify compliance officer (if PHI involved)
4. Review audit logs for scope
5. Implement remediation
6. Post-incident review

### Key Rotation
```bash
# Rotate KMS key (automatic via AWS)
# Manual rotation for application secrets:
aws secretsmanager rotate-secret --secret-id rung/prod/api-keys
```

### Access Review
- Monthly: Review IAM roles and permissions
- Quarterly: Audit Cognito user list
- Annually: Full security assessment
