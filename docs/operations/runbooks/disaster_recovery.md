# Disaster Recovery Runbook

## Document Control

| Version | Date | Author | Status |
|---------|------|--------|--------|
| 1.0 | 2026-02-02 | Operations Team | Production |

## Recovery Objectives

| Metric | Target | Description |
|--------|--------|-------------|
| RTO | < 4 hours | Recovery Time Objective - maximum downtime |
| RPO | < 1 hour | Recovery Point Objective - maximum data loss |

---

## 1. Disaster Scenarios

### 1.1 Scenario Classification

| Scenario | Severity | RTO | RPO | Runbook Section |
|----------|----------|-----|-----|-----------------|
| Single AZ failure | Medium | 15 min | 0 | Section 2 |
| RDS failure | High | 30 min | 5 min | Section 3 |
| Region failure | Critical | 4 hours | 1 hour | Section 4 |
| Data corruption | Critical | 2 hours | Varies | Section 5 |
| Security breach | Critical | Immediate | N/A | Section 6 |

---

## 2. Single AZ Failure Recovery

**Scenario:** One Availability Zone becomes unavailable.

**Impact:** Degraded performance, some requests may fail.

**Automatic Recovery:** Multi-AZ deployment handles this automatically.

### 2.1 Verification Steps

```bash
# 1. Check current AZ status
aws ec2 describe-availability-zones --region us-east-1

# 2. Verify RDS Multi-AZ status
aws rds describe-db-instances \
  --db-instance-identifier rung-prod \
  --query 'DBInstances[0].MultiAZ'

# 3. Check Lambda function availability
aws lambda get-function --function-name rung-api-prod \
  --query 'Configuration.VpcConfig.SubnetIds'

# 4. Verify ALB health
aws elbv2 describe-target-health \
  --target-group-arn $TARGET_GROUP_ARN
```

### 2.2 Manual Intervention (if needed)

```bash
# If automatic failover hasn't occurred after 10 minutes:

# 1. Force RDS failover (if stuck)
aws rds reboot-db-instance \
  --db-instance-identifier rung-prod \
  --force-failover

# 2. Update Route 53 health checks
aws route53 update-health-check \
  --health-check-id $HEALTH_CHECK_ID \
  --regions us-east-1a us-east-1b

# 3. Notify operations team
./scripts/notify_ops.sh "AZ Failure Recovery Initiated"
```

### 2.3 Verification Checklist

- [ ] RDS primary is in healthy AZ
- [ ] All Lambda functions responding
- [ ] ALB health checks passing
- [ ] API endpoints responding
- [ ] Audit logging functional

---

## 3. RDS Failure Recovery

**Scenario:** Primary RDS instance fails or becomes unresponsive.

**Impact:** All database operations fail.

### 3.1 Automatic Failover (Multi-AZ)

RDS Multi-AZ automatically fails over to standby. Monitor:

```bash
# Watch for failover event
aws rds describe-events \
  --source-identifier rung-prod \
  --source-type db-instance \
  --duration 60

# Expected event: "Multi-AZ instance failover started"
# Followed by: "Multi-AZ instance failover completed"
```

### 3.2 Manual Recovery (if automatic fails)

```bash
# 1. Check instance status
aws rds describe-db-instances \
  --db-instance-identifier rung-prod \
  --query 'DBInstances[0].DBInstanceStatus'

# 2. If stuck, attempt reboot with failover
aws rds reboot-db-instance \
  --db-instance-identifier rung-prod \
  --force-failover

# 3. If reboot fails, restore from snapshot
LATEST_SNAPSHOT=$(aws rds describe-db-snapshots \
  --db-instance-identifier rung-prod \
  --query 'DBSnapshots | sort_by(@, &SnapshotCreateTime) | [-1].DBSnapshotIdentifier' \
  --output text)

aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier rung-prod-recovery \
  --db-snapshot-identifier $LATEST_SNAPSHOT \
  --db-subnet-group-name rung-private-subnets \
  --vpc-security-group-ids $RDS_SG_ID \
  --multi-az

# 4. Update application configuration
aws ssm put-parameter \
  --name "/rung/prod/database/endpoint" \
  --value "rung-prod-recovery.xxxxx.us-east-1.rds.amazonaws.com" \
  --type SecureString \
  --overwrite

# 5. Restart Lambda functions to pick up new endpoint
aws lambda update-function-configuration \
  --function-name rung-api-prod \
  --environment "Variables={DB_REFRESH=$(date +%s)}"
```

### 3.3 Point-in-Time Recovery

If data corruption is detected:

```bash
# 1. Identify corruption time
# Review audit logs for last known good state

# 2. Restore to point in time
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier rung-prod \
  --target-db-instance-identifier rung-prod-pitr \
  --restore-time "2026-02-02T10:00:00Z" \
  --db-subnet-group-name rung-private-subnets \
  --vpc-security-group-ids $RDS_SG_ID \
  --multi-az

# 3. Validate data integrity
psql -h rung-prod-pitr.xxxxx.us-east-1.rds.amazonaws.com \
  -U rung_admin -d rung \
  -c "SELECT COUNT(*) FROM clients; SELECT COUNT(*) FROM sessions;"

# 4. Swap endpoints after validation
```

### 3.4 Verification Checklist

- [ ] RDS instance status is "available"
- [ ] Database connections successful
- [ ] All tables accessible
- [ ] PHI data intact and encrypted
- [ ] Audit logging resumed

---

## 4. Region Failure Recovery

**Scenario:** Entire AWS region (us-east-1) becomes unavailable.

**Impact:** Complete service outage.

**RTO:** < 4 hours | **RPO:** < 1 hour

### 4.1 Pre-Requisites

Ensure these are in place:
- [ ] Cross-region S3 replication enabled
- [ ] RDS automated backups copied to us-west-2
- [ ] Terraform state in S3 with cross-region replication
- [ ] DR region (us-west-2) infrastructure templated

### 4.2 Recovery Procedure

```bash
# Phase 1: Assess and Declare (15 min)
# =====================================

# 1. Confirm region failure (not just AZ)
aws ec2 describe-regions --region us-west-2

# 2. Declare disaster - notify stakeholders
./scripts/declare_disaster.sh "Region Failure - us-east-1"

# 3. Activate DR team
# PagerDuty escalation automatic

# Phase 2: Infrastructure (1 hour)
# =================================

# 1. Switch to DR region
export AWS_REGION=us-west-2
cd terraform/environments/dr

# 2. Deploy DR infrastructure
terraform init
terraform apply -auto-approve

# Phase 3: Data Recovery (1.5 hours)
# ===================================

# 1. Identify latest RDS snapshot in DR region
LATEST_SNAPSHOT=$(aws rds describe-db-snapshots \
  --region us-west-2 \
  --query 'DBSnapshots | sort_by(@, &SnapshotCreateTime) | [-1].DBSnapshotIdentifier' \
  --output text)

# 2. Restore RDS from cross-region snapshot
aws rds restore-db-instance-from-db-snapshot \
  --region us-west-2 \
  --db-instance-identifier rung-dr \
  --db-snapshot-identifier $LATEST_SNAPSHOT \
  --db-subnet-group-name rung-private-subnets-dr \
  --vpc-security-group-ids $DR_RDS_SG_ID \
  --multi-az

# 3. Wait for RDS to become available (30-45 min)
aws rds wait db-instance-available \
  --db-instance-identifier rung-dr \
  --region us-west-2

# 4. Verify S3 data replicated
aws s3 ls s3://rung-voice-memos-dr-prod/ --region us-west-2
aws s3 ls s3://rung-transcripts-dr-prod/ --region us-west-2

# Phase 4: Application Deployment (30 min)
# =========================================

# 1. Deploy Lambda functions to DR region
cd ../../..
./scripts/deploy_lambdas.sh us-west-2 prod

# 2. Update Cognito (if using regional pool)
# Note: Consider using global Cognito setup

# 3. Update API Gateway
./scripts/deploy_api.sh us-west-2 prod

# Phase 5: DNS Cutover (15 min)
# =============================

# 1. Update Route 53 to point to DR region
aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "api.rung.health",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "'$DR_ALB_ZONE_ID'",
          "DNSName": "'$DR_ALB_DNS'",
          "EvaluateTargetHealth": true
        }
      }
    }]
  }'

# 2. Verify DNS propagation
dig api.rung.health

# Phase 6: Validation (30 min)
# ============================

# 1. Run smoke tests
./scripts/smoke_tests.sh us-west-2

# 2. Verify PHI accessible
./scripts/verify_phi_access.sh

# 3. Check audit logging
./scripts/verify_audit_logs.sh

# 4. Notify stakeholders of recovery
./scripts/notify_recovery_complete.sh
```

### 4.3 Post-Recovery

- [ ] Document timeline and actions taken
- [ ] Calculate actual RTO/RPO achieved
- [ ] Schedule post-incident review
- [ ] Plan for failback when primary region recovers

---

## 5. Data Corruption Recovery

**Scenario:** Data corruption detected in database.

### 5.1 Detection

Corruption may be detected via:
- Application errors (constraint violations)
- Audit log anomalies
- User reports
- Integrity check failures

### 5.2 Recovery Procedure

```bash
# 1. STOP all write operations immediately
# Update API Gateway to return 503 for write operations

# 2. Identify corruption scope
psql -h $DB_HOST -U rung_admin -d rung <<EOF
-- Check for orphaned records
SELECT COUNT(*) FROM sessions WHERE client_id NOT IN (SELECT id FROM clients);
SELECT COUNT(*) FROM clinical_briefs WHERE session_id NOT IN (SELECT id FROM sessions);

-- Check for invalid data
SELECT COUNT(*) FROM clients WHERE consent_status NOT IN ('pending', 'active', 'revoked');
EOF

# 3. Identify last known good state from audit logs
aws logs filter-log-events \
  --log-group-name /rung/audit/prod \
  --start-time $(date -d '24 hours ago' +%s)000 \
  --filter-pattern "{ $.action = \"*\" }" \
  --query 'events[*].message' | jq -r '.[]' | head -100

# 4. Perform point-in-time recovery (see Section 3.3)

# 5. Validate recovered data
./scripts/validate_data_integrity.sh

# 6. Resume operations
# Re-enable write operations in API Gateway
```

---

## 6. Security Breach Recovery

**Scenario:** Security breach detected (unauthorized access).

**Reference:** See `docs/security/incident_response.md` for full procedures.

### 6.1 Immediate Actions

```bash
# 1. Isolate affected resources
# Modify security groups to block all ingress
aws ec2 modify-security-group-rules \
  --group-id $AFFECTED_SG_ID \
  --security-group-rules '[{"SecurityGroupRuleId":"'$RULE_ID'","SecurityGroupRule":{"IpProtocol":"-1","FromPort":-1,"ToPort":-1,"CidrIpv4":"0.0.0.0/32"}}]'

# 2. Revoke all active sessions
# Force Cognito token invalidation
aws cognito-idp admin-user-global-sign-out \
  --user-pool-id $USER_POOL_ID \
  --username $AFFECTED_USER

# 3. Rotate all secrets
aws secretsmanager rotate-secret \
  --secret-id rung-db-credentials-prod

aws secretsmanager rotate-secret \
  --secret-id rung-api-keys-prod

# 4. Capture forensic evidence
./scripts/capture_forensics.sh

# 5. Notify incident response team
./scripts/notify_security_incident.sh
```

---

## 7. Recovery Verification

### 7.1 Standard Verification Checklist

After any recovery, verify:

- [ ] **API Health**
  ```bash
  curl -I https://api.rung.health/health
  # Expected: HTTP 200
  ```

- [ ] **Database Connectivity**
  ```bash
  psql -h $DB_HOST -U rung_admin -d rung -c "SELECT 1"
  ```

- [ ] **PHI Access**
  ```bash
  # Test decryption works
  ./scripts/test_phi_access.sh
  ```

- [ ] **Audit Logging**
  ```bash
  aws logs describe-log-streams \
    --log-group-name /rung/audit/prod \
    --order-by LastEventTime \
    --descending \
    --limit 1
  ```

- [ ] **Authentication**
  ```bash
  # Test Cognito authentication
  ./scripts/test_auth.sh
  ```

- [ ] **n8n Workflows**
  ```bash
  curl -I https://n8n.internal.rung.health/healthz
  ```

### 7.2 Smoke Test Suite

```bash
# Run comprehensive smoke tests
./scripts/smoke_tests.sh

# Expected output:
# ✓ API Gateway responding
# ✓ Lambda functions healthy
# ✓ RDS connections successful
# ✓ S3 access working
# ✓ Cognito authentication functional
# ✓ Audit logging active
# ✓ Encryption/decryption working
```

---

## 8. Communication Templates

### 8.1 Initial Notification

```
SUBJECT: [RUNG] Service Disruption - Recovery in Progress

Status: INVESTIGATING/RECOVERING
Severity: [P1/P2/P3]
Impact: [Description of user impact]

We are aware of service disruption affecting [scope].
Our team is actively working on recovery.

Estimated Time to Recovery: [X hours]

Next Update: [Time]

Updates will be posted to: [Status page URL]
```

### 8.2 Recovery Complete

```
SUBJECT: [RUNG] Service Restored

Status: RESOLVED
Duration: [X hours Y minutes]

The service has been fully restored.

Root Cause: [Brief description]

Actions Taken:
- [Action 1]
- [Action 2]

Post-Incident Review: Scheduled for [Date/Time]

If you experience any issues, please contact support@rung.health
```

---

## 9. Contacts

### 9.1 Escalation Path

| Level | Contact | Response Time |
|-------|---------|---------------|
| L1 | On-Call Engineer | 5 min |
| L2 | Engineering Lead | 15 min |
| L3 | CTO | 30 min |
| L4 | CEO | 1 hour |

### 9.2 External Contacts

| Service | Contact | Purpose |
|---------|---------|---------|
| AWS Support | Enterprise Support Case | Infrastructure issues |
| PagerDuty | Auto-escalation | Alerting |

---

## Appendix A: Recovery Scripts

All recovery scripts are located in:
```
scripts/
├── disaster_recovery/
│   ├── declare_disaster.sh
│   ├── deploy_dr_infra.sh
│   ├── restore_rds.sh
│   ├── cutover_dns.sh
│   ├── smoke_tests.sh
│   └── notify_*.sh
```

## Appendix B: Testing Schedule

| Test | Frequency | Last Test | Next Test |
|------|-----------|-----------|-----------|
| RDS Failover | Quarterly | - | - |
| Backup Restore | Monthly | - | - |
| Full DR Drill | Annual | - | - |
| Runbook Review | Quarterly | - | - |
