# n8n Workflows - DEPRECATED

**Status**: ⛔ DEPRECATED as of 2026-02-06
**Superseded By**: Python async pipelines in `src/pipelines/`
**Reason**: See `decisions.log` ADR-011

---

## Migration Summary

The original architecture design used self-hosted n8n on EC2 for workflow orchestration. During implementation (Phase B), the architecture was consolidated to Python async pipelines running on ECS Fargate.

### Why Migrated

**Problems with n8n approach**:
- Split-brain architecture: n8n (JavaScript) orchestrated Python services, duplicating security-critical logic
- No HIPAA BAA coverage for self-hosted n8n
- Additional infrastructure cost: 1 EC2 instance, 1 ALB, 1 PostgreSQL database
- Complexity: Two languages for security-critical code paths
- Limited debuggability: Visual workflows good for simple flows, but complex error states hard to debug

**Benefits of Python pipelines**:
- Single language (Python) for all security-critical code
- Single deployment unit (Docker container on ECS)
- Type safety with Pydantic models
- Direct service integration (no HTTP abstraction layer)
- Better HIPAA auditability (all code in one codebase)
- Structured logging for debugging
- Lower infrastructure cost

### Migration Path

| n8n Workflow | Python Pipeline | Status |
|--------------|----------------|--------|
| `workflows/pre_session.json` | `src/pipelines/pre_session.py` | ✅ Migrated |
| `workflows/post_session.json` | `src/pipelines/post_session.py` | ✅ Migrated |
| `workflows/couples_merge.json` | `src/pipelines/couples_merge.py` | ✅ Migrated |

### Architecture Comparison

**Old Architecture (n8n)**:
```
Client → API Gateway → Lambda → n8n Webhook → n8n Workflow (JS)
                                    ↓
                            HTTP calls to FastAPI services
                                    ↓
                            Python business logic
```

**New Architecture (Consolidated)**:
```
Client → ALB → ECS Fargate (FastAPI) → Python async pipeline
                                            ↓
                                    Direct service calls
                                            ↓
                                    Python business logic
```

### Files in this Directory

These files are preserved for reference only:

- `workflows/` - Original n8n workflow JSON exports (never deployed)
- `credentials/` - n8n credential templates (never used)
- `README.md` - Original n8n setup instructions (outdated)

**DO NOT USE THESE FILES FOR IMPLEMENTATION**

---

## Current Implementation

For the current pipeline implementation, see:

- **Pre-Session**: `src/pipelines/pre_session.py`
- **Post-Session**: `src/pipelines/post_session.py`
- **Couples Merge**: `src/pipelines/couples_merge.py`
- **Base Utilities**: `src/pipelines/base.py`

For deployment, see:
- `Dockerfile` - Container definition
- `Makefile` - Build/deploy commands
- `terraform/modules/ecs/` - ECS Fargate infrastructure

For documentation, see:
- `BLUEPRINT.md` - Current implementation status
- `AGENTS.md` - Build/run/test instructions
- `decisions.log` - ADR-011 for full rationale

---

*Deprecated: 2026-02-06*
