# Rung - Psychology Agent Orchestration System

Backend architecture documentation for a HIPAA-compliant multi-agent system that augments therapy sessions.

## Overview

Rung is a therapy augmentation platform that uses AI agents to:
- **Pre-Session**: Convert therapist voice memos into clinical briefs and client preparation guides
- **Post-Session**: Extract frameworks from session notes and generate development sprint plans
- **Couples**: Merge partner insights at the framework level (no raw data crossing)

## Architecture Highlights

| Component | Technology | Purpose |
|-----------|------------|---------|
| LLM | AWS Bedrock (Claude 3.5 Sonnet) | AI inference (HIPAA BAA) |
| Orchestration | n8n (self-hosted) | Workflow automation |
| Database | RDS PostgreSQL | Structured data with field-level encryption |
| Storage | S3 (SSE-KMS) | Voice memos, transcripts, exports |
| Auth | Cognito | Therapist authentication with MFA |
| Context | Perceptor MCP | Longitudinal client tracking |
| Research | Perplexity API | Evidence-based framework lookup (anonymized) |

## Agent Architecture

Two isolated agents with strict context separation:

```
+---------------------------+    +---------------------------+
|      RUNG AGENT           |    |      BETH AGENT           |
|   (Clinical Analysis)     |    |  (Client Communication)   |
+---------------------------+    +---------------------------+
| Inputs:                   |    | Inputs:                   |
| - Raw transcripts         |    | - Abstracted themes       |
| - Session notes           |    | - Exercise templates      |
| - Clinical history        |    | - Client language level   |
+---------------------------+    +---------------------------+
| Outputs:                  |    | Outputs:                  |
| - Clinical briefs         |    | - Client guides           |
| - Framework analysis      |    | - Accessible exercises    |
| - Risk assessments        |    | - Psychoeducation         |
+---------------------------+    +---------------------------+
```

**Critical**: Beth NEVER receives raw clinical data. All content passes through an abstraction layer.

## Documentation

| File | Purpose |
|------|---------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Complete technical specification |
| [BLUEPRINT.md](./BLUEPRINT.md) | Implementation phases with checkboxes |
| [decisions.log](./decisions.log) | Architectural decision records |

## Key Sections in ARCHITECTURE.md

1. **System Overview** - High-level architecture diagram
2. **Service Architecture** - Bounded contexts and communication patterns
3. **Data Models** - Entity relationships and encryption strategy
4. **API Specifications** - OpenAPI 3.0 spec with all endpoints
5. **n8n Workflows** - Pre-session, post-session, and couples merge
6. **Security Architecture** - Auth, encryption, audit logging
7. **Infrastructure** - AWS components and deployment
8. **Implementation Phases** - 6 phases over 20 weeks

## HIPAA Compliance

Key compliance measures:
- AWS BAA covers all infrastructure
- Field-level encryption for PHI (AES-256-GCM, KMS)
- Audit logging with 7-year retention
- MFA required for all therapist access
- Perplexity queries anonymized (no BAA available)
- No PHI in Slack notifications

## Quick Start (Development)

```bash
# Prerequisites
- AWS CLI configured
- Terraform installed
- Python 3.11+
- Node.js 18+

# Clone and setup
cd /home/ubuntu/projects/RelationshipManagementApp/rung-architecture

# Review architecture
cat ARCHITECTURE.md

# Track progress
cat BLUEPRINT.md
```

## Implementation Status

- [x] Architecture Design Complete
- [ ] Phase 1: Foundation (Weeks 1-4)
- [ ] Phase 2: Pre-Session Pipeline (Weeks 5-8)
- [ ] Phase 3: Post-Session Pipeline (Weeks 9-11)
- [ ] Phase 4: Couples Merge (Weeks 12-14)
- [ ] Phase 5: Security & Compliance (Weeks 15-17)
- [ ] Phase 6: Production Readiness (Weeks 18-20)

## Contact

Architecture designed for Ralph-loop automation with clear completion criteria and testable components.

---

*Last Updated: 2026-01-31*
