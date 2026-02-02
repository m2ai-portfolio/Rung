# Rung Security Risk Assessment

## Document Control

| Version | Date | Author | Status |
|---------|------|--------|--------|
| 1.0 | 2026-02-02 | Security Team | Initial Assessment |

## 1. Executive Summary

This risk assessment identifies, analyzes, and documents security risks to the Rung Psychology Agent Orchestration System. As a HIPAA-covered application processing Protected Health Information (PHI), this assessment is required under 45 CFR 164.308(a)(1)(ii)(A).

### 1.1 Scope

- All Rung system components
- All PHI touchpoints
- All third-party integrations
- All user access paths

### 1.2 Key Findings

| Risk Level | Count | Mitigated |
|------------|-------|-----------|
| Critical | 0 | N/A |
| High | 3 | 3 |
| Medium | 5 | 5 |
| Low | 7 | 7 |

**Overall Risk Posture: ACCEPTABLE**

---

## 2. Methodology

### 2.1 Risk Calculation

**Risk Score = Likelihood × Impact**

| Score | Level | Description |
|-------|-------|-------------|
| 1 | Very Low | Rare occurrence, minimal impact |
| 2 | Low | Unlikely, limited impact |
| 3 | Medium | Possible, moderate impact |
| 4 | High | Likely, significant impact |
| 5 | Critical | Almost certain, severe impact |

**Risk Rating Matrix:**

| | Impact 1 | Impact 2 | Impact 3 | Impact 4 | Impact 5 |
|---|---|---|---|---|---|
| **Likelihood 5** | 5 | 10 | 15 | 20 | 25 |
| **Likelihood 4** | 4 | 8 | 12 | 16 | 20 |
| **Likelihood 3** | 3 | 6 | 9 | 12 | 15 |
| **Likelihood 2** | 2 | 4 | 6 | 8 | 10 |
| **Likelihood 1** | 1 | 2 | 3 | 4 | 5 |

**Risk Levels:**
- 1-4: Low (Green)
- 5-9: Medium (Yellow)
- 10-14: High (Orange)
- 15-25: Critical (Red)

### 2.2 Assessment Process

1. Asset identification
2. Threat identification
3. Vulnerability assessment
4. Likelihood determination
5. Impact analysis
6. Risk calculation
7. Control identification
8. Residual risk evaluation

---

## 3. Asset Inventory

### 3.1 Data Assets

| Asset | Classification | PHI Level | Location |
|-------|---------------|-----------|----------|
| Voice memos | Critical | Direct PHI | S3 (encrypted) |
| Transcripts | Critical | Direct PHI | S3 (encrypted) |
| Session notes | Critical | Direct PHI | RDS (encrypted) |
| Clinical briefs | Critical | Direct PHI | RDS (encrypted) |
| Client guides | High | Derived PHI | RDS (encrypted) |
| Framework analyses | High | Abstracted PHI | RDS (encrypted) |
| Merged frameworks | Medium | Isolated data | RDS (encrypted) |
| Audit logs | Medium | No PHI | CloudWatch |

### 3.2 System Assets

| Asset | Criticality | Description |
|-------|-------------|-------------|
| RDS PostgreSQL | Critical | Primary data store |
| S3 Buckets | Critical | Object storage |
| Lambda Functions | High | API handlers |
| n8n Workflows | High | Orchestration |
| API Gateway | High | Public interface |
| Bedrock | High | LLM processing |
| Cognito | High | Authentication |
| KMS | Critical | Encryption keys |

---

## 4. Threat Analysis

### 4.1 External Threats

| ID | Threat | Description | Threat Actor |
|----|--------|-------------|--------------|
| T-01 | Unauthorized access | External attacker gains system access | Cybercriminal |
| T-02 | Data exfiltration | PHI stolen from system | Cybercriminal |
| T-03 | Ransomware | Systems encrypted for ransom | Cybercriminal |
| T-04 | DDoS attack | Service availability impacted | Various |
| T-05 | Supply chain attack | Compromised dependency | Nation-state/Criminal |

### 4.2 Internal Threats

| ID | Threat | Description | Threat Actor |
|----|--------|-------------|--------------|
| T-06 | Insider data theft | Employee steals PHI | Malicious insider |
| T-07 | Accidental disclosure | Unintentional PHI exposure | Employee error |
| T-08 | Privilege abuse | Excessive access misused | Authorized user |

### 4.3 Application-Specific Threats

| ID | Threat | Description | Threat Actor |
|----|--------|-------------|--------------|
| T-09 | Isolation bypass | PHI crosses client boundaries | Bug/Attacker |
| T-10 | Agent manipulation | LLM produces harmful output | Prompt injection |
| T-11 | Anonymization failure | PHI sent to external API | Bug |
| T-12 | Couples data mixing | Partner A sees Partner B data | Bug/Attacker |

---

## 5. Vulnerability Assessment

### 5.1 Technical Vulnerabilities

| ID | Vulnerability | CVSS | Status |
|----|---------------|------|--------|
| V-01 | Unpatched dependencies | Varies | Mitigated (automated scanning) |
| V-02 | SQL injection | 9.8 | Mitigated (parameterized queries) |
| V-03 | XSS | 6.1 | Mitigated (output encoding) |
| V-04 | SSRF | 7.5 | Mitigated (input validation) |
| V-05 | Broken authentication | 7.5 | Mitigated (Cognito MFA) |

### 5.2 Operational Vulnerabilities

| ID | Vulnerability | Severity | Status |
|----|---------------|----------|--------|
| V-06 | Weak passwords | High | Mitigated (policy enforcement) |
| V-07 | Insufficient logging | Medium | Mitigated (comprehensive audit) |
| V-08 | Missing backups | High | Mitigated (automated backups) |
| V-09 | No DR plan | High | Mitigated (multi-AZ, documented DR) |

### 5.3 Application-Specific Vulnerabilities

| ID | Vulnerability | Severity | Status |
|----|---------------|----------|--------|
| V-10 | Weak isolation layer | Critical | Mitigated (whitelist approach) |
| V-11 | LLM output not validated | High | Mitigated (schema validation) |
| V-12 | Anonymizer bypass | Critical | Mitigated (fail-safe blocking) |

---

## 6. Risk Register

### 6.1 High Risks (Mitigated)

#### R-01: Isolation Layer Bypass
| Attribute | Value |
|-----------|-------|
| Threat | T-09, T-12 |
| Vulnerability | V-10 |
| Asset | Client PHI, Couples data |
| Inherent Likelihood | 3 |
| Inherent Impact | 5 |
| **Inherent Risk** | **15 (Critical)** |
| Controls | Whitelist-only extraction, 100% test coverage, strict mode |
| Residual Likelihood | 1 |
| Residual Impact | 5 |
| **Residual Risk** | **5 (Medium)** |
| Owner | Security Team |
| Review | Quarterly |

#### R-02: PHI Sent to External API
| Attribute | Value |
|-----------|-------|
| Threat | T-11 |
| Vulnerability | V-12 |
| Asset | Client PHI |
| Inherent Likelihood | 3 |
| Inherent Impact | 5 |
| **Inherent Risk** | **15 (Critical)** |
| Controls | Anonymization layer, PHI detection, fail-safe blocking |
| Residual Likelihood | 1 |
| Residual Impact | 5 |
| **Residual Risk** | **5 (Medium)** |
| Owner | Security Team |
| Review | Quarterly |

#### R-03: Unauthorized PHI Access
| Attribute | Value |
|-----------|-------|
| Threat | T-01, T-06, T-08 |
| Vulnerability | V-05, V-06 |
| Asset | All PHI |
| Inherent Likelihood | 4 |
| Inherent Impact | 5 |
| **Inherent Risk** | **20 (Critical)** |
| Controls | MFA, RBAC, audit logging, session management |
| Residual Likelihood | 2 |
| Residual Impact | 4 |
| **Residual Risk** | **8 (Medium)** |
| Owner | Security Team |
| Review | Quarterly |

### 6.2 Medium Risks

#### R-04: Data Exfiltration
| Attribute | Value |
|-----------|-------|
| Threat | T-02 |
| Vulnerability | V-01, V-02 |
| Asset | All PHI |
| Inherent Likelihood | 3 |
| Inherent Impact | 5 |
| **Inherent Risk** | **15 (Critical)** |
| Controls | Encryption, network segmentation, DLP monitoring |
| Residual Likelihood | 1 |
| Residual Impact | 4 |
| **Residual Risk** | **4 (Low)** |
| Owner | Security Team |
| Review | Quarterly |

#### R-05: Ransomware Attack
| Attribute | Value |
|-----------|-------|
| Threat | T-03 |
| Vulnerability | V-01 |
| Asset | All systems |
| Inherent Likelihood | 3 |
| Inherent Impact | 4 |
| **Inherent Risk** | **12 (High)** |
| Controls | Automated backups, multi-AZ, immutable logs |
| Residual Likelihood | 2 |
| Residual Impact | 2 |
| **Residual Risk** | **4 (Low)** |
| Owner | DevOps Team |
| Review | Quarterly |

#### R-06: LLM Manipulation
| Attribute | Value |
|-----------|-------|
| Threat | T-10 |
| Vulnerability | V-11 |
| Asset | Agent outputs |
| Inherent Likelihood | 3 |
| Inherent Impact | 3 |
| **Inherent Risk** | **9 (Medium)** |
| Controls | Schema validation, output filtering, prompt hardening |
| Residual Likelihood | 2 |
| Residual Impact | 2 |
| **Residual Risk** | **4 (Low)** |
| Owner | Engineering Team |
| Review | Quarterly |

#### R-07: Service Availability
| Attribute | Value |
|-----------|-------|
| Threat | T-04 |
| Vulnerability | None specific |
| Asset | System availability |
| Inherent Likelihood | 3 |
| Inherent Impact | 3 |
| **Inherent Risk** | **9 (Medium)** |
| Controls | WAF, rate limiting, multi-AZ, auto-scaling |
| Residual Likelihood | 2 |
| Residual Impact | 2 |
| **Residual Risk** | **4 (Low)** |
| Owner | DevOps Team |
| Review | Quarterly |

#### R-08: Accidental Disclosure
| Attribute | Value |
|-----------|-------|
| Threat | T-07 |
| Vulnerability | Human error |
| Asset | Client PHI |
| Inherent Likelihood | 3 |
| Inherent Impact | 4 |
| **Inherent Risk** | **12 (High)** |
| Controls | Training, access controls, audit logging, DLP |
| Residual Likelihood | 2 |
| Residual Impact | 3 |
| **Residual Risk** | **6 (Medium)** |
| Owner | HR/Security |
| Review | Annually |

### 6.3 Low Risks

#### R-09: Supply Chain Attack
| Attribute | Value |
|-----------|-------|
| Threat | T-05 |
| Vulnerability | V-01 |
| Asset | All systems |
| Inherent Likelihood | 2 |
| Inherent Impact | 4 |
| **Inherent Risk** | **8 (Medium)** |
| Controls | Dependency scanning, lockfiles, vendor review |
| Residual Likelihood | 1 |
| Residual Impact | 3 |
| **Residual Risk** | **3 (Low)** |
| Owner | Engineering Team |
| Review | Annually |

#### R-10 through R-15: Additional Low Risks
| ID | Risk | Residual Score |
|----|------|----------------|
| R-10 | Configuration drift | 3 (Low) |
| R-11 | Key compromise | 4 (Low) |
| R-12 | Backup failure | 2 (Low) |
| R-13 | Log tampering | 2 (Low) |
| R-14 | Session hijacking | 3 (Low) |
| R-15 | API abuse | 4 (Low) |

---

## 7. Control Summary

### 7.1 Preventive Controls

| Control | Risks Addressed | Effectiveness |
|---------|-----------------|---------------|
| Encryption (at rest) | R-02, R-04 | High |
| Encryption (in transit) | R-02, R-04 | High |
| MFA | R-03, R-14 | High |
| RBAC | R-03, R-06, R-08 | High |
| Input validation | R-06, V-02, V-03, V-04 | High |
| Isolation layer | R-01, R-02 | Critical |
| Anonymization | R-02 | Critical |
| Network segmentation | R-01, R-04 | High |

### 7.2 Detective Controls

| Control | Risks Addressed | Effectiveness |
|---------|-----------------|---------------|
| Audit logging | R-03, R-06, R-08 | High |
| Anomaly detection | R-03, R-04, R-05 | Medium |
| Vulnerability scanning | R-04, R-05, R-09 | High |
| Log monitoring | All | High |
| Integrity monitoring | R-05, R-13 | Medium |

### 7.3 Corrective Controls

| Control | Risks Addressed | Effectiveness |
|---------|-----------------|---------------|
| Incident response | All | High |
| Backup/restore | R-05 | High |
| DR procedures | R-05, R-07 | High |
| Patch management | R-04, R-05, R-09 | High |

---

## 8. Risk Treatment Plan

### 8.1 Accepted Risks

No risks are currently accepted without mitigation.

### 8.2 Transferred Risks

| Risk | Transfer Method | Party |
|------|-----------------|-------|
| Infrastructure physical security | Cloud hosting | AWS |
| Payment processing | Not applicable | N/A |

### 8.3 Avoided Risks

| Risk | Avoidance Method |
|------|------------------|
| On-premises PHI storage | Cloud-only architecture |
| Direct client LLM access | Agent abstraction layer |

### 8.4 Mitigated Risks

All identified risks have been mitigated to acceptable levels as documented in Section 6.

---

## 9. Recommendations

### 9.1 Short-Term (0-3 months)

| Priority | Recommendation | Status |
|----------|----------------|--------|
| High | Implement automated security scanning in CI/CD | Planned |
| High | Complete penetration testing | Planned |
| Medium | Enhance anomaly detection rules | In Progress |
| Medium | Document all runbooks | In Progress |

### 9.2 Medium-Term (3-6 months)

| Priority | Recommendation | Status |
|----------|----------------|--------|
| Medium | Implement SIEM solution | Planned |
| Medium | Enhance DLP capabilities | Planned |
| Low | Security awareness training refresh | Planned |

### 9.3 Long-Term (6-12 months)

| Priority | Recommendation | Status |
|----------|----------------|--------|
| Medium | Third-party security audit | Planned |
| Low | SOC 2 Type II certification | Under consideration |
| Low | ISO 27001 certification | Under consideration |

---

## 10. Conclusion

This risk assessment demonstrates that Rung has implemented comprehensive security controls to protect PHI and maintain HIPAA compliance. All identified high and critical inherent risks have been mitigated to acceptable levels through multiple layers of technical and administrative controls.

The unique risks associated with AI-powered psychology support (isolation layer bypass, LLM manipulation, anonymization failure) have been addressed with specialized controls including whitelist-based extraction, schema validation, and fail-safe blocking mechanisms.

### 10.1 Next Steps

1. Complete planned short-term recommendations
2. Schedule quarterly risk review
3. Plan annual comprehensive reassessment
4. Monitor for new threats and vulnerabilities

---

## Appendix A: Risk Assessment Team

| Name | Role | Contribution |
|------|------|--------------|
| [Security Officer] | Lead | Overall assessment |
| [Engineering Lead] | Technical | Vulnerability analysis |
| [DevOps Lead] | Infrastructure | Control verification |
| [Compliance Officer] | Compliance | HIPAA requirements |

## Appendix B: References

- NIST SP 800-30: Guide for Conducting Risk Assessments
- HIPAA Security Rule: 45 CFR 164.308(a)(1)
- OWASP Top 10 2021
- AWS Well-Architected Framework - Security Pillar

## Appendix C: Review History

| Date | Reviewer | Changes |
|------|----------|---------|
| 2026-02-02 | Security Team | Initial assessment |
