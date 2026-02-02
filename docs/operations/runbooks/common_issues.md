# Common Issues Runbook

## Document Control

| Version | Date | Author | Status |
|---------|------|--------|--------|
| 1.0 | 2026-02-02 | Operations Team | Production |

---

## 1. API Performance Issues

### 1.1 High Latency (P95 > 5s)

**Symptoms:**
- Slow API responses
- User complaints about performance
- CloudWatch latency alarms triggered

**Investigation:**

```bash
# 1. Check API Gateway metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Latency \
  --dimensions Name=ApiName,Value=rung-api \
  --start-time $(date -d '1 hour ago' -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics p95

# 2. Check Lambda duration
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=rung-api-prod \
  --start-time $(date -d '1 hour ago' -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics p95

# 3. Check RDS performance
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name ReadLatency \
  --dimensions Name=DBInstanceIdentifier,Value=rung-prod \
  --start-time $(date -d '1 hour ago' -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Average
```

**Resolution:**

| Cause | Resolution |
|-------|------------|
| Lambda cold starts | Enable provisioned concurrency |
| Database queries slow | Check query patterns, add indexes |
| VPC networking | Verify VPC endpoints configured |
| Bedrock latency | Check Bedrock service health |

```bash
# Enable provisioned concurrency
aws lambda put-provisioned-concurrency-config \
  --function-name rung-api-prod \
  --qualifier prod \
  --provisioned-concurrent-executions 10

# Check for missing indexes
psql -h $DB_HOST -U rung_admin -d rung <<EOF
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0;
EOF
```

### 1.2 High Error Rate (5xx > 5%)

**Symptoms:**
- Elevated 5xx errors in CloudWatch
- API error rate alarm triggered
- User-reported failures

**Investigation:**

```bash
# 1. Check recent Lambda errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/rung-api-prod \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "ERROR" \
  --limit 20

# 2. Check API Gateway errors
aws logs filter-log-events \
  --log-group-name /aws/apigateway/rung-prod \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "{ $.status >= 500 }" \
  --limit 20

# 3. Check RDS connections
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBInstanceIdentifier,Value=rung-prod \
  --start-time $(date -d '1 hour ago' -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 \
  --statistics Maximum
```

**Resolution:**

| Cause | Resolution |
|-------|------------|
| Database connection exhaustion | Increase max connections, check connection pooling |
| Memory exhaustion | Increase Lambda memory |
| Timeout | Increase timeout, optimize code |
| Dependency failure | Check external service health |

---

## 2. Authentication Issues

### 2.1 Users Cannot Log In

**Symptoms:**
- Login failures reported
- High failed authentication count
- Cognito errors in logs

**Investigation:**

```bash
# 1. Check Cognito user pool status
aws cognito-idp describe-user-pool \
  --user-pool-id $USER_POOL_ID \
  --query 'UserPool.Status'

# 2. Check for account lockouts
aws cognito-idp admin-get-user \
  --user-pool-id $USER_POOL_ID \
  --username $USERNAME \
  --query 'UserStatus'

# 3. Check Cognito CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Cognito \
  --metric-name SignInSuccesses \
  --dimensions Name=UserPoolId,Value=$USER_POOL_ID \
  --start-time $(date -d '1 hour ago' -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Sum
```

**Resolution:**

```bash
# Unlock user account
aws cognito-idp admin-enable-user \
  --user-pool-id $USER_POOL_ID \
  --username $USERNAME

# Reset user password (sends reset email)
aws cognito-idp admin-reset-user-password \
  --user-pool-id $USER_POOL_ID \
  --username $USERNAME

# Force global sign-out (invalidate all sessions)
aws cognito-idp admin-user-global-sign-out \
  --user-pool-id $USER_POOL_ID \
  --username $USERNAME
```

### 2.2 MFA Issues

**Symptoms:**
- Users reporting MFA not working
- TOTP codes rejected

**Resolution:**

```bash
# 1. Check user MFA status
aws cognito-idp admin-get-user \
  --user-pool-id $USER_POOL_ID \
  --username $USERNAME \
  --query 'MFAOptions'

# 2. Reset MFA (user will need to re-enroll)
aws cognito-idp admin-set-user-mfa-preference \
  --user-pool-id $USER_POOL_ID \
  --username $USERNAME \
  --software-token-mfa-settings Enabled=false,PreferredMfa=false

# 3. User re-enrolls via app
# Provide instructions for MFA re-setup
```

---

## 3. Workflow Issues (n8n)

### 3.1 Workflow Not Triggering

**Symptoms:**
- Pre-session or post-session workflow not running
- Webhook not receiving events

**Investigation:**

```bash
# 1. Check n8n health
curl -I https://n8n.internal.rung.health/healthz

# 2. Check n8n logs
aws logs filter-log-events \
  --log-group-name /rung/n8n/prod \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "ERROR" \
  --limit 20

# 3. Verify webhook URL is correct
curl -X POST https://n8n.internal.rung.health/webhook/pre-session \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

**Resolution:**

| Cause | Resolution |
|-------|------------|
| n8n container down | Restart ECS service |
| Webhook URL changed | Update API configuration |
| Workflow disabled | Enable workflow in n8n UI |
| Memory exhaustion | Increase container memory |

```bash
# Restart n8n ECS service
aws ecs update-service \
  --cluster rung-prod \
  --service n8n \
  --force-new-deployment
```

### 3.2 Bedrock Calls Failing

**Symptoms:**
- Agent analysis not returning results
- Timeout errors in workflow

**Investigation:**

```bash
# 1. Check Bedrock service health
aws bedrock list-foundation-models --region us-east-1

# 2. Check for throttling
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name ThrottledCount \
  --start-time $(date -d '1 hour ago' -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Sum

# 3. Check VPC endpoint
aws ec2 describe-vpc-endpoints \
  --filters Name=service-name,Values=com.amazonaws.us-east-1.bedrock-runtime \
  --query 'VpcEndpoints[0].State'
```

**Resolution:**

| Cause | Resolution |
|-------|------------|
| Throttling | Request quota increase |
| VPC endpoint issue | Verify endpoint configuration |
| Model unavailable | Switch to alternate model |

---

## 4. Database Issues

### 4.1 Connection Exhaustion

**Symptoms:**
- "too many connections" errors
- Intermittent database failures

**Investigation:**

```bash
# 1. Check current connections
psql -h $DB_HOST -U rung_admin -d rung -c "
SELECT count(*) FROM pg_stat_activity;
"

# 2. Check connections by state
psql -h $DB_HOST -U rung_admin -d rung -c "
SELECT state, count(*)
FROM pg_stat_activity
GROUP BY state;
"

# 3. Find long-running queries
psql -h $DB_HOST -U rung_admin -d rung -c "
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes'
AND state = 'active';
"
```

**Resolution:**

```bash
# 1. Kill idle connections
psql -h $DB_HOST -U rung_admin -d rung -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle'
AND query_start < now() - interval '30 minutes';
"

# 2. Increase max connections (requires restart)
aws rds modify-db-parameter-group \
  --db-parameter-group-name rung-prod \
  --parameters "ParameterName=max_connections,ParameterValue=200,ApplyMethod=pending-reboot"

# 3. Reboot RDS to apply
aws rds reboot-db-instance \
  --db-instance-identifier rung-prod
```

### 4.2 Slow Queries

**Symptoms:**
- Database latency spikes
- Specific operations timing out

**Investigation:**

```bash
# Enable slow query logging (if not already)
# Check pg_stat_statements for slow queries
psql -h $DB_HOST -U rung_admin -d rung -c "
SELECT query, calls, total_time/calls as avg_time, rows
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;
"

# Check for missing indexes
psql -h $DB_HOST -U rung_admin -d rung -c "
SELECT schemaname, relname, seq_scan, seq_tup_read,
       idx_scan, idx_tup_fetch
FROM pg_stat_user_tables
WHERE seq_scan > idx_scan
ORDER BY seq_tup_read DESC
LIMIT 10;
"
```

**Resolution:**

```sql
-- Add missing indexes
CREATE INDEX CONCURRENTLY idx_sessions_client_id
ON sessions(client_id);

CREATE INDEX CONCURRENTLY idx_clinical_briefs_session_id
ON clinical_briefs(session_id);

CREATE INDEX CONCURRENTLY idx_audit_logs_created_at
ON audit_logs(created_at);

-- Analyze tables to update statistics
ANALYZE clients;
ANALYZE sessions;
ANALYZE clinical_briefs;
```

---

## 5. Storage Issues

### 5.1 S3 Access Denied

**Symptoms:**
- Voice memo uploads failing
- Transcript retrieval failing

**Investigation:**

```bash
# 1. Check bucket policy
aws s3api get-bucket-policy --bucket rung-voice-memos-prod

# 2. Check IAM role permissions
aws iam get-role-policy \
  --role-name rung-lambda-role \
  --policy-name s3-access

# 3. Check VPC endpoint
aws ec2 describe-vpc-endpoints \
  --filters Name=service-name,Values=com.amazonaws.us-east-1.s3 \
  --query 'VpcEndpoints[0].State'
```

**Resolution:**

```bash
# Update bucket policy if needed
aws s3api put-bucket-policy \
  --bucket rung-voice-memos-prod \
  --policy file://bucket-policy.json

# Check Lambda execution role
aws lambda get-function \
  --function-name rung-api-prod \
  --query 'Configuration.Role'
```

---

## 6. Couples Merge Issues

### 6.1 Isolation Layer Failures

**Symptoms:**
- Merge operations failing
- IsolationViolation errors in logs

**Investigation:**

```bash
# 1. Check recent merge failures
aws logs filter-log-events \
  --log-group-name /rung/audit/prod \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "{ $.event_type = \"couples_merge\" && $.action = \"merge_failed\" }" \
  --limit 10

# 2. Check for isolation violations
aws logs filter-log-events \
  --log-group-name /rung/security/prod \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "IsolationViolation" \
  --limit 10
```

**Resolution:**

| Cause | Resolution |
|-------|------------|
| Non-whitelisted term | Review and update whitelist |
| PHI in framework name | Clean data, review extraction |
| Schema mismatch | Verify Pydantic schemas |

### 6.2 Merge Authorization Failures

**Symptoms:**
- 403 errors on merge operations
- Authorization failed in audit logs

**Investigation:**

```bash
# Check couple link status
psql -h $DB_HOST -U rung_admin -d rung -c "
SELECT id, therapist_id, status
FROM couple_links
WHERE id = '$LINK_ID';
"

# Check therapist association
psql -h $DB_HOST -U rung_admin -d rung -c "
SELECT c.id, c.therapist_id
FROM clients c
JOIN couple_links cl ON c.id IN (cl.partner_a_id, cl.partner_b_id)
WHERE cl.id = '$LINK_ID';
"
```

**Resolution:**

- Verify therapist owns both clients
- Check couple link status is ACTIVE
- Verify requesting user is the assigned therapist

---

## 7. Monitoring and Alerting

### 7.1 False Positive Alerts

**Symptoms:**
- Frequent alerts that are not actionable
- Alert fatigue

**Resolution:**

```bash
# Adjust alarm thresholds
aws cloudwatch put-metric-alarm \
  --alarm-name rung-failed-auth-spike-prod \
  --threshold 20 \
  --evaluation-periods 2 \
  --datapoints-to-alarm 2

# Add ok-actions to auto-resolve
aws cloudwatch put-metric-alarm \
  --alarm-name rung-api-error-rate-prod \
  --ok-actions $SNS_TOPIC_ARN
```

### 7.2 Missing Alerts

**Symptoms:**
- Issues discovered without alerts
- Monitoring gaps

**Resolution:**

- Review CloudWatch alarm coverage
- Add missing metric filters
- Test alarm triggers with synthetic data

---

## 8. Quick Reference

### 8.1 Common Commands

```bash
# Check all service health
./scripts/health_check.sh

# View recent errors
./scripts/view_errors.sh --last-hour

# Restart Lambda functions
./scripts/restart_lambdas.sh prod

# Check database status
./scripts/db_status.sh

# View active alarms
aws cloudwatch describe-alarms \
  --state-value ALARM \
  --alarm-name-prefix rung
```

### 8.2 Escalation Matrix

| Issue Type | L1 Response | L2 Escalation | L3 Escalation |
|------------|-------------|---------------|---------------|
| API Errors | 5 min | 15 min if unresolved | 30 min |
| Auth Issues | 5 min | 15 min if unresolved | 30 min |
| Data Issues | Immediate | Immediate | Immediate |
| Performance | 15 min | 30 min if unresolved | 1 hour |

---

## Appendix: Log Locations

| Component | Log Group |
|-----------|-----------|
| API Gateway | /aws/apigateway/rung-prod |
| Lambda | /aws/lambda/rung-* |
| Audit | /rung/audit/prod |
| Security | /rung/security/prod |
| n8n | /rung/n8n/prod |
