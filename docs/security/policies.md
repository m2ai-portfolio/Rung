# Rung Security Policies

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-02 | Security Team | Initial release |

## 1. Purpose and Scope

This document defines the security policies for the Rung Psychology Agent Orchestration System. These policies ensure HIPAA compliance and protect Protected Health Information (PHI) processed by the system.

### 1.1 Scope

These policies apply to:
- All system components (APIs, agents, workflows, databases)
- All users (therapists, administrators, support staff)
- All environments (development, staging, production)
- All third-party integrations

### 1.2 Definitions

| Term | Definition |
|------|------------|
| PHI | Protected Health Information as defined by HIPAA |
| ePHI | Electronic Protected Health Information |
| BAA | Business Associate Agreement |
| MFA | Multi-Factor Authentication |

---

## 2. Access Control Policies

### 2.1 Authentication Requirements

**Policy AC-001: Multi-Factor Authentication**
- All user accounts MUST use MFA (TOTP-based)
- No exceptions for any role
- Recovery codes must be stored securely offline
- MFA tokens expire after 30 seconds

**Policy AC-002: Password Requirements**
- Minimum 12 characters
- Mixed case letters required
- Numbers required
- Special characters required
- No password reuse (last 24 passwords)
- Maximum age: 90 days
- Lockout after 5 failed attempts (15-minute duration)

**Policy AC-003: Session Management**
- Access tokens expire after 1 hour
- Refresh tokens expire after 24 hours
- Idle timeout: 15 minutes
- Concurrent session limit: 3 per user

### 2.2 Authorization Requirements

**Policy AC-004: Role-Based Access Control**

| Role | Permissions |
|------|-------------|
| Therapist | Read/write own clients, trigger workflows, view analyses |
| Client | Read own guides, submit voice memos |
| Admin | User management, system configuration, audit log access |
| Support | Read-only access to non-PHI system data |

**Policy AC-005: Least Privilege**
- Users receive minimum permissions required for their role
- Elevated permissions require approval and time-limited
- Service accounts have specific, documented permissions

**Policy AC-006: Separation of Duties**
- No single user can access both individual partner analyses in couples therapy
- Isolation layer must be invoked for any cross-client data access
- Admin actions require audit trail

### 2.3 Client Data Isolation

**Policy AC-007: Context Isolation**
- Rung agent context is NEVER shared with Beth agent
- Individual client data is NEVER shared between clients
- Couples merge uses ONLY framework-level abstractions
- Isolation layer enforces whitelist-only data extraction

**Policy AC-008: Therapist-Client Binding**
- Clients can only be accessed by their assigned therapist
- Couple links require same therapist for both partners
- Therapist reassignment requires explicit authorization

---

## 3. Data Protection Policies

### 3.1 Encryption Requirements

**Policy DP-001: Encryption at Rest**
- All databases: AES-256 encryption via AWS KMS
- All S3 buckets: AES-256 with customer-managed keys
- All backups: Encrypted with separate key
- Field-level encryption for sensitive PHI fields

**Policy DP-002: Encryption in Transit**
- TLS 1.3 required for all connections
- TLS 1.2 minimum (TLS 1.0/1.1 disabled)
- Certificate pinning for mobile applications
- Internal VPC traffic encrypted

**Policy DP-003: Key Management**
- KMS key hierarchy:
  - `rung-master-key`: Root CMK, annual rotation
  - `rung-rds-key`: Database encryption
  - `rung-s3-key`: Storage encryption
  - `rung-field-key`: Field-level encryption
- Key rotation: Annual for CMK, automatic for data keys
- Key access logged and audited

### 3.2 Data Classification

**Policy DP-004: Data Classification Levels**

| Level | Description | Examples | Handling |
|-------|-------------|----------|----------|
| PHI-Critical | Direct identifiers + health data | Session transcripts, clinical notes | Field-level encryption, strict access |
| PHI-Sensitive | Health information | Framework analyses, risk flags | Encrypted, role-based access |
| PHI-Derived | Abstracted health data | Theme categories, pattern names | Encrypted, isolation layer output |
| Internal | System operational data | Logs (sanitized), metrics | Standard encryption |
| Public | Non-sensitive | Documentation, marketing | No special handling |

### 3.3 Data Retention and Disposal

**Policy DP-005: Retention Periods**

| Data Type | Retention | Justification |
|-----------|-----------|---------------|
| Clinical records | 7 years post-termination | State law requirements |
| Audit logs | 7 years | HIPAA requirement |
| Session recordings | 90 days | Then archive to Glacier |
| Backups | 30 days | Disaster recovery |
| Deleted data | Immediate logical, 30 days physical | Secure deletion |

**Policy DP-006: Secure Disposal**
- Cryptographic erasure for encrypted data
- Secure overwrite for unencrypted storage
- Certificate of destruction for physical media
- Audit log entry for all disposals

---

## 4. Network Security Policies

### 4.1 Network Architecture

**Policy NS-001: VPC Configuration**
- Production workloads in private subnets only
- Public subnets for ALB and NAT Gateway only
- VPC Flow Logs enabled for all traffic
- No direct internet access for compute resources

**Policy NS-002: Security Groups**
- Deny-all default policy
- Explicit allow rules documented
- No 0.0.0.0/0 ingress (except ALB 443)
- Regular review of rules (quarterly)

### 4.2 API Security

**Policy NS-003: API Gateway**
- WAF enabled with OWASP ruleset
- Rate limiting: 100 requests/minute per user
- Request validation enabled
- Response headers include security headers

**Policy NS-004: Input Validation**
- All inputs validated before processing
- SQL injection prevention via parameterized queries
- XSS prevention via output encoding
- File upload restrictions (type, size, scanning)

---

## 5. Audit and Monitoring Policies

### 5.1 Logging Requirements

**Policy AM-001: Audit Event Logging**

All of the following events MUST be logged:
- Authentication success/failure
- Authorization decisions
- PHI access (read, create, update, delete)
- System configuration changes
- Security events (alerts, violations)
- Agent invocations and outputs
- Couples merge operations (full audit trail)

**Policy AM-002: Log Format**
```json
{
  "timestamp": "ISO-8601",
  "event_type": "string",
  "user_id": "uuid",
  "resource_type": "string",
  "resource_id": "uuid",
  "action": "string",
  "result": "success|failure",
  "ip_address": "string",
  "user_agent": "string",
  "details": {}
}
```

**Policy AM-003: Log Protection**
- Logs stored in CloudWatch with 7-year retention
- Logs are immutable (no delete permissions)
- Log access requires specific IAM permissions
- Log tampering triggers immediate alert

### 5.2 Monitoring Requirements

**Policy AM-004: Real-Time Monitoring**
- Failed authentication spike (>10 in 5 minutes)
- Unusual data access patterns
- After-hours PHI access
- High-volume API requests
- Error rate anomalies

**Policy AM-005: Alert Response**

| Severity | Response Time | Escalation |
|----------|---------------|------------|
| Critical | 15 minutes | Immediate page, security team |
| High | 1 hour | Slack alert, on-call |
| Medium | 4 hours | Email notification |
| Low | 24 hours | Daily report |

---

## 6. Incident Response Policies

### 6.1 Incident Classification

**Policy IR-001: Incident Severity**

| Level | Description | Examples |
|-------|-------------|----------|
| P1 - Critical | Active breach, PHI exposure | Data exfiltration, unauthorized access |
| P2 - High | Potential breach, service down | Suspicious activity, system outage |
| P3 - Medium | Security weakness, degraded service | Vulnerability found, performance issue |
| P4 - Low | Minor issue, no impact | Failed scan, false positive |

### 6.2 Response Requirements

**Policy IR-002: Breach Notification**
- Internal notification: Immediate
- HHS notification: Within 60 days (>500 individuals)
- Individual notification: Within 60 days
- Media notification: If >500 in single state

See `incident_response.md` for detailed procedures.

---

## 7. Third-Party Security Policies

### 7.1 Vendor Requirements

**Policy TP-001: BAA Requirements**
- All vendors with PHI access MUST have signed BAA
- BAA must include breach notification requirements
- Annual review of vendor compliance
- Current BAAs:
  - AWS (executed)
  - Perplexity Labs (anonymized queries only - no BAA needed)

**Policy TP-002: API Security**
- External API calls MUST NOT include PHI
- Anonymization layer required for research queries
- API keys stored in AWS Secrets Manager
- Rate limiting on all external calls

### 7.2 Integration Security

**Policy TP-003: Allowed Integrations**

| Integration | PHI Allowed | Requirements |
|-------------|-------------|--------------|
| AWS Bedrock | Yes | BAA, VPC endpoint |
| AWS Transcribe | Yes | BAA, VPC endpoint |
| Perplexity | NO | Anonymization required |
| Slack | NO | Sanitized notifications only |
| n8n | Internal only | Self-hosted, VPC |

---

## 8. Physical Security Policies

### 8.1 Cloud Infrastructure

**Policy PS-001: AWS Security**
- All resources in us-east-1 (HIPAA-eligible)
- Multi-AZ deployment for critical services
- No local storage of PHI
- AWS physical security controls apply

### 8.2 Development Workstations

**Policy PS-002: Developer Security**
- No PHI on local machines
- Development uses synthetic data only
- VPN required for production access
- Full disk encryption required

---

## 9. Change Management Policies

### 9.1 Code Changes

**Policy CM-001: Code Review**
- All changes require peer review
- Security-sensitive changes require security review
- No direct commits to main branch
- Automated security scanning in CI/CD

### 9.2 Infrastructure Changes

**Policy CM-002: Infrastructure as Code**
- All infrastructure defined in Terraform
- Changes require plan review
- Production changes require approval
- Rollback plan documented

---

## 10. Compliance Verification

### 10.1 Regular Assessments

**Policy CV-001: Assessment Schedule**

| Assessment | Frequency | Responsible |
|------------|-----------|-------------|
| Vulnerability scan | Weekly | Automated |
| Penetration test | Annual | Third party |
| HIPAA audit | Annual | Compliance team |
| Access review | Quarterly | Security team |
| Policy review | Annual | Leadership |

### 10.2 Compliance Metrics

**Policy CV-002: KPIs**
- Zero unpatched critical vulnerabilities (>7 days)
- 100% MFA adoption
- <15 minute mean time to detect (MTTD)
- <4 hour mean time to respond (MTTR)
- Zero PHI in external API calls

---

## Appendix A: Policy Exceptions

Any exception to these policies requires:
1. Written justification
2. Risk assessment
3. Compensating controls
4. Time-limited approval
5. Security team sign-off
6. Executive approval for PHI-related exceptions

## Appendix B: Related Documents

- `data_flows.md` - PHI data flow diagrams
- `incident_response.md` - Incident response procedures
- `hipaa_checklist.md` - HIPAA compliance verification
- `risk_assessment.md` - Security risk assessment
