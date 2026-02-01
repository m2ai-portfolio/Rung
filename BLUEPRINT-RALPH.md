# Rung Implementation Blueprint - Ralph-Loop Optimized

## Overview

This blueprint is structured for Ralph-loop execution with:
- Clear completion promises per phase
- Measurable success criteria
- Self-correction mechanisms (TDD)
- Safety escape hatches
- Git checkpoints

**Total Phases**: 6 major phases, broken into sub-phases for context management
**Estimated Total**: 20 weeks

---

## Pre-Flight Checklist

Before starting any Ralph-loop:
- [ ] AWS credentials configured
- [ ] Python 3.11+ installed
- [ ] Terraform 1.5+ installed
- [ ] Docker available for local testing
- [ ] `.env.example` exists with required variables

---

## Phase 1: Infrastructure Foundation

### Phase 1A: VPC and Network (Ralph-Loop Ready)

```bash
/ralph-loop "
Phase 1A: Create AWS VPC infrastructure for HIPAA-compliant Rung system.

REQUIREMENTS:
1. VPC with CIDR 10.0.0.0/16 in us-east-1
2. 2 private subnets (10.0.1.0/24, 10.0.2.0/24) - different AZs
3. 2 public subnets (10.0.101.0/24, 10.0.102.0/24) - different AZs
4. NAT Gateway in public subnet for Lambda egress
5. VPC Endpoint for Bedrock (interface endpoint)
6. VPC Endpoint for S3 (gateway endpoint)
7. Security groups:
   - rung-lambda-sg: outbound to Bedrock, RDS, S3
   - rung-rds-sg: inbound from Lambda SG only
   - rung-n8n-sg: inbound 443 from ALB, outbound to Bedrock/RDS

DELIVERABLES:
- terraform/modules/vpc/main.tf
- terraform/modules/vpc/variables.tf
- terraform/modules/vpc/outputs.tf
- terraform/environments/dev/vpc.tf
- Tests that verify:
  - VPC created with correct CIDR
  - Subnets in different AZs
  - NAT Gateway functional
  - VPC Endpoints reachable

SELF-CORRECTION:
- Run 'terraform validate' after each change
- Run 'terraform plan' to verify no errors
- If plan fails, fix and retry
- Run tests with 'pytest tests/infra/test_vpc.py -v'

After 20 iterations without completion:
- Document blockers in BLOCKERS.md
- List approaches attempted
- Output: <promise>BLOCKED_1A</promise>

When all requirements met and tests pass:
Output: <promise>PHASE_1A_COMPLETE</promise>
" --max-iterations 25 --completion-promise "PHASE_1A_COMPLETE"
```

**Checkpoint**: `git commit -m "feat(infra): Phase 1A - VPC infrastructure complete"`

---

### Phase 1B: Database and Encryption (Ralph-Loop Ready)

```bash
/ralph-loop "
Phase 1B: Create RDS PostgreSQL with encryption for Rung system.

REQUIREMENTS:
1. RDS PostgreSQL 15 instance (db.r6g.large)
2. Multi-AZ deployment
3. Encrypted storage (KMS managed key)
4. Database name: rung
5. Username from AWS Secrets Manager
6. Password from AWS Secrets Manager
7. Subnet group using private subnets from Phase 1A
8. KMS key hierarchy:
   - rung-master-key (CMK)
   - rung-rds-key (for RDS encryption)
   - rung-s3-key (for S3 encryption)
   - rung-field-key (for field-level encryption)

DELIVERABLES:
- terraform/modules/rds/main.tf
- terraform/modules/rds/variables.tf
- terraform/modules/rds/outputs.tf
- terraform/modules/kms/main.tf
- terraform/modules/kms/variables.tf
- terraform/modules/kms/outputs.tf
- Tests that verify:
  - RDS instance is encrypted
  - Multi-AZ is enabled
  - Security group allows only Lambda access
  - KMS keys created with correct policies

SELF-CORRECTION:
- Run 'terraform validate' after each change
- Run 'terraform plan' to verify no errors
- Test database connectivity from Lambda context
- Run 'pytest tests/infra/test_rds.py -v'

After 20 iterations without completion:
- Document blockers in BLOCKERS.md
- Output: <promise>BLOCKED_1B</promise>

When all requirements met and tests pass:
Output: <promise>PHASE_1B_COMPLETE</promise>
" --max-iterations 25 --completion-promise "PHASE_1B_COMPLETE"
```

**Checkpoint**: `git commit -m "feat(infra): Phase 1B - RDS and KMS encryption complete"`

---

### Phase 1C: S3 and Cognito (Ralph-Loop Ready)

```bash
/ralph-loop "
Phase 1C: Create S3 buckets and Cognito user pool for Rung.

REQUIREMENTS:
1. S3 Buckets (all encrypted with rung-s3-key):
   - rung-voice-memos-{env}: voice memo uploads
   - rung-transcripts-{env}: transcription output
   - rung-exports-{env}: data export requests
   - Versioning enabled
   - Lifecycle rules: 90 day transition to Glacier
   - Block public access

2. Cognito User Pool:
   - Name: rung-therapists-{env}
   - MFA required (TOTP)
   - Password policy: 12+ chars, mixed case, numbers, symbols
   - Email verification required
   - Custom attributes: practice_id, role

3. Cognito App Client:
   - Generate client secret
   - OAuth 2.0 flows: authorization_code, refresh_token
   - Callback URLs configurable

DELIVERABLES:
- terraform/modules/s3/main.tf
- terraform/modules/cognito/main.tf
- Tests that verify:
  - Buckets encrypted and versioned
  - Public access blocked
  - Cognito MFA enforced
  - Token generation works

SELF-CORRECTION:
- Run 'terraform validate' after each change
- Verify bucket policies with 'aws s3api get-bucket-policy'
- Test Cognito with sample user creation
- Run 'pytest tests/infra/test_s3_cognito.py -v'

After 20 iterations without completion:
- Document blockers in BLOCKERS.md
- Output: <promise>BLOCKED_1C</promise>

When all requirements met and tests pass:
Output: <promise>PHASE_1C_COMPLETE</promise>
" --max-iterations 25 --completion-promise "PHASE_1C_COMPLETE"
```

**Checkpoint**: `git commit -m "feat(infra): Phase 1C - S3 and Cognito complete"`

---

### Phase 1D: Database Schema (Ralph-Loop Ready)

```bash
/ralph-loop "
Phase 1D: Create database schema for Rung system.

REQUIREMENTS:
Create the following tables with proper relationships:

1. therapists
   - id (UUID PK)
   - cognito_sub (VARCHAR, unique)
   - email_encrypted (BYTEA)
   - practice_name (VARCHAR)
   - created_at, updated_at

2. clients
   - id (UUID PK)
   - therapist_id (FK -> therapists)
   - name_encrypted (BYTEA)
   - contact_encrypted (BYTEA)
   - consent_status (ENUM: pending, active, revoked)
   - consent_date (TIMESTAMP)
   - created_at, updated_at

3. sessions
   - id (UUID PK)
   - client_id (FK -> clients)
   - session_type (ENUM: individual, couples)
   - session_date (TIMESTAMP)
   - status (ENUM: scheduled, in_progress, completed, cancelled)
   - notes_encrypted (BYTEA)
   - created_at, updated_at

4. agents
   - id (UUID PK)
   - name (VARCHAR: 'rung' or 'beth')
   - client_id (FK -> clients)
   - system_prompt (TEXT)
   - created_at, updated_at

5. clinical_briefs
   - id (UUID PK)
   - session_id (FK -> sessions)
   - agent_id (FK -> agents, must be 'rung')
   - content_encrypted (BYTEA)
   - frameworks_identified (JSONB)
   - risk_flags (JSONB)
   - research_citations (JSONB)
   - created_at

6. client_guides
   - id (UUID PK)
   - session_id (FK -> sessions)
   - agent_id (FK -> agents, must be 'beth')
   - content_encrypted (BYTEA)
   - key_points (JSONB)
   - exercises_suggested (JSONB)
   - created_at

7. development_plans
   - id (UUID PK)
   - client_id (FK -> clients)
   - sprint_number (INT)
   - goals (JSONB)
   - exercises (JSONB)
   - progress (JSONB)
   - created_at, updated_at

8. couple_links
   - id (UUID PK)
   - partner_a_id (FK -> clients)
   - partner_b_id (FK -> clients)
   - therapist_id (FK -> therapists)
   - status (ENUM: active, paused, terminated)
   - created_at, updated_at
   - CONSTRAINT: partner_a_id < partner_b_id (prevent duplicates)

9. framework_merges
   - id (UUID PK)
   - couple_link_id (FK -> couple_links)
   - session_id (FK -> sessions)
   - partner_a_frameworks (JSONB) -- abstracted only
   - partner_b_frameworks (JSONB) -- abstracted only
   - merged_insights (JSONB)
   - created_at

10. audit_logs
    - id (UUID PK)
    - event_type (VARCHAR)
    - user_id (UUID, nullable)
    - resource_type (VARCHAR)
    - resource_id (UUID)
    - action (VARCHAR)
    - ip_address (VARCHAR)
    - user_agent (TEXT)
    - details (JSONB)
    - created_at

DELIVERABLES:
- src/db/migrations/001_initial_schema.sql
- src/db/migrations/002_indexes.sql
- src/models/therapist.py (Pydantic + SQLAlchemy)
- src/models/client.py
- src/models/session.py
- src/models/clinical_brief.py
- src/models/client_guide.py
- src/models/couple_link.py
- src/models/framework_merge.py
- src/models/audit_log.py
- Tests for all models (CRUD operations)

SELF-CORRECTION:
- Run migrations on test database
- Verify foreign key constraints
- Test encryption/decryption round-trip
- Run 'pytest tests/db/ -v'

After 20 iterations without completion:
- Document blockers in BLOCKERS.md
- Output: <promise>BLOCKED_1D</promise>

When all requirements met and tests pass:
Output: <promise>PHASE_1D_COMPLETE</promise>
" --max-iterations 30 --completion-promise "PHASE_1D_COMPLETE"
```

**Checkpoint**: `git commit -m "feat(db): Phase 1D - Database schema complete"`

---

## Phase 2: Pre-Session Pipeline

### Phase 2A: Voice Processing (Ralph-Loop Ready)

```bash
/ralph-loop "
Phase 2A: Implement voice memo upload and transcription.

REQUIREMENTS:
1. API endpoint: POST /sessions/{session_id}/voice-memo
   - Accept multipart form upload
   - Validate session exists and user has access
   - Client-side encrypt before S3 upload
   - Trigger AWS Transcribe Medical job
   - Return job_id for polling

2. API endpoint: GET /sessions/{session_id}/transcription/status
   - Return transcription job status
   - When complete, return transcript (encrypted)

3. API endpoint: GET /sessions/{session_id}/transcript
   - Return decrypted transcript content
   - Audit log the access

4. Lambda functions:
   - voice_upload_handler
   - transcription_status_handler
   - transcript_retrieval_handler

5. Integration with AWS Transcribe Medical:
   - Use medical vocabulary
   - Speaker diarization enabled
   - Output to rung-transcripts bucket

DELIVERABLES:
- src/api/voice_memo.py
- src/services/transcription.py
- src/lambdas/voice_upload.py
- src/lambdas/transcription_status.py
- src/lambdas/transcript_retrieval.py
- terraform/modules/transcribe/main.tf
- Tests:
  - Unit tests for all handlers
  - Integration test with sample audio
  - Security test: unauthorized access blocked

SELF-CORRECTION:
- Run unit tests after each function
- Test with real audio file (5 min max)
- Verify encryption in S3
- Verify audit log entry created
- Run 'pytest tests/voice/ -v'

After 25 iterations without completion:
- Document blockers in BLOCKERS.md
- Output: <promise>BLOCKED_2A</promise>

When all requirements met and tests pass:
Output: <promise>PHASE_2A_COMPLETE</promise>
" --max-iterations 30 --completion-promise "PHASE_2A_COMPLETE"
```

**Checkpoint**: `git commit -m "feat(voice): Phase 2A - Voice processing complete"`

---

### Phase 2B: Rung Agent (Ralph-Loop Ready)

```bash
/ralph-loop "
Phase 2B: Implement Rung clinical analysis agent.

REQUIREMENTS:
1. Rung System Prompt:
   - Role: Clinical analyst for therapist support
   - Identify psychological frameworks in client input
   - Detect defense mechanisms
   - Flag risk indicators
   - Output structured JSON

2. Framework Taxonomy (implement detection for):
   - Attachment patterns (secure, anxious, avoidant, disorganized)
   - Defense mechanisms (intellectualization, projection, denial, etc.)
   - Communication patterns (Gottman: criticism, contempt, defensiveness, stonewalling)
   - Relationship dynamics (pursuer-distancer, parent-child, etc.)

3. Bedrock Integration:
   - Use Claude 3.5 Sonnet via Bedrock
   - Max tokens: 4096
   - Temperature: 0.3 (clinical consistency)
   - Structured output parsing

4. Output Schema:
   {
     'frameworks_identified': [{'name': str, 'confidence': float, 'evidence': str}],
     'defense_mechanisms': [{'type': str, 'indicators': [str]}],
     'risk_flags': [{'level': 'low|medium|high', 'description': str}],
     'key_themes': [str],
     'suggested_exploration': [str],
     'session_questions': [str]
   }

DELIVERABLES:
- src/agents/rung.py
- src/agents/prompts/rung_system.txt
- src/agents/schemas/rung_output.py
- src/services/bedrock_client.py
- Tests:
  - Unit tests for output parsing
  - Integration test with Bedrock
  - Framework detection accuracy tests
  - Risk flag detection tests

SELF-CORRECTION:
- Test with sample transcripts
- Verify output matches schema
- Check framework detection accuracy
- Run 'pytest tests/agents/test_rung.py -v'

After 25 iterations without completion:
- Document blockers in BLOCKERS.md
- Output: <promise>BLOCKED_2B</promise>

When all requirements met and tests pass:
Output: <promise>PHASE_2B_COMPLETE</promise>
" --max-iterations 30 --completion-promise "PHASE_2B_COMPLETE"
```

**Checkpoint**: `git commit -m "feat(agent): Phase 2B - Rung agent complete"`

---

### Phase 2C: Research Integration (Ralph-Loop Ready)

```bash
/ralph-loop "
Phase 2C: Implement Perplexity research integration with anonymization.

REQUIREMENTS:
1. Query Anonymization Layer:
   - Strip all proper nouns
   - Remove dates and locations
   - Replace specific details with generic terms
   - Validation: reject queries that fail anonymization check

2. Perplexity Integration:
   - API client with rate limiting
   - Query construction from Rung output
   - Citation parsing
   - Response caching (non-PHI queries only)

3. Query Templates:
   - 'evidence-based interventions for {framework}'
   - 'therapeutic techniques for {pattern}'
   - 'research on {defense_mechanism} in couples therapy'

4. Output Schema:
   {
     'query': str,
     'anonymized_query': str,
     'citations': [{'title': str, 'source': str, 'summary': str}],
     'key_findings': [str],
     'recommended_techniques': [str]
   }

DELIVERABLES:
- src/services/anonymizer.py
- src/services/perplexity_client.py
- src/services/research.py
- Tests:
  - Anonymization tests (CRITICAL)
  - PHI detection tests
  - Perplexity integration tests
  - Cache behavior tests

CRITICAL: NO PHI must reach Perplexity API
- Test with known PHI patterns
- Fail-safe: block suspicious queries

SELF-CORRECTION:
- Run anonymization tests first
- Verify no PHI in outbound queries
- Test with sample Rung outputs
- Run 'pytest tests/research/ -v'

After 20 iterations without completion:
- Document blockers in BLOCKERS.md
- Output: <promise>BLOCKED_2C</promise>

When all requirements met and tests pass:
Output: <promise>PHASE_2C_COMPLETE</promise>
" --max-iterations 25 --completion-promise "PHASE_2C_COMPLETE"
```

**Checkpoint**: `git commit -m "feat(research): Phase 2C - Research integration complete"`

---

### Phase 2D: Beth Agent and Pre-Session Workflow (Ralph-Loop Ready)

```bash
/ralph-loop "
Phase 2D: Implement Beth agent and complete pre-session n8n workflow.

REQUIREMENTS:
1. Beth System Prompt:
   - Role: Client communication specialist
   - Convert clinical insights to accessible language
   - NO clinical jargon
   - Friendly, supportive tone
   - Focus on practical preparation

2. Beth Input (from Rung abstraction layer - NOT raw Rung output):
   {
     'themes': [str],  -- generalized themes only
     'exploration_areas': [str],
     'session_focus': str
   }

3. Beth Output Schema:
   {
     'session_prep': str,  -- conversational preparation guide
     'discussion_points': [str],  -- things to consider
     'reflection_questions': [str],  -- self-reflection prompts
     'exercises': [str]  -- optional exercises before session
   }

4. Abstraction Layer (CRITICAL):
   - Extract themes from Rung output
   - Strip clinical terminology
   - Remove defense mechanism labels
   - Remove risk flags (therapist only)

5. n8n Pre-Session Workflow:
   - Webhook trigger (from API)
   - Fetch voice memo from S3
   - Trigger/poll transcription
   - Load Perceptor context (agent-specific)
   - Call Rung agent (Bedrock)
   - Call Perplexity research
   - Abstraction layer (for Beth)
   - Call Beth agent (Bedrock)
   - Generate dual output:
     - Clinical Brief (therapist)
     - Client Guide (client)
   - Store in database
   - Archive to Perceptor
   - Slack notification

DELIVERABLES:
- src/agents/beth.py
- src/agents/prompts/beth_system.txt
- src/agents/schemas/beth_output.py
- src/services/abstraction_layer.py
- n8n/workflows/pre_session.json
- src/api/pre_session.py (status, clinical-brief, client-guide endpoints)
- Tests:
  - Beth output quality tests
  - Abstraction layer isolation tests (CRITICAL)
  - E2E workflow test
  - Dual output generation tests

CRITICAL: Beth must NEVER receive raw Rung output
- Abstraction layer tests must all pass
- Verify no clinical terminology in Beth output

SELF-CORRECTION:
- Test abstraction layer isolation
- Verify Beth output is client-friendly
- Run full workflow test
- Run 'pytest tests/e2e/test_pre_session.py -v'

After 30 iterations without completion:
- Document blockers in BLOCKERS.md
- Output: <promise>BLOCKED_2D</promise>

When all requirements met and tests pass:
Output: <promise>PHASE_2D_COMPLETE</promise>
" --max-iterations 40 --completion-promise "PHASE_2D_COMPLETE"
```

**Checkpoint**: `git commit -m "feat(workflow): Phase 2D - Pre-session pipeline complete"`

---

## Phase 3: Post-Session Pipeline

### Phase 3A: Notes Processing and Framework Extraction

```bash
/ralph-loop "
Phase 3A: Implement post-session notes processing.

REQUIREMENTS:
1. API endpoint: POST /sessions/{session_id}/notes
   - Accept session notes (text)
   - Encrypt before storage
   - Trigger post-session workflow
   - Return processing status

2. Framework Extraction from Notes:
   - Identify frameworks discussed
   - Extract homework assigned
   - Note modalities used (CBT, DBT, EFT, etc.)
   - Identify breakthrough moments
   - Track client progress indicators

3. Output Schema:
   {
     'frameworks_discussed': [str],
     'modalities_used': [str],
     'homework_assigned': [{'task': str, 'due': str}],
     'breakthroughs': [str],
     'progress_indicators': [str],
     'areas_for_next_session': [str]
   }

DELIVERABLES:
- src/api/post_session.py
- src/services/notes_processor.py
- src/services/framework_extractor.py
- Tests:
  - Notes encryption tests
  - Framework extraction accuracy
  - API endpoint tests

SELF-CORRECTION:
- Test with sample session notes
- Verify encryption round-trip
- Check extraction accuracy
- Run 'pytest tests/post_session/ -v'

When all requirements met and tests pass:
Output: <promise>PHASE_3A_COMPLETE</promise>
" --max-iterations 25 --completion-promise "PHASE_3A_COMPLETE"
```

---

### Phase 3B: Development Planning and Perceptor

```bash
/ralph-loop "
Phase 3B: Implement development planning and Perceptor integration.

REQUIREMENTS:
1. Sprint Planning Algorithm:
   - Analyze extracted frameworks
   - Generate SMART goals
   - Recommend exercises based on frameworks
   - Create 1-2 week sprint plan
   - Track cumulative progress

2. Perceptor Integration:
   - Save context after each session
   - Tag structure: [agent, stage, session-date, client-id]
   - Retrieve historical context for pattern analysis
   - Enable longitudinal tracking

3. Development Plan Output:
   {
     'sprint_number': int,
     'duration_days': int,
     'goals': [{'goal': str, 'metric': str, 'target': str}],
     'exercises': [{'name': str, 'frequency': str, 'description': str}],
     'reflection_prompts': [str],
     'progress_from_last_sprint': str
   }

4. n8n Post-Session Workflow:
   - Webhook trigger
   - Fetch session notes
   - Extract frameworks
   - Load development plan history
   - Generate new sprint plan
   - Store in database
   - Archive to Perceptor
   - Slack notification

DELIVERABLES:
- src/services/sprint_planner.py
- src/services/perceptor_client.py
- n8n/workflows/post_session.json
- src/api/development_plan.py
- Tests:
  - Sprint planning tests
  - Perceptor save/load tests
  - Longitudinal context retrieval
  - E2E post-session workflow

SELF-CORRECTION:
- Test sprint planning with history
- Verify Perceptor context retrieval
- Run full workflow test
- Run 'pytest tests/e2e/test_post_session.py -v'

When all requirements met and tests pass:
Output: <promise>PHASE_3B_COMPLETE</promise>
" --max-iterations 30 --completion-promise "PHASE_3B_COMPLETE"
```

**Checkpoint**: `git commit -m "feat(workflow): Phase 3 - Post-session pipeline complete"`

---

## Phase 4: Couples Merge

### Phase 4A: Couple Linking and Isolation Layer

```bash
/ralph-loop "
Phase 4A: Implement couple linking and framework isolation.

REQUIREMENTS:
1. Couple Linking API:
   - POST /couples (link two clients)
   - GET /couples/{link_id}
   - PATCH /couples/{link_id} (update status)
   - Validation: same therapist, different clients

2. Framework Isolation Layer (CRITICAL):
   - Extract ONLY framework-level data
   - Strip all specific content
   - Remove quotes, incidents, emotions
   - Output only pattern names and categories

3. Isolation Rules:
   ALLOWED:
   - Pattern category names ('attachment anxiety')
   - Framework references ('Gottman Four Horsemen')
   - Theme categories ('communication', 'intimacy', 'trust')

   PROHIBITED:
   - Direct quotes from sessions
   - Specific incidents
   - Emotional content details
   - Dates or timeline specifics

4. Topic Matching:
   - Identify overlapping themes between partners
   - Find complementary patterns
   - Detect potential conflict areas

DELIVERABLES:
- src/api/couples.py
- src/services/couple_manager.py
- src/services/isolation_layer.py
- src/services/topic_matcher.py
- Tests:
  - Couple linking tests
  - Isolation layer tests (CRITICAL - 100% coverage)
  - No PHI crossing boundaries (security tests)
  - Topic matching accuracy

CRITICAL: This phase requires extra security review
- All isolation tests must pass
- Conduct manual review of isolation logic

SELF-CORRECTION:
- Run isolation tests first
- Verify no specific content in output
- Test with adversarial inputs
- Run 'pytest tests/security/test_couples_isolation.py -v --strict'

When all requirements met and ALL security tests pass:
Output: <promise>PHASE_4A_COMPLETE</promise>
" --max-iterations 35 --completion-promise "PHASE_4A_COMPLETE"
```

---

### Phase 4B: Couples Merge Workflow

```bash
/ralph-loop "
Phase 4B: Implement couples merge workflow.

REQUIREMENTS:
1. Merge API:
   - POST /couples/{link_id}/merge (trigger merge)
   - GET /couples/{link_id}/merged-frameworks

2. Merge Workflow (n8n):
   - Trigger on couples session scheduling
   - Fetch partner A frameworks (isolated)
   - Fetch partner B frameworks (isolated)
   - Match topics
   - Generate merged insights (Rung agent)
   - Store in framework_merges table
   - Comprehensive audit logging
   - Slack notification

3. Merged Output Schema:
   {
     'couple_link_id': str,
     'session_id': str,
     'partner_a_frameworks': [str],  -- names only
     'partner_b_frameworks': [str],  -- names only
     'overlapping_themes': [str],
     'complementary_patterns': [str],
     'suggested_focus_areas': [str],
     'couples_exercises': [str]
   }

4. Audit Requirements:
   - Log every merge operation
   - Record what data was accessed
   - Track isolation layer invocations
   - Enable forensic review

DELIVERABLES:
- n8n/workflows/couples_merge.json
- src/services/merge_engine.py
- src/api/merged_frameworks.py
- Tests:
  - Merge workflow E2E test
  - Audit log completeness test
  - Isolation verification test
  - Clinical utility review (manual)

SELF-CORRECTION:
- Verify audit logs capture all operations
- Test with both partners having different frameworks
- Verify no PHI in merged output
- Run 'pytest tests/e2e/test_couples_merge.py -v'

When all requirements met and tests pass:
Output: <promise>PHASE_4B_COMPLETE</promise>
" --max-iterations 30 --completion-promise "PHASE_4B_COMPLETE"
```

**Checkpoint**: `git commit -m "feat(couples): Phase 4 - Couples merge complete"`

---

## Phase 5: Security & Compliance

```bash
/ralph-loop "
Phase 5: Security hardening and HIPAA compliance verification.

REQUIREMENTS:
1. Audit System:
   - All HIPAA-required events logged
   - CloudWatch Logs with 7-year retention
   - Anomaly detection alerts configured
   - Query templates for common investigations

2. Security Testing:
   - OWASP ZAP scan on all endpoints
   - Dependency vulnerability scan
   - Secret scanning in codebase
   - Remediate all critical/high findings

3. HIPAA Compliance Checklist (45 controls):
   - Access controls documented
   - Encryption verified (at rest + in transit)
   - Audit logging verified
   - Backup/recovery tested
   - Incident response documented
   - BAA execution confirmed

4. Documentation:
   - Security policies
   - Data flow diagrams with PHI markers
   - Access control matrix
   - Incident response plan
   - Risk assessment

DELIVERABLES:
- docs/security/policies.md
- docs/security/data_flows.md
- docs/security/incident_response.md
- docs/compliance/hipaa_checklist.md (all items checked)
- docs/compliance/risk_assessment.md
- terraform/modules/monitoring/alerts.tf
- Tests:
  - Penetration test results
  - OWASP scan results
  - Compliance verification tests

SELF-CORRECTION:
- Run security scans
- Verify all 45 HIPAA controls
- Fix any critical findings
- Run 'pytest tests/security/ -v'

When all requirements met and no critical findings:
Output: <promise>PHASE_5_COMPLETE</promise>
" --max-iterations 40 --completion-promise "PHASE_5_COMPLETE"
```

**Checkpoint**: `git commit -m "feat(security): Phase 5 - Security and compliance complete"`

---

## Phase 6: Production Readiness

```bash
/ralph-loop "
Phase 6: Production readiness and beta launch preparation.

REQUIREMENTS:
1. Performance:
   - Load tests (k6): 100 concurrent users
   - P95 latency < 5s for all workflows
   - Lambda cold start optimization
   - Database query optimization

2. Disaster Recovery:
   - RTO: < 4 hours
   - RPO: < 1 hour
   - DR runbook documented
   - Failover tested

3. Monitoring:
   - CloudWatch dashboards for all services
   - PagerDuty/Slack alerting
   - Runbooks for common issues

4. Beta Launch:
   - Therapist onboarding guide
   - Support documentation
   - Feedback collection mechanism
   - First 3-5 beta therapists onboarded

DELIVERABLES:
- docs/operations/runbooks/
- docs/onboarding/therapist_guide.md
- scripts/load_tests/
- terraform/modules/monitoring/dashboards.tf
- Tests:
  - Load test results (100 VUs, <5% error rate)
  - DR test results
  - Performance benchmarks

SELF-CORRECTION:
- Run load tests
- Execute DR test
- Verify all dashboards
- Run 'pytest tests/performance/ -v'

When all requirements met:
Output: <promise>PHASE_6_COMPLETE</promise>
" --max-iterations 35 --completion-promise "PHASE_6_COMPLETE"
```

**Checkpoint**: `git commit -m "feat(prod): Phase 6 - Production ready"`

---

## Summary

| Phase | Sub-Phase | Max Iterations | Promise | Status |
|-------|-----------|----------------|---------|--------|
| 1A | VPC/Network | 25 | PHASE_1A_COMPLETE | ✅ DONE |
| 1B | RDS/KMS | 25 | PHASE_1B_COMPLETE | ✅ DONE |
| 1C | S3/Cognito | 25 | PHASE_1C_COMPLETE | ✅ DONE |
| 1D | DB Schema | 30 | PHASE_1D_COMPLETE |
| 2A | Voice Processing | 30 | PHASE_2A_COMPLETE |
| 2B | Rung Agent | 30 | PHASE_2B_COMPLETE |
| 2C | Research | 25 | PHASE_2C_COMPLETE |
| 2D | Beth + Workflow | 40 | PHASE_2D_COMPLETE |
| 3A | Notes Processing | 25 | PHASE_3A_COMPLETE |
| 3B | Dev Planning | 30 | PHASE_3B_COMPLETE |
| 4A | Couple Isolation | 35 | PHASE_4A_COMPLETE |
| 4B | Merge Workflow | 30 | PHASE_4B_COMPLETE |
| 5 | Security | 40 | PHASE_5_COMPLETE |
| 6 | Production | 35 | PHASE_6_COMPLETE |

**Total Estimated API Cost**: $300-500 per full run (conservative estimate)

---

*Last Updated: 2026-01-31*
