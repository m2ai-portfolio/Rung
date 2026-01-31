# Rung - Operational Guide

## Quick Start

### Prerequisites
- AWS CLI configured with appropriate IAM role
- Docker (for local n8n testing)
- Python 3.11+
- Node.js 18+ (for Perceptor MCP)
- Terraform 1.5+

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
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# Integration tests (requires AWS credentials)
pytest tests/integration/ -v

# Security/isolation tests (CRITICAL - must pass)
pytest tests/security/ -v --strict

# Coverage report
pytest tests/ --cov=src --cov-report=html
```

### Infrastructure Deployment

```bash
# Initialize Terraform
cd terraform/
terraform init

# Plan (review changes)
terraform plan -out=tfplan

# Apply (requires approval)
terraform apply tfplan
```

### n8n Workflows

```bash
# Export workflow for backup
curl -X GET "http://n8n-host/api/v1/workflows/{id}" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" > n8n/workflow-{name}.json

# Import workflow
curl -X POST "http://n8n-host/api/v1/workflows" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -d @n8n/workflow-{name}.json
```

## Development Workflow

### Branch Naming
- `feature/phase-{N}-{description}` - New phase work
- `fix/{issue-description}` - Bug fixes
- `security/{issue}` - Security-related changes

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

## Phase-Specific Commands

### Phase 1: Foundation

```bash
# Deploy VPC and RDS
cd terraform/phase1
terraform apply

# Verify database connection
psql -h $RDS_ENDPOINT -U rung_admin -d rung

# Test encryption
python scripts/test_encryption.py
```

### Phase 2: Pre-Session Pipeline

```bash
# Test voice memo upload
python scripts/test_voice_upload.py --file test_memo.m4a

# Test Rung agent
python scripts/test_rung_agent.py --input "sample transcript"

# Test Perplexity anonymization
python scripts/test_perplexity.py --query "attachment anxiety frameworks"

# Full pre-session E2E
pytest tests/e2e/test_pre_session.py -v
```

### Phase 3: Post-Session Pipeline

```bash
# Test notes processing
python scripts/test_notes_processing.py --session-id 123

# Test Perceptor integration
python scripts/test_perceptor.py --action save

# Full post-session E2E
pytest tests/e2e/test_post_session.py -v
```

### Phase 4: Couples Merge

```bash
# Test isolation layer (CRITICAL)
pytest tests/security/test_couples_isolation.py -v --strict

# Test framework extraction
python scripts/test_framework_extraction.py

# Full couples E2E
pytest tests/e2e/test_couples_merge.py -v
```

## Monitoring

### CloudWatch Dashboards
- `Rung-Workflows`: n8n workflow execution metrics
- `Rung-API`: API Gateway latency and errors
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

**n8n workflow fails silently**
```bash
# Check n8n logs
docker logs rung-n8n --tail 100

# Check specific execution
curl "http://n8n-host/api/v1/executions/{id}" \
  -H "X-N8N-API-KEY: $N8N_API_KEY"
```

**Bedrock timeout**
- Check VPC endpoint configuration
- Verify IAM role has bedrock:InvokeModel permission
- Review token budget (may exceed limit)

**Perceptor not saving**
- Verify Perceptor MCP is running: `curl http://localhost:3100/health`
- Check tag format matches expected schema
- Review Perceptor logs for errors

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
