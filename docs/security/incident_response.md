# Rung Incident Response Plan

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-02 | Security Team | Initial release |

## 1. Purpose and Scope

This document defines the incident response procedures for the Rung Psychology Agent Orchestration System. As a HIPAA-covered entity, Rung must maintain robust incident detection, response, and reporting capabilities.

### 1.1 Scope

This plan covers:
- Security incidents affecting system availability, integrity, or confidentiality
- Privacy incidents involving PHI
- Compliance violations
- Third-party security events affecting Rung

### 1.2 Definitions

| Term | Definition |
|------|------------|
| Security Incident | Any event that threatens the security of Rung systems |
| Breach | Unauthorized access, use, or disclosure of PHI |
| Covered Entity | Rung and its business associates |
| Breach Notification | Required communication to affected parties |

---

## 2. Incident Response Team

### 2.1 Core Team

| Role | Primary | Backup | Responsibilities |
|------|---------|--------|------------------|
| Incident Commander | CTO | Engineering Lead | Overall response coordination |
| Security Lead | Security Engineer | DevOps Lead | Technical investigation |
| Communications | CEO | Operations | External communications |
| Legal/Compliance | Legal Counsel | Compliance Officer | Regulatory requirements |
| Technical Lead | Senior Engineer | Platform Engineer | System recovery |

### 2.2 Contact Information

**On-Call Rotation:** PagerDuty - rung-security

**Escalation Path:**
1. On-call engineer (5 min response)
2. Security Lead (15 min response)
3. Incident Commander (30 min response)
4. Executive team (as needed)

---

## 3. Incident Classification

### 3.1 Severity Levels

| Level | Name | Description | Response Time | Examples |
|-------|------|-------------|---------------|----------|
| P1 | Critical | Active breach, PHI exposed | 15 min | Data exfiltration, unauthorized PHI access |
| P2 | High | Potential breach, major service impact | 1 hour | Suspicious activity, system compromise |
| P3 | Medium | Security weakness, degraded service | 4 hours | Vulnerability discovered, minor outage |
| P4 | Low | Minor issue, no immediate impact | 24 hours | Failed scan, policy violation |

### 3.2 Incident Categories

| Category | Description | HIPAA Implications |
|----------|-------------|-------------------|
| Unauthorized Access | Access without proper authorization | Potential breach |
| Data Exposure | PHI visible to unauthorized parties | Breach requiring notification |
| System Compromise | Malware, unauthorized changes | Potential breach |
| Availability | Service disruption | May affect access to PHI |
| Insider Threat | Employee misconduct | Potential breach |
| Third-Party | Vendor security event | Depends on data exposure |

---

## 4. Incident Response Phases

### 4.1 Phase 1: Detection and Identification

**Objectives:**
- Detect security events
- Confirm incident validity
- Classify severity
- Activate response team

**Detection Sources:**
- CloudWatch anomaly detection
- WAF alerts
- Failed authentication monitoring
- Audit log analysis
- User reports
- Third-party notifications

**Identification Checklist:**
- [ ] Event confirmed as incident (not false positive)
- [ ] Severity level assigned
- [ ] Category determined
- [ ] PHI involvement assessed
- [ ] Incident ticket created
- [ ] Response team notified

**Timeline:** 15 minutes for P1, 1 hour for P2

### 4.2 Phase 2: Containment

**Objectives:**
- Limit incident scope
- Preserve evidence
- Prevent further damage
- Maintain service where safe

**Short-Term Containment:**
- [ ] Isolate affected systems
- [ ] Block malicious IPs/users
- [ ] Revoke compromised credentials
- [ ] Enable enhanced logging
- [ ] Snapshot affected resources

**Long-Term Containment:**
- [ ] Apply temporary fixes
- [ ] Segment network if needed
- [ ] Implement additional monitoring
- [ ] Prepare for eradication

**Evidence Preservation:**
- [ ] Capture system images
- [ ] Export logs to secure location
- [ ] Document timeline
- [ ] Preserve chain of custody

**Timeline:** 1 hour for initial containment

### 4.3 Phase 3: Eradication

**Objectives:**
- Remove threat completely
- Fix vulnerabilities exploited
- Verify clean state

**Eradication Steps:**
- [ ] Identify root cause
- [ ] Remove malware/unauthorized access
- [ ] Patch vulnerabilities
- [ ] Reset affected credentials
- [ ] Review and fix configurations
- [ ] Update security controls

**Verification:**
- [ ] Run security scans
- [ ] Review logs for residual activity
- [ ] Confirm all indicators of compromise addressed

**Timeline:** Varies based on scope

### 4.4 Phase 4: Recovery

**Objectives:**
- Restore normal operations
- Verify system integrity
- Resume business functions

**Recovery Steps:**
- [ ] Restore from clean backups if needed
- [ ] Rebuild affected systems
- [ ] Gradual service restoration
- [ ] Enhanced monitoring period
- [ ] User communication

**Validation:**
- [ ] System functionality testing
- [ ] Security control verification
- [ ] PHI integrity confirmation
- [ ] Performance baseline comparison

**Timeline:** Varies; enhanced monitoring for 30 days

### 4.5 Phase 5: Post-Incident

**Objectives:**
- Document lessons learned
- Improve security posture
- Complete regulatory requirements

**Post-Incident Activities:**
- [ ] Complete incident report
- [ ] Conduct lessons learned meeting
- [ ] Update security controls
- [ ] Revise procedures as needed
- [ ] Complete regulatory notifications
- [ ] Archive incident documentation

**Timeline:** 7 days for initial review, ongoing for improvements

---

## 5. Communication Plan

### 5.1 Internal Communication

**During Incident:**
- Slack channel: #incident-response (private)
- Video bridge: Always-on during P1/P2
- Status updates: Every 30 minutes for P1, hourly for P2

**Post-Incident:**
- All-hands briefing for significant incidents
- Written summary to leadership
- Lessons learned distribution

### 5.2 External Communication

**Stakeholder Communication Matrix:**

| Stakeholder | When to Notify | Method | Owner |
|-------------|----------------|--------|-------|
| Affected Users | Confirmed breach | Email + In-app | Communications |
| Regulators (HHS) | >500 affected, within 60 days | OCR Portal | Legal/Compliance |
| Media | >500 in single state | Press release | Communications |
| Business Partners | If they are affected | Direct contact | Legal |
| Law Enforcement | If criminal activity | Direct contact | Legal |

### 5.3 Communication Templates

**Initial Notification (Internal):**
```
SECURITY INCIDENT - [SEVERITY]

Time Detected: [TIME]
Incident ID: [ID]
Category: [CATEGORY]
PHI Involved: [YES/NO/UNKNOWN]

Brief Description:
[DESCRIPTION]

Current Status: [INVESTIGATING/CONTAINED/RESOLVED]

Bridge: [LINK]
Lead: [NAME]

Updates every [30 min/1 hour]
```

**Breach Notification (External):**
```
Dear [NAME],

We are writing to inform you of a security incident that may have
affected your personal health information.

What Happened:
[BRIEF DESCRIPTION]

What Information Was Involved:
[TYPES OF DATA]

What We Are Doing:
[ACTIONS TAKEN]

What You Can Do:
[RECOMMENDED ACTIONS]

For More Information:
[CONTACT DETAILS]

[SIGNATURE]
```

---

## 6. HIPAA Breach Notification Requirements

### 6.1 Breach Determination

**Is it a Breach?**

A breach is presumed unless one of these exceptions applies:
1. Unintentional acquisition by workforce member acting in good faith
2. Inadvertent disclosure between authorized persons
3. Good faith belief that unauthorized person could not retain information
4. Information was encrypted to NIST standards

**Risk Assessment Factors:**
- Nature and extent of PHI involved
- Unauthorized person who used/received PHI
- Whether PHI was actually acquired or viewed
- Extent to which risk has been mitigated

### 6.2 Notification Timeline

| Condition | Timeline | Recipient |
|-----------|----------|-----------|
| Any breach | Within 60 days of discovery | Affected individuals |
| >500 affected | Within 60 days | HHS OCR |
| >500 in single state | Within 60 days | Prominent media |
| <500 affected | Within 60 days of calendar year end | HHS OCR (annual log) |

### 6.3 Notification Content Requirements

Individual notifications must include:
- [ ] Brief description of what happened
- [ ] Types of information involved
- [ ] Steps individuals should take
- [ ] What covered entity is doing
- [ ] Contact procedures

HHS notification must include:
- [ ] Name of covered entity
- [ ] Business associate involved (if applicable)
- [ ] Discovery date
- [ ] Number of individuals affected
- [ ] Types of information involved
- [ ] Brief description
- [ ] Safeguards in place
- [ ] Actions taken in response

---

## 7. Specific Incident Playbooks

### 7.1 Unauthorized PHI Access

**Indicators:**
- Unusual query patterns in audit logs
- Access from unexpected IP/location
- Access outside business hours
- Bulk data downloads

**Response:**
1. Immediately revoke user access
2. Review audit logs for scope
3. Identify all accessed records
4. Assess PHI exposure
5. Document for breach determination
6. Notify affected therapists

### 7.2 Isolation Layer Bypass

**Indicators:**
- Non-whitelisted terms in merge output
- PHI patterns in cross-client data
- Audit log shows isolation_invoked = false

**Response:**
1. **CRITICAL**: Halt all couples merge operations
2. Review all recent merge outputs
3. Identify scope of exposure
4. Fix isolation layer
5. Verify with security tests
6. Resume only after verification

### 7.3 External API Data Leak

**Indicators:**
- PHI patterns in Perplexity logs
- Anonymization failures
- Query blocking alerts

**Response:**
1. Block all external API calls
2. Review query logs
3. Contact external vendor
4. Assess PHI exposure
5. Fix anonymization layer
6. Resume with enhanced monitoring

### 7.4 Credential Compromise

**Indicators:**
- Multiple failed authentications
- Successful auth from unusual location
- Password reset requests
- MFA bypass attempts

**Response:**
1. Force logout affected user
2. Reset credentials
3. Review session activity
4. Check for data access
5. Review MFA configuration
6. Notify user

### 7.5 Ransomware/Malware

**Indicators:**
- Unusual file encryption
- Ransom notes
- Unusual network traffic
- System performance degradation

**Response:**
1. Isolate affected systems immediately
2. Do not pay ransom
3. Preserve evidence
4. Assess backup integrity
5. Contact law enforcement
6. Rebuild from clean backups

---

## 8. Tools and Resources

### 8.1 Investigation Tools

| Tool | Purpose | Access |
|------|---------|--------|
| CloudWatch Logs Insights | Log analysis | AWS Console |
| AWS CloudTrail | API audit | AWS Console |
| VPC Flow Logs | Network analysis | AWS Console |
| AWS GuardDuty | Threat detection | AWS Console |
| Security Hub | Security posture | AWS Console |

### 8.2 Common Queries

**Audit Log - PHI Access by User:**
```sql
SELECT timestamp, user_id, resource_type, resource_id, action
FROM audit_logs
WHERE user_id = '[USER_ID]'
  AND resource_type IN ('client', 'session', 'clinical_brief')
ORDER BY timestamp DESC;
```

**CloudWatch - Failed Authentications:**
```
fields @timestamp, @message
| filter @message like /authentication failed/
| stats count() by bin(5m)
```

**Couples Merge Audit:**
```sql
SELECT * FROM audit_logs
WHERE event_type = 'couples_merge'
  AND isolation_invoked = false;
```

### 8.3 Evidence Collection

**Preserve:**
- System snapshots (EBS, RDS)
- Log exports (CloudWatch to S3)
- Network captures (VPC Flow Logs)
- Configuration backups

**Chain of Custody:**
- Document who accessed evidence
- Record timestamps
- Use write-once storage
- Hash files for integrity

---

## 9. Training and Testing

### 9.1 Training Requirements

| Role | Training | Frequency |
|------|----------|-----------|
| All Staff | Security awareness | Annual |
| Engineering | Incident response | Quarterly |
| Incident Team | Tabletop exercises | Quarterly |
| Leadership | Breach notification | Annual |

### 9.2 Testing Schedule

| Exercise | Frequency | Participants |
|----------|-----------|--------------|
| Tabletop | Quarterly | Incident team |
| Technical drill | Monthly | Engineering |
| Full simulation | Annual | All teams |
| Backup restore | Monthly | DevOps |

---

## 10. Metrics and Reporting

### 10.1 Key Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Mean Time to Detect (MTTD) | <15 min | - |
| Mean Time to Respond (MTTR) | <4 hours | - |
| Mean Time to Contain (MTTC) | <1 hour | - |
| Incidents per quarter | <5 | - |
| P1/P2 incidents per year | 0 | - |

### 10.2 Reporting Requirements

**Monthly:**
- Security incident summary
- Near-miss analysis
- Control effectiveness

**Quarterly:**
- Trend analysis
- Lessons learned summary
- Training completion

**Annual:**
- Full security review
- Policy updates
- Risk assessment refresh

---

## Appendix A: Incident Report Template

```
INCIDENT REPORT

Incident ID: [ID]
Date/Time Detected: [TIMESTAMP]
Date/Time Resolved: [TIMESTAMP]
Severity: [P1/P2/P3/P4]
Category: [CATEGORY]

SUMMARY
[Brief description of the incident]

TIMELINE
[Detailed timeline of events]

ROOT CAUSE
[Analysis of why the incident occurred]

IMPACT
- Systems Affected: [LIST]
- Data Exposed: [YES/NO, DETAILS]
- Users Affected: [COUNT]
- Service Disruption: [DURATION]

RESPONSE ACTIONS
[List of actions taken]

LESSONS LEARNED
[What can be improved]

RECOMMENDATIONS
[Specific improvements to implement]

ATTACHMENTS
[Links to logs, evidence, communications]
```

## Appendix B: Escalation Contacts

**Primary Contacts:**
- Security: security@rung.health
- On-Call: PagerDuty rung-security
- Legal: legal@rung.health

**External Contacts:**
- AWS Support: Enterprise support case
- Law Enforcement: Local FBI field office
- HHS OCR: https://ocrportal.hhs.gov

## Appendix C: Regulatory References

- HIPAA Security Rule: 45 CFR 164.308(a)(6)
- HIPAA Breach Notification Rule: 45 CFR 164.400-414
- HITECH Act: Section 13402
