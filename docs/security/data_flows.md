# Rung Data Flow Diagrams

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-02 | Security Team | Initial release |

## 1. Overview

This document describes data flows in the Rung system with emphasis on PHI handling. All flows are designed to minimize PHI exposure and maintain HIPAA compliance.

### 1.1 PHI Markers Legend

```
[PHI] - Contains Protected Health Information
[ePHI] - Contains encrypted PHI
[ANON] - Anonymized data (no PHI)
[SAFE] - Framework-level data only (isolation layer output)
[AUDIT] - Audit trail data
```

---

## 2. Pre-Session Workflow

### 2.1 Voice Memo Upload Flow

```
┌─────────────┐     [PHI]      ┌─────────────┐    [ePHI]     ┌─────────────┐
│   Client    │ ──────────────>│   API GW    │ ─────────────>│     S3      │
│   Device    │   Voice Memo   │   + WAF     │  Encrypted    │ voice-memos │
└─────────────┘                └─────────────┘               └─────────────┘
                                     │                              │
                                     │ [AUDIT]                      │ [ePHI]
                                     v                              v
                              ┌─────────────┐               ┌─────────────┐
                              │  CloudWatch │               │  Transcribe │
                              │    Logs     │               │   Medical   │
                              └─────────────┘               └─────────────┘
                                                                   │
                                                                   │ [ePHI]
                                                                   v
                                                            ┌─────────────┐
                                                            │     S3      │
                                                            │ transcripts │
                                                            └─────────────┘
```

**PHI Touchpoints:**
1. Client device -> API Gateway: Voice memo (TLS encrypted)
2. API Gateway -> S3: Client-side encrypted before storage
3. S3 -> Transcribe: Encrypted in transit
4. Transcribe -> S3: Output encrypted at rest

**Controls:**
- TLS 1.3 for all transfers
- KMS encryption for S3
- VPC endpoints for AWS services
- Audit logging at API Gateway

### 2.2 Rung Agent Analysis Flow

```
┌─────────────┐    [ePHI]     ┌─────────────┐    [PHI]      ┌─────────────┐
│     S3      │ ─────────────>│    n8n      │ ─────────────>│   Bedrock   │
│ transcripts │  Decrypted    │  Workflow   │   Analysis    │   (Claude)  │
└─────────────┘   in memory   └─────────────┘   Request     └─────────────┘
                                    │                              │
                                    │                              │ [PHI]
                                    │                              v
                                    │                       ┌─────────────┐
                                    │ [ePHI]                │    Rung     │
                                    v                       │   Output    │
                              ┌─────────────┐               │  (struct)   │
                              │     RDS     │<──────────────└─────────────┘
                              │clinical_briefs               [ePHI]
                              └─────────────┘
```

**PHI Touchpoints:**
1. S3 -> n8n: Decrypted in memory (VPC only)
2. n8n -> Bedrock: PHI sent for analysis (VPC endpoint, BAA)
3. Bedrock -> n8n: Structured output with PHI
4. n8n -> RDS: Encrypted before storage

**Controls:**
- n8n in private subnet
- Bedrock via VPC endpoint (no public internet)
- Field-level encryption for clinical content
- No PHI logged in n8n

### 2.3 Research Query Flow (Perplexity)

```
┌─────────────┐    [PHI]      ┌─────────────┐    [ANON]     ┌─────────────┐
│    Rung     │ ─────────────>│ Anonymizer  │ ─────────────>│  Perplexity │
│   Output    │               │   Layer     │   Query       │     API     │
└─────────────┘               └─────────────┘               └─────────────┘
                                    │                              │
                                    │ BLOCKED                      │ [ANON]
                                    │ if PHI                       v
                                    v                       ┌─────────────┐
                              ┌─────────────┐               │  Research   │
                              │   Reject    │               │   Results   │
                              │   Request   │               └─────────────┘
                              └─────────────┘
```

**CRITICAL: NO PHI reaches Perplexity**

**Anonymization Rules:**
- Strip all proper nouns
- Remove dates and locations
- Replace specific details with generic terms
- Block query if anonymization uncertain

**Controls:**
- Whitelist-based query construction
- PHI detection before external call
- Fail-safe: reject suspicious queries
- No BAA with Perplexity (not needed)

### 2.4 Beth Agent Synthesis Flow

```
┌─────────────┐    [PHI]      ┌─────────────┐    [SAFE]     ┌─────────────┐
│    Rung     │ ─────────────>│ Abstraction │ ─────────────>│   Bedrock   │
│   Output    │               │   Layer     │  Themes Only  │   (Beth)    │
└─────────────┘               └─────────────┘               └─────────────┘
                                                                   │
         PROHIBITED:                                               │ [SAFE]
         - Clinical terminology                                    v
         - Defense mechanisms                              ┌─────────────┐
         - Risk flags                                      │    Beth     │
         - Raw evidence                                    │   Output    │
                                                           └─────────────┘
                                                                   │
                                                                   │ [ePHI]
                                                                   v
                                                           ┌─────────────┐
                                                           │     RDS     │
                                                           │client_guides│
                                                           └─────────────┘
```

**CRITICAL: Raw Rung output NEVER reaches Beth**

**Abstraction Layer Output:**
- Theme categories only
- Exploration areas (generalized)
- Session focus (non-clinical language)

**Controls:**
- Whitelist extraction only
- No clinical terminology passes
- Separate agent prompts
- Output validation

---

## 3. Post-Session Workflow

### 3.1 Notes Processing Flow

```
┌─────────────┐    [PHI]      ┌─────────────┐    [ePHI]     ┌─────────────┐
│  Therapist  │ ─────────────>│   API GW    │ ─────────────>│     RDS     │
│   Client    │  Session Notes│   + WAF     │   Encrypted   │  sessions   │
└─────────────┘               └─────────────┘               └─────────────┘
                                    │                              │
                                    │ [AUDIT]                      │ [ePHI]
                                    v                              v
                              ┌─────────────┐               ┌─────────────┐
                              │  CloudWatch │               │    n8n      │
                              │    Logs     │               │  Workflow   │
                              └─────────────┘               └─────────────┘
                                                                   │
                                                                   │ [PHI]
                                                                   v
                                                           ┌─────────────┐
                                                           │  Framework  │
                                                           │  Extractor  │
                                                           └─────────────┘
```

### 3.2 Development Plan Flow

```
┌─────────────┐    [PHI]      ┌─────────────┐    [SAFE]     ┌─────────────┐
│  Framework  │ ─────────────>│   Sprint    │ ─────────────>│  Perceptor  │
│  Extractor  │               │   Planner   │   Context     │    MCP      │
└─────────────┘               └─────────────┘               └─────────────┘
                                    │                              │
                                    │ [ePHI]                       │ [SAFE]
                                    v                              v
                              ┌─────────────┐               ┌─────────────┐
                              │     RDS     │               │   Context   │
                              │dev_plans    │               │   Store     │
                              └─────────────┘               └─────────────┘
```

**Perceptor Context:**
- Tags: [agent, stage, session-date, client-id]
- Content: Framework-level data only
- No PHI in stored contexts

---

## 4. Couples Merge Workflow

### 4.1 Framework Isolation Flow

```
┌─────────────┐                              ┌─────────────┐
│  Partner A  │    [PHI]      ┌─────────────┤  Partner B  │
│  Analysis   │ ─────────────>│  ISOLATION  │<─────────────│  Analysis   │
│   (Rung)    │               │   LAYER     │    [PHI]     │   (Rung)    │
└─────────────┘               └─────────────┘              └─────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              v                     v                     v
       ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
       │  [SAFE]     │       │  [SAFE]     │       │  [BLOCKED]  │
       │ Attachment  │       │  Framework  │       │   Quotes    │
       │  Patterns   │       │   Names     │       │  Incidents  │
       └─────────────┘       └─────────────┘       │  Details    │
                                                   └─────────────┘
```

**CRITICAL SECURITY BOUNDARY**

**Allowed Output (Whitelist):**
- Attachment pattern categories
- Framework references (names only)
- Theme categories
- Modality names
- Defense pattern categories
- Communication pattern categories

**BLOCKED (Never Crosses):**
- Direct quotes from sessions
- Specific incidents or events
- Emotional content details
- Dates or timeline specifics
- Names, places, identifying info
- Numerical details
- Evidence strings
- Session questions
- Exploration suggestions

### 4.2 Topic Matching Flow

```
┌─────────────┐               ┌─────────────┐               ┌─────────────┐
│  Partner A  │    [SAFE]     │   Topic     │    [SAFE]     │  Partner B  │
│  Isolated   │ ─────────────>│   Matcher   │<─────────────│  Isolated   │
│ Frameworks  │               └─────────────┘               │ Frameworks  │
└─────────────┘                     │                       └─────────────┘
                                    │ [SAFE]
                    ┌───────────────┼───────────────┐
                    v               v               v
             ┌───────────┐   ┌───────────┐   ┌───────────┐
             │Overlapping│   │Complement-│   │ Potential │
             │  Themes   │   │ary Patterns│  │ Conflicts │
             └───────────┘   └───────────┘   └───────────┘
```

### 4.3 Merge Engine Flow

```
┌─────────────┐    [SAFE]     ┌─────────────┐    [SAFE]     ┌─────────────┐
│   Topic     │ ─────────────>│   Merge     │ ─────────────>│   Bedrock   │
│   Matcher   │               │   Engine    │               │   (Rung)    │
└─────────────┘               └─────────────┘               └─────────────┘
                                    │                              │
                                    │ [AUDIT]                      │ [SAFE]
                                    v                              v
                              ┌─────────────┐               ┌─────────────┐
                              │  Audit Log  │               │   Merged    │
                              │  (complete) │               │ Frameworks  │
                              └─────────────┘               └─────────────┘
                                                                   │
                                                                   │ [ePHI]
                                                                   v
                                                           ┌─────────────┐
                                                           │     RDS     │
                                                           │framework_   │
                                                           │  merges     │
                                                           └─────────────┘
```

**Audit Requirements:**
- Every merge operation logged
- Isolation layer invocation recorded
- Data accessed documented
- Therapist authorization verified
- IP address captured
- Timestamp recorded

---

## 5. Data Storage Architecture

### 5.1 Database PHI Distribution

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              RDS PostgreSQL                                 │
├──────────────────┬──────────────────────────────────────────────────────────┤
│     Table        │                    PHI Fields                            │
├──────────────────┼──────────────────────────────────────────────────────────┤
│ therapists       │ email_encrypted [ePHI]                                   │
├──────────────────┼──────────────────────────────────────────────────────────┤
│ clients          │ name_encrypted [ePHI], contact_encrypted [ePHI]          │
├──────────────────┼──────────────────────────────────────────────────────────┤
│ sessions         │ notes_encrypted [ePHI]                                   │
├──────────────────┼──────────────────────────────────────────────────────────┤
│ clinical_briefs  │ content_encrypted [ePHI]                                 │
├──────────────────┼──────────────────────────────────────────────────────────┤
│ client_guides    │ content_encrypted [ePHI]                                 │
├──────────────────┼──────────────────────────────────────────────────────────┤
│ development_plans│ goals [SAFE], exercises [SAFE], progress [SAFE]          │
├──────────────────┼──────────────────────────────────────────────────────────┤
│ couple_links     │ No PHI (IDs only)                                        │
├──────────────────┼──────────────────────────────────────────────────────────┤
│ framework_merges │ partner_*_frameworks [SAFE], merged_insights [SAFE]      │
├──────────────────┼──────────────────────────────────────────────────────────┤
│ audit_logs       │ No PHI (sanitized details)                               │
└──────────────────┴──────────────────────────────────────────────────────────┘
```

### 5.2 S3 Bucket PHI Distribution

```
┌────────────────────────────────────────────────────────────────────────────┐
│                                 S3 Buckets                                  │
├──────────────────────────┬──────────────────────────────────────────────────┤
│       Bucket             │                  Content                         │
├──────────────────────────┼──────────────────────────────────────────────────┤
│ rung-voice-memos-{env}   │ Voice recordings [ePHI] - Client encrypted       │
├──────────────────────────┼──────────────────────────────────────────────────┤
│ rung-transcripts-{env}   │ Transcriptions [ePHI] - KMS encrypted            │
├──────────────────────────┼──────────────────────────────────────────────────┤
│ rung-exports-{env}       │ Data exports [ePHI] - Client encrypted           │
└──────────────────────────┴──────────────────────────────────────────────────┘
```

---

## 6. External Integration Boundaries

### 6.1 AWS Services (BAA Covered)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AWS HIPAA-Eligible Services                          │
│                              (BAA Required)                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐            │
│   │  Bedrock  │   │Transcribe │   │    RDS    │   │    S3     │            │
│   │  [PHI OK] │   │  Medical  │   │  [ePHI]   │   │  [ePHI]   │            │
│   └───────────┘   │  [PHI OK] │   └───────────┘   └───────────┘            │
│                   └───────────┘                                             │
│   ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐            │
│   │   KMS     │   │ CloudWatch│   │  Cognito  │   │  Lambda   │            │
│   │  [Keys]   │   │  [Logs]   │   │  [Auth]   │   │ [Compute] │            │
│   └───────────┘   └───────────┘   └───────────┘   └───────────┘            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                         VPC Endpoints Only
                                    │
                                    v
```

### 6.2 External Services (No PHI)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         External Services (NO PHI)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │                         ANONYMIZATION BARRIER                      │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                    │                                        │
│                                    v                                        │
│   ┌───────────┐                              ┌───────────┐                 │
│   │ Perplexity│   [ANON queries only]        │   Slack   │  [No PHI]      │
│   │   Labs    │                              │Notifications               │
│   └───────────┘                              └───────────┘                 │
│                                                                              │
│   Examples of blocked queries:                                              │
│   - "John mentioned attachment anxiety" -> BLOCKED                         │
│   - "Patient discussed childhood trauma on Monday" -> BLOCKED              │
│                                                                              │
│   Examples of allowed queries:                                              │
│   - "Evidence-based interventions for attachment anxiety" -> OK            │
│   - "Therapeutic techniques for avoidant patterns" -> OK                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Access Control Matrix

### 7.1 Role-Based Data Access

| Data Type | Therapist | Client | Admin | Support |
|-----------|-----------|--------|-------|---------|
| Own client records | R/W | - | R | - |
| Own client guide | - | R | R | - |
| Voice memos | R/W | W | R | - |
| Clinical briefs | R/W | - | R | - |
| Merged frameworks | R/W | - | R | - |
| Audit logs | - | - | R | R (sanitized) |
| System config | - | - | R/W | R |

### 7.2 Service-to-Service Access

| Source | Destination | Data Type | Authorization |
|--------|-------------|-----------|---------------|
| API GW | Lambda | Request | Cognito token |
| Lambda | RDS | ePHI | IAM role |
| Lambda | S3 | ePHI | IAM role |
| n8n | Bedrock | PHI | IAM role + VPC |
| n8n | RDS | ePHI | IAM role + VPC |
| Anonymizer | Perplexity | ANON | API key |

---

## Appendix A: Network Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS VPC (10.0.0.0/16)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────────────────┐   ┌─────────────────────────────┐        │
│   │     Public Subnet A         │   │     Public Subnet B         │        │
│   │     (10.0.101.0/24)         │   │     (10.0.102.0/24)         │        │
│   │                             │   │                             │        │
│   │   ┌───────────┐             │   │             ┌───────────┐   │        │
│   │   │    ALB    │             │   │             │    NAT    │   │        │
│   │   └───────────┘             │   │             └───────────┘   │        │
│   └─────────────────────────────┘   └─────────────────────────────┘        │
│                                                                              │
│   ┌─────────────────────────────┐   ┌─────────────────────────────┐        │
│   │     Private Subnet A        │   │     Private Subnet B        │        │
│   │     (10.0.1.0/24)           │   │     (10.0.2.0/24)           │        │
│   │                             │   │                             │        │
│   │   ┌───────────┐             │   │             ┌───────────┐   │        │
│   │   │  Lambda   │             │   │             │    RDS    │   │        │
│   │   │   n8n     │             │   │             │  (Multi-AZ)│  │        │
│   │   └───────────┘             │   │             └───────────┘   │        │
│   └─────────────────────────────┘   └─────────────────────────────┘        │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────┐      │
│   │                       VPC Endpoints                              │      │
│   │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │      │
│   │   │ Bedrock │  │   S3    │  │Transcribe│ │CloudWatch│          │      │
│   │   └─────────┘  └─────────┘  └─────────┘  └─────────┘           │      │
│   └─────────────────────────────────────────────────────────────────┘      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Appendix B: Encryption Key Hierarchy

```
                    ┌─────────────────────┐
                    │   rung-master-key   │
                    │       (CMK)         │
                    │   Annual Rotation   │
                    └─────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          v                   v                   v
   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
   │rung-rds-key │     │rung-s3-key  │     │rung-field-  │
   │   (RDS)     │     │   (S3)      │     │    key      │
   │             │     │             │     │(Field-level)│
   └─────────────┘     └─────────────┘     └─────────────┘
          │                   │                   │
          v                   v                   v
   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
   │  Database   │     │   Bucket    │     │   Column    │
   │  Encryption │     │  Encryption │     │  Encryption │
   └─────────────┘     └─────────────┘     └─────────────┘
```
