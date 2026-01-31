# Rung Implementation Blueprint

## Project Overview
- **Project**: Rung Psychology Agent Orchestration System
- **Start Date**: TBD
- **Target Completion**: 20 weeks from start
- **Status**: Design Complete, Implementation Pending

---

## Phase Tracking

### Phase 1: Foundation (Weeks 1-4)
**Status**: Not Started
**Estimated Duration**: 4 weeks

#### Week 1: Infrastructure Provisioning
- [ ] Create VPC with public/private subnets (us-east-1)
- [ ] Deploy RDS PostgreSQL (db.r6g.large, Multi-AZ, encrypted)
- [ ] Create S3 buckets (voice-memos, transcripts, exports, n8n-data)
- [ ] Configure Cognito user pool with MFA
- [ ] Create KMS keys (master, rds, s3, perceptor)
- [ ] Set up NAT Gateway for Lambda egress
- [ ] Verify all encryption configurations

#### Week 2: Database Schema
- [ ] Create all core tables (therapists, clients, sessions, agents)
- [ ] Create workflow output tables (clinical_briefs, client_guides, development_plans)
- [ ] Create couples tables (couple_links, framework_merges)
- [ ] Create audit_logs table
- [ ] Create all indexes
- [ ] Deploy encryption/decryption functions
- [ ] Run initial test data insertion
- [ ] Verify encrypted fields store/retrieve correctly

#### Week 3: Basic API
- [ ] Deploy API Gateway with custom domain
- [ ] Create Lambda authorizer (Cognito JWT validation)
- [ ] Implement /clients CRUD endpoints
- [ ] Implement /sessions CRUD endpoints
- [ ] Configure CORS
- [ ] Set up rate limiting
- [ ] Create Postman collection
- [ ] Verify audit logging on all endpoints

#### Week 4: n8n Deployment
- [ ] Launch EC2 instance for n8n (t3.medium, private subnet)
- [ ] Configure n8n with PostgreSQL backend
- [ ] Set up ALB with SSL termination
- [ ] Configure Slack integration
- [ ] Create health check workflow
- [ ] Test webhook triggering from API Gateway
- [ ] Document n8n access and credentials

**Phase 1 Completion Criteria**:
- [ ] All infrastructure tests pass (15 tests)
- [ ] All API tests pass (25 tests)
- [ ] Encryption verification tests pass
- [ ] n8n health check returns 200
- [ ] Slack notification received from test workflow

---

### Phase 2: Pre-Session Pipeline (Weeks 5-8)
**Status**: Not Started
**Estimated Duration**: 4 weeks
**Dependencies**: Phase 1 complete

#### Week 5: Voice Processing
- [ ] Create /sessions/{id}/voice-memo upload endpoint
- [ ] Implement client-side encryption before S3 upload
- [ ] Integrate AWS Transcribe Medical
- [ ] Implement transcription job polling
- [ ] Store transcripts encrypted in S3
- [ ] Create transcript retrieval endpoint
- [ ] Test with 5-minute voice memo (target: <3 min processing)

#### Week 6: Rung Agent
- [ ] Define Rung system prompt (clinical analysis focus)
- [ ] Implement Bedrock inference Lambda
- [ ] Create clinical analysis prompt template
- [ ] Implement framework extraction logic
- [ ] Implement pattern detection
- [ ] Implement risk flag identification
- [ ] Create output parsing and validation
- [ ] Test with sample transcripts

#### Week 7: Research Integration
- [ ] Implement query anonymization function
- [ ] Create Perplexity API integration Lambda
- [ ] Implement citation parsing
- [ ] Create citation storage in clinical_briefs
- [ ] Add response caching (non-PHI queries only)
- [ ] Verify no PHI in outbound Perplexity requests (security review)

#### Week 8: Pre-Session Workflow Complete
- [ ] Define Beth system prompt (client communication focus)
- [ ] Implement Beth agent Bedrock integration
- [ ] Create client guide generation logic
- [ ] Build complete n8n pre-session workflow
  - [ ] Webhook trigger node
  - [ ] JWT validation node
  - [ ] S3 fetch node
  - [ ] Transcription nodes (start, poll, retrieve)
  - [ ] Parallel processing (Perceptor, Rung, Perplexity)
  - [ ] Merge node
  - [ ] Dual output generation (Clinical Brief, Client Guide)
  - [ ] Storage nodes (RDS, Perceptor)
  - [ ] Slack notification node
- [ ] Create /sessions/{id}/pre-session/status endpoint
- [ ] Create /sessions/{id}/clinical-brief endpoint
- [ ] Create /sessions/{id}/client-guide endpoint
- [ ] End-to-end test (target: <5 min total)

**Phase 2 Completion Criteria**:
- [ ] Voice processing tests pass (10 tests)
- [ ] Rung agent tests pass (15 tests)
- [ ] Research integration tests pass
- [ ] Pre-session E2E test completes successfully
- [ ] Clinical brief matches expected format
- [ ] Client guide uses non-clinical language (manual review)
- [ ] Slack notification received on workflow completion

---

### Phase 3: Post-Session Pipeline (Weeks 9-11)
**Status**: Not Started
**Estimated Duration**: 3 weeks
**Dependencies**: Phase 2 complete

#### Week 9: Notes Processing
- [ ] Create /sessions/{id}/notes submission endpoint
- [ ] Implement notes encryption
- [ ] Create framework extraction from notes logic
- [ ] Implement modality detection
- [ ] Store frameworks in clinical_briefs table

#### Week 10: Development Planning
- [ ] Create sprint planning algorithm
- [ ] Implement SMART goal generation
- [ ] Create exercise recommendation engine
- [ ] Link exercises to identified frameworks
- [ ] Implement progress tracking model
- [ ] Create /clients/{id}/development-plan endpoint

#### Week 11: Post-Session Workflow
- [ ] Build complete n8n post-session workflow
  - [ ] Webhook trigger node
  - [ ] Notes encryption node
  - [ ] Framework extraction node
  - [ ] Plan loading node
  - [ ] Sprint planning node
  - [ ] Storage nodes (RDS)
  - [ ] Perceptor archive node
  - [ ] Slack notification node
- [ ] Create /sessions/{id}/post-session/status endpoint
- [ ] Implement Perceptor context saving
- [ ] Test longitudinal context retrieval
- [ ] End-to-end test (target: <3 min total)

**Phase 3 Completion Criteria**:
- [ ] Post-session E2E test completes successfully
- [ ] Perceptor integration tests pass
- [ ] Development plan generated matches expected format
- [ ] Context retrievable across sessions
- [ ] Workflow completes in <3 minutes

---

### Phase 4: Couples Merge (Weeks 12-14)
**Status**: Not Started
**Estimated Duration**: 3 weeks
**Dependencies**: Phase 3 complete

#### Week 12: Couple Linking
- [ ] Create /couples POST endpoint (link two clients)
- [ ] Implement validation (same therapist, different clients)
- [ ] Create couple_links table operations
- [ ] Implement link status management (active, paused, terminated)
- [ ] Create /couples/{linkId} GET endpoint

#### Week 13: Framework Isolation
- [ ] Create framework-only data extraction function
- [ ] Implement PHI stripping layer
- [ ] Create topic matching algorithm
- [ ] Build isolation verification tests
- [ ] Security review of isolation layer
- [ ] Document isolation rules

#### Week 14: Merge Workflow
- [ ] Build complete n8n couples-merge workflow
  - [ ] Webhook trigger node
  - [ ] Link validation node
  - [ ] Parallel framework fetch (Partner A, Partner B)
  - [ ] Topic matching node
  - [ ] Framework merge node (Rung agent)
  - [ ] Storage node (framework_merges table)
  - [ ] Audit logging node
  - [ ] Slack notification node
- [ ] Create /couples/{linkId}/merge POST endpoint
- [ ] Create /couples/{linkId}/merged-frameworks GET endpoint
- [ ] Implement comprehensive audit logging for merges
- [ ] End-to-end test with isolation verification

**Phase 4 Completion Criteria**:
- [ ] Couples isolation tests pass (ALL must pass)
- [ ] Couples merge E2E test completes successfully
- [ ] No PHI crosses client boundaries (security verification)
- [ ] Full audit trail exists for all merge operations
- [ ] Merged insights are clinically useful (manual review)

---

### Phase 5: Security & Compliance (Weeks 15-17)
**Status**: Not Started
**Estimated Duration**: 3 weeks
**Dependencies**: Phase 4 complete

#### Week 15: Audit System
- [ ] Verify all HIPAA-required events logged
- [ ] Implement CloudWatch Logs backup
- [ ] Configure 7-year retention policy
- [ ] Create audit log analysis queries
- [ ] Implement anomaly detection alerts
  - [ ] Failed auth attempts
  - [ ] PHI access outside business hours
  - [ ] Bulk PHI export
- [ ] Test alert triggering

#### Week 16: Security Testing
- [ ] Conduct penetration testing (external vendor)
- [ ] Run OWASP ZAP scan
- [ ] Review findings and prioritize
- [ ] Remediate all critical vulnerabilities
- [ ] Remediate all high vulnerabilities
- [ ] Document accepted medium vulnerabilities with mitigations
- [ ] Create security documentation

#### Week 17: HIPAA Compliance
- [ ] Complete HIPAA compliance checklist (45 controls)
- [ ] Execute AWS BAA
- [ ] Complete risk assessment document
- [ ] Create policies and procedures documentation
- [ ] Document all PHI data flows
- [ ] Review and sign off on compliance status

**Phase 5 Completion Criteria**:
- [ ] OWASP scan shows no critical/high findings
- [ ] All 45 HIPAA controls addressed
- [ ] AWS BAA executed and on file
- [ ] Risk assessment document complete
- [ ] Policies and procedures documented

---

### Phase 6: Production Readiness (Weeks 18-20)
**Status**: Not Started
**Estimated Duration**: 3 weeks
**Dependencies**: Phase 5 complete

#### Week 18: Performance
- [ ] Create load test scripts (k6)
- [ ] Run load tests (100 concurrent users)
- [ ] Identify and fix performance bottlenecks
- [ ] Optimize Lambda cold starts
- [ ] Optimize database queries
- [ ] Create capacity planning document
- [ ] Verify P95 latency <5s for workflows

#### Week 19: Disaster Recovery
- [ ] Create disaster recovery runbook
- [ ] Document RTO (target: <4 hours)
- [ ] Document RPO (target: <1 hour)
- [ ] Test RDS failover
- [ ] Test S3 cross-region replication (if configured)
- [ ] Execute full DR test
- [ ] Document DR test results

#### Week 20: Beta Launch
- [ ] Create therapist onboarding guide
- [ ] Create monitoring dashboards (CloudWatch)
- [ ] Create support runbooks
- [ ] Create feedback collection mechanism
- [ ] Onboard 3-5 beta therapists
- [ ] Monitor for first-week issues
- [ ] Collect and document feedback

**Phase 6 Completion Criteria**:
- [ ] Load tests pass (100 VUs, <5% error rate)
- [ ] DR test successful (recovery within 4 hours)
- [ ] 3-5 beta therapists onboarded
- [ ] No critical issues in first week
- [ ] Feedback mechanism operational

---

## Overall Completion Checklist

- [ ] Phase 1: Foundation - Complete
- [ ] Phase 2: Pre-Session Pipeline - Complete
- [ ] Phase 3: Post-Session Pipeline - Complete
- [ ] Phase 4: Couples Merge - Complete
- [ ] Phase 5: Security & Compliance - Complete
- [ ] Phase 6: Production Readiness - Complete
- [ ] All tests passing
- [ ] Documentation complete
- [ ] HIPAA compliance verified
- [ ] Beta therapists providing positive feedback

---

## Notes

### Key Dependencies
- AWS BAA must be executed before processing any real PHI
- n8n must be self-hosted (not cloud) for HIPAA coverage
- Perplexity queries must be anonymized (no BAA available)

### Risk Mitigation
- Couples merge isolation is CRITICAL - extra security review required
- Voice memo processing latency may exceed targets - consider async notification
- Perceptor MCP needs custom integration - allow buffer time

### Success Metrics
- Workflow completion time: <5 min (pre-session), <3 min (post-session)
- System availability: 99.9%
- Zero PHI breaches
- Beta therapist satisfaction: >4/5

---

*Last Updated: 2026-01-31*
