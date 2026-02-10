# Rung Implementation Blueprint

## Project Overview
- **Project**: Rung Psychology Agent Orchestration System
- **Start Date**: 2026-01-31
- **Status**: Phase E (Documentation) - Pre-Production
- **Architecture**: Consolidated FastAPI + ECS Fargate (ADR-011)

---

## Phase Tracking

### Phase 0: Test Stabilization  ✅ **COMPLETE**
**Status**: Complete
**Estimated Duration**: 1 week
**Actual Duration**: 1 week

#### Completed Work
- [x] All pytest tests passing
- [x] SQLite test database working
- [x] Test isolation fixed (no cross-contamination)
- [x] Mock services for Bedrock/S3/Perplexity
- [x] Security/isolation tests passing

**Completion Criteria**: ✅ All tests passing with >80% coverage

---

### Phase A: Foundation (Encryption, Audit, Migrations)  ✅ **COMPLETE**
**Status**: Complete
**Estimated Duration**: 1 week
**Actual Duration**: 1 week

#### Week 1: Core Services
- [x] Implement KMS envelope encryption (`src/services/encryption.py`)
- [x] Create centralized audit service (`src/services/audit.py`)
- [x] Set up Alembic migrations (`src/db/alembic/`)
- [x] Create initial migration with all tables
- [x] Add encryption/decryption to model layer
- [x] Test encryption round-trip
- [x] Test audit logging for HIPAA events

**Completion Criteria**: ✅ Encryption, audit, and migrations functional

---

### Phase B: Pipeline Orchestration  ✅ **COMPLETE**
**Status**: Complete
**Estimated Duration**: 2 weeks
**Actual Duration**: 2 weeks

#### Week 1: Pre-Session Pipeline
- [x] Create `src/pipelines/base.py` (common pipeline utilities)
- [x] Implement `src/pipelines/pre_session.py`
  - [x] Fetch transcript from S3
  - [x] Run Rung agent + Research in parallel
  - [x] Abstract clinical output for Beth
  - [x] Generate client guide
  - [x] Store clinical_brief and client_guide
  - [x] Audit logging
- [x] Create FastAPI endpoint POST `/sessions/{id}/voice-memo`
- [x] Create FastAPI endpoint GET `/sessions/{id}/pre-session/status`
- [x] E2E tests for pre-session pipeline

#### Week 2: Post-Session & Couples Pipelines
- [x] Implement `src/pipelines/post_session.py`
  - [x] Load session notes
  - [x] Extract frameworks
  - [x] Generate development plan
  - [x] Store plan and update progress
- [x] Implement `src/pipelines/couples_merge.py`
  - [x] Validate couple link
  - [x] Fetch frameworks (isolation enforced)
  - [x] Topic matching
  - [x] Merge at framework level only
  - [x] Extra audit logging for couples
- [x] Create FastAPI endpoint POST `/sessions/{id}/notes`
- [x] Create FastAPI endpoint POST `/couples/{linkId}/merge`
- [x] E2E tests for all pipelines

**Completion Criteria**: ✅ All 3 pipelines functional with tests passing

---

### Phase C: Progress Analytics  ✅ **COMPLETE**
**Status**: Complete
**Estimated Duration**: 1 week
**Actual Duration**: 1 week

#### Week 1: Analytics Service
- [x] Create `src/services/progress_analytics.py`
  - [x] Calculate development trajectory
  - [x] Track framework usage over time
  - [x] Identify pattern shifts
  - [x] Generate progress summaries
- [x] Create `src/api/progress.py` endpoints
  - [x] GET `/clients/{id}/progress`
  - [x] GET `/clients/{id}/development-trajectory`
- [x] Add analytics to post-session pipeline
- [x] Tests for progress analytics service

**Completion Criteria**: ✅ Progress analytics integrated into post-session flow

---

### Phase D: Deployment Infrastructure  ✅ **COMPLETE**
**Status**: Complete
**Estimated Duration**: 1 week
**Actual Duration**: 1 week

#### Week 1: ECS Fargate Setup
- [x] Create Dockerfile for FastAPI application
- [x] Create Makefile for build/deploy commands
- [x] Create `terraform/modules/ecs/` for ECS Fargate
  - [x] ECS cluster
  - [x] Task definition (1 vCPU, 2 GB)
  - [x] Service with auto-scaling
  - [x] ALB integration
  - [x] CloudWatch logs
  - [x] ECR repository
- [x] Create `terraform/environments/dev/` configuration
- [x] Test local Docker build
- [x] Document deployment process (`DEPLOYMENT.md`)
- [x] Create deployment checklist (`DEPLOYMENT_CHECKLIST.md`)

**Completion Criteria**: ✅ Docker + ECS infrastructure ready for deployment

---

### Phase E: Documentation  ✅ **COMPLETE**
**Status**: Complete
**Estimated Duration**: 1 week

#### Week 1: Documentation Updates
- [x] Update `decisions.log` with ADR-011
- [x] Update `ARCHITECTURE.md` (added consolidation notice)
- [x] Update `BLUEPRINT.md` (this file - marked phases complete)
- [x] Update `CLAUDE.md` (technology stack, file structure)
- [x] Update `README.md` (quick start, architecture)
- [x] Update `AGENTS.md` (build/run/test instructions)
- [x] Review all documentation for accuracy
- [x] Add deprecation notes to `n8n.deprecated/DEPRECATED.md`
- [x] Create pipeline reference doc (PIPELINE_SECTION.md)

**Completion Criteria**:
- [x] All documentation reflects consolidated architecture
- [x] No references to n8n in active docs (except decisions.log history)
- [x] Makefile commands documented
- [x] ECS deployment process clear

---

### Phase E2: Reading List Feature  ✅ **COMPLETE**
**Status**: Complete
**Date**: 2026-02-09
**ADR**: ADR-012 (Reading List PHI Boundaries)

#### Implementation
- [x] Data model: `ReadingItem` SQLAlchemy model + Pydantic schemas (`src/models/reading_item.py`)
- [x] Alembic migration: `reading_items` table with indexes
- [x] Service layer: `ReadingListService` with encryption, audit, authorization (`src/services/reading_list.py`)
- [x] API endpoints: CRUD + assign + for-session (`src/api/reading_list.py`)
- [x] Pipeline integration: Reading context injected into Rung analysis request
- [x] Pipeline resilience: Reading service failure doesn't break pre-session pipeline
- [x] Soft delete: `deleted_at` column for HIPAA audit trail preservation
- [x] PHI encryption: Client notes and therapist assignment notes encrypted at rest
- [x] Audit logging: All PHI operations (create/read/update/delete) logged
- [x] Client isolation: Client A cannot access Client B's reading items
- [x] Therapist ownership: Therapist can only access owned client's items
- [x] Tests: 85 tests, 88% coverage (model 100%, service 86%, API 82%)

**Completion Criteria**:
- [x] All reading list tests passing
- [x] Encryption round-trip verified
- [x] Client isolation verified
- [x] Pipeline integration tested (with context, without context, failure resilience)
- [x] No regressions in existing tests

---

### Phase F: Production Deployment  ⚪ **NEXT**
**Status**: Not Started
**Estimated Duration**: 8-10 working days
**Dependencies**: Phase E2 complete
**Target Monthly Cost**: ~$130-170/month (right-sized for field test)

#### Infrastructure Sizing (Field Test: 1 Therapist, 1-2 Clients)

| Service | Size | Monthly Cost |
|---------|------|-------------|
| RDS PostgreSQL | db.t4g.micro, 20 GB gp3, single-AZ | ~$15 |
| ECS Fargate | 0.5 vCPU, 1 GB, 1 task | ~$18 |
| ALB | HTTPS (ACM cert) | ~$18 |
| NAT Gateway | Single | ~$35 |
| KMS Keys | 5 CMKs | ~$5 |
| VPC Endpoints | Bedrock + Bedrock Runtime | ~$16 |
| Bedrock (Claude 3.5 Sonnet) | ~8 sessions/month | ~$15-40 |
| Perplexity API | ~8 sessions/month | ~$5-20 |
| S3, CloudWatch, Route53, Secrets Manager, Cognito | Minimal | ~$5 |

#### Sub-Phase F0: Prerequisites (1-2 days)

Manual, non-automatable steps that block infrastructure provisioning.

- [ ] **F0.1** Execute AWS BAA — AWS Console → Artifact → Accept BAA (requires AWS Organizations)
- [ ] **F0.2** Request Bedrock model access — Claude 3.5 Sonnet in us-east-1 (24-48h approval)
- [ ] **F0.3** Domain decision — Choose API domain (e.g., `api.rung.app` or subdomain of existing)
- [ ] **F0.4** Request ACM SSL certificate — DNS validation for domain from F0.3 (free)
- [ ] **F0.5** Create Terraform state backend — S3 bucket (versioned, encrypted) + DynamoDB lock table
- [ ] **F0.6** Create `terraform/environments/prod/` — Copy from dev, adjust sizes/settings
- [ ] **F0.7** Create production Perplexity API key — Store in Secrets Manager
- [ ] **F0.8** Verify Slack webhook for notifications

#### Sub-Phase F1: Infrastructure Provisioning (3-4 days)

All Terraform-automatable. Dependency order: VPC → KMS → RDS/S3/Cognito → ALB → ECS → DNS.

- [ ] **F1.1** Create production VPC — 2 AZs, private/public subnets, single NAT gateway, VPC endpoints (S3 gateway + Bedrock interface), VPC flow logs (7-year retention)
- [ ] **F1.2** Create KMS keys — Master CMK, RDS key, S3 key, field encryption key, Secrets Manager key
- [ ] **F1.3** Deploy RDS PostgreSQL — db.t4g.micro, 20 GB gp3, single-AZ, 35-day backup retention, encryption (KMS), force SSL, deletion protection ON, skip final snapshot OFF
- [ ] **F1.4** Create S3 buckets — voice-memos, transcripts, exports; SSE-KMS encrypted, versioned, Glacier transition at 90 days
- [ ] **F1.5** Configure Cognito — deletion protection ACTIVE, admin-create-user only, MFA ON, production callback/logout URLs
- [ ] **F1.6** Deploy ALB with HTTPS — ACM certificate, HTTP→HTTPS redirect, deletion protection, access logs to S3
- [ ] **F1.7** Deploy ECS Fargate — 0.5 vCPU / 1 GB, desired count 1, max 2, CloudWatch log retention 2557 days (7 years)
- [ ] **F1.8** Configure Route53 DNS — Hosted zone + A record (alias) → ALB
- [ ] **F1.9** Create CloudWatch alarms — ECS CPU/memory, RDS CPU/storage/connections, ALB 5xx rate → SNS email
- [ ] **F1.10** Configure audit log retention — All log groups set to 2557 days (7 years) per HIPAA
- [ ] **F1.11** Store secrets in Secrets Manager — PERPLEXITY_API_KEY, SLACK_WEBHOOK_URL, app-level secrets
- [ ] **F1.12** Enable CloudTrail — Dedicated trail with S3 delivery for production account

#### Sub-Phase F2: Security Validation & Onboarding (3-4 days)

- [ ] **F2.1** Run dependency security audit — `pip audit` + `safety check`, fix critical/high vulnerabilities
- [ ] **F2.2** HIPAA technical safeguard verification:
  - [ ] Access Control (§164.312(a)): Cognito unique user IDs, 1-hour token expiry, KMS encryption
  - [ ] Audit Controls (§164.312(b)): Audit service logs all PHI access, 7-year CloudWatch retention, VPC flow logs
  - [ ] Integrity (§164.312(c)): S3 versioning, RDS backups, field-level encryption
  - [ ] Authentication (§164.312(d)): MFA enforced, strong password policy
  - [ ] Transmission Security (§164.312(e)): HTTPS enforced (ALB+ACM), RDS force_ssl, S3 HTTPS policy, VPC endpoints
- [ ] **F2.3** Perplexity anonymization audit — Review 5-10 sample Rung agent queries, verify zero PHI leakage
- [ ] **F2.4** Build and push Docker image — Tag `rung:v1.0.0`, push to production ECR
- [ ] **F2.5** Run Alembic migrations — `alembic upgrade head` against production RDS, verify schema
- [ ] **F2.6** First deploy to production ECS — Verify health check, verify `/docs` disabled in production
- [ ] **F2.7** Create Madeline's Cognito account — Admin-create-user, add to therapists group, MFA setup on first login
- [ ] **F2.8** Create Matthew as test client — POST `/clients` via API, verify encryption round-trip in production
- [ ] **F2.9** Smoke test: pre-session pipeline — Upload voice memo → Bedrock inference → Perplexity research → clinical brief encrypted → client guide encrypted → audit logs → Slack notification
- [ ] **F2.10** Smoke test: post-session pipeline — Submit session notes → development plan generated → progress analytics updated
- [ ] **F2.11** Create production runbook — Deploy, rollback, view logs, rotate credentials, create/disable users, emergency shutdown
- [ ] **F2.12** Backup/restore validation — Manual RDS snapshot → restore to new instance → verify data → delete test instance
- [ ] **F2.13** Onboard Madeline — Login flow, MFA setup, trigger pre-session workflow, find clinical brief

#### Explicitly Deferred (Not Needed for Field Test)

| Item | Rationale | Revisit When |
|------|-----------|-------------|
| Multi-AZ RDS | Doubles cost; 1-user system, single-AZ + backups sufficient | Paying users |
| Penetration testing | Cost prohibitive for solo project | Revenue or compliance audit |
| Load testing (k6) | 1 therapist, ~8 sessions/month; meaningless at this scale | 10+ concurrent users |
| Full 45-control HIPAA checklist | Many controls are administrative (policies, training); focus on technical safeguards | Pre-commercial launch |
| WAF on ALB | Cognito auth + security groups sufficient for 1 user | Public-facing API |
| Blue-green deployments | Rolling deploy with ECS circuit breaker sufficient | Multiple users relying on uptime |
| Automated credential rotation | Manual rotation acceptable for field test | Production hardening |

#### Known Security Gaps (Tracked)

| Gap | Severity | Mitigation |
|-----|----------|------------|
| ALB currently HTTP-only | **High** | Fixed in F1.6 — no PHI until HTTPS active |
| No CloudTrail | Medium | Fixed in F1.12 |
| Perplexity has no BAA | Medium | Anonymization layer (ADR-005) + audit in F2.3 |
| KMS policies reference Lambda (legacy) | Low | Update to reference ECS task role; not a security risk |
| Terraform state is local | Medium | Fixed in F0.5 |

**Completion Criteria**:
- [ ] Production infrastructure deployed and accessible via HTTPS
- [ ] HIPAA technical safeguards verified with evidence
- [ ] Perplexity anonymization audited (zero PHI in sample queries)
- [ ] Both pipelines smoke-tested end-to-end in production
- [ ] Madeline onboarded with MFA, first real session scheduled
- [ ] Backup restore validated
- [ ] No critical issues in first week of monitoring

---

### Phase G: Couples Module (Phase 2)  ⚪ **FUTURE**
**Status**: Not Started
**Timeline**: After successful solo therapy field test
**Dependencies**: Phase F complete + 4-6 solo sessions completed

#### Prerequisites
- [ ] Madeline + Matthew field test complete (Rung only)
- [ ] Framework extraction proven stable
- [ ] Isolation layer security reviewed
- [ ] Stacey onboarded as second client (Beth agent)

#### Implementation
- [ ] Activate couples_merge pipeline in production
- [ ] Create couple link (Matthew + Stacey)
- [ ] Execute first couples merge workflow
- [ ] Review merged frameworks with Madeline
- [ ] Verify isolation (no PHI cross-contamination)
- [ ] Monitor for 4-6 couples sessions

**Completion Criteria**:
- [ ] Couples merge produces clinically useful insights
- [ ] Zero isolation violations
- [ ] Therapist satisfaction with merged output

---

## Overall Completion Checklist

- [x] Phase 0: Test Stabilization
- [x] Phase A: Foundation (Encryption, Audit, Migrations)
- [x] Phase B: Pipeline Orchestration
- [x] Phase C: Progress Analytics
- [x] Phase D: Deployment Infrastructure
- [x] Phase E: Documentation
- [x] Phase E2: Reading List Feature
- [ ] Phase F: Production Deployment
  - [ ] F0: Prerequisites (BAA, Bedrock access, domain, ACM cert, TF state)
  - [ ] F1: Infrastructure Provisioning (VPC, RDS, S3, Cognito, ALB, ECS, DNS)
  - [ ] F2: Security Validation & Onboarding (HIPAA verification, smoke tests, Madeline onboard)
- [ ] Phase G: Couples Module (Phase 2)

---

## Architecture Notes

### Major Changes (ADR-011)
**Original Plan**: n8n on EC2 + Lambda handlers
**Current Reality**: Python async pipelines on ECS Fargate

**Rationale**:
- Single language (Python) for all security-critical code
- Eliminates split-brain (n8n JavaScript vs Python services)
- Reduces infrastructure cost (no EC2, ALB, PostgreSQL for n8n)
- Better HIPAA auditability (all code in one codebase)

**Migration Path**:
- n8n workflows → `src/pipelines/` (completed)
- Lambda handlers → FastAPI endpoints (completed)
- n8n files preserved in `n8n.deprecated/` for reference

### Key Components
| Component | Location | Status |
|-----------|----------|--------|
| Pipelines | `src/pipelines/` | ✅ Complete |
| API Endpoints | `src/api/` | ✅ Complete |
| Agents | `src/agents/` | ✅ Complete |
| Services | `src/services/` | ✅ Complete |
| Encryption | `src/services/encryption.py` | ✅ Complete |
| Audit | `src/services/audit.py` | ✅ Complete |
| Progress Analytics | `src/services/progress_analytics.py` | ✅ Complete |
| Reading List | `src/services/reading_list.py` | ✅ Complete |
| Migrations | `src/db/alembic/` | ✅ Complete |
| Deployment | `terraform/modules/ecs/` | ✅ Complete |
| Tests | `tests/` | ✅ 80%+ coverage |

---

## Success Metrics

### Technical Metrics
- ✅ Test coverage: >80% (current: 82%)
- ✅ Pipeline execution time: <5 min (pre-session), <3 min (post-session)
- ⏳ System availability: 99.9% (post-deployment)
- ⏳ Zero PHI breaches (ongoing)

### Field Test Metrics (Phase F/G)
- ⏳ Therapist satisfaction: >4/5
- ⏳ Clinical utility: Frameworks useful in session prep
- ⏳ Time savings: Pre-session prep time reduced by 50%+

---

## Notes

### Risk Mitigation
- ✅ Agent isolation tested extensively (security/ tests)
- ✅ Encryption verified at field and file level
- ✅ Audit logging comprehensive (HIPAA compliant)
- ⏳ Couples merge isolation CRITICAL - extra review before Phase G

### Known Issues
- None critical
- Minor: Perplexity anonymization needs manual audit of sample queries (Phase F)

---

*Last Updated: 2026-02-09*
