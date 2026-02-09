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
| Orchestration | Python async pipelines | Workflow execution (`src/pipelines/`) |
| API | FastAPI + Pydantic | Type-safe endpoints with validation |
| Deployment | ECS Fargate | Docker container on AWS |
| Database | RDS PostgreSQL + Alembic | Structured data with migrations |
| Storage | S3 (SSE-KMS) | Voice memos, transcripts, encrypted |
| Encryption | KMS envelope encryption | Field-level PHI encryption |
| Audit | Centralized service | HIPAA-compliant audit logging |
| Auth | Cognito | Therapist authentication with MFA |
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
- Docker installed
- Python 3.11+

# Setup
cd ~/projects/Rung
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run database migrations
make migrate

# Start development server
make dev

# Run tests
make test

# Build Docker image
make build

# Deploy to ECS (requires AWS credentials)
make deploy
```

## Development Commands

```bash
# Development
make dev              # Start FastAPI dev server with auto-reload
make test             # Run test suite with coverage
make lint             # Run linters (ruff, mypy)
make fmt              # Format code (Black, isort)
make migrate          # Run database migrations

# Docker & Deployment
make build            # Build Docker image locally
make run-local        # Run container locally with .env
make push             # Build and push to ECR
make deploy           # Deploy to ECS Fargate

# Infrastructure
make tf-plan          # Terraform plan (dev environment)
make tf-apply         # Terraform apply (dev environment)
```

## Implementation Status

- [x] Architecture Design Complete
- [x] Phase 0: Test Stabilization
- [x] Phase A: Foundation (Encryption, Audit, Migrations)
- [x] Phase B: Pipeline Orchestration (Pre-Session, Post-Session, Couples)
- [x] Phase C: Progress Analytics
- [x] Phase D: Deployment Infrastructure (ECS Fargate)
- [x] Phase E: Documentation
- [x] Phase E2: Reading List Feature (ADR-012)
- [ ] Phase F: Production Deployment
- [ ] Phase G: Couples Module Field Test

## Contact

Architecture designed for Ralph-loop automation with clear completion criteria and testable components.

---

*Last Updated: 2026-02-09*
