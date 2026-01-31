# Rung - Psychology Agent Orchestration System

## Project Overview

**Rung** is a HIPAA-compliant multi-agent psychology support system that acts as a structured translator layer between therapy clients and their therapist.

**Classification**: Healthcare AI | HIPAA-Compliant | Field Test Phase

## Core Concept

Agents do NOT replace clinical judgment - they augment it by:
- Pre-processing client thoughts into clinically-relevant frameworks
- Researching evidence-based interventions before sessions
- Post-processing session insights into actionable development plans
- Maintaining strict context boundaries between individual clients

## Agent Roles

### Rung (Clinical Agent)
- **Purpose**: Pre-session analysis + post-session synthesis
- **Audience**: Therapist (Madeline)
- **Tone**: Socratic, systems-oriented, flags defense patterns
- **Boundary**: ZERO access to Beth's context

### Beth (Client Agent)
- **Purpose**: Client-accessible communication
- **Audience**: Client
- **Tone**: Friendly, accessible language, no clinical jargon
- **Boundary**: ZERO access to Rung's raw output

## Technology Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| LLM | AWS Bedrock (Claude) | HIPAA BAA required |
| Orchestration | n8n (self-hosted EC2) | In VPC for HIPAA |
| Database | RDS PostgreSQL | Encrypted, Multi-AZ |
| Storage | S3 | Client-side encryption |
| Context | Perceptor MCP | Longitudinal tracking |
| Research | Perplexity Labs | Anonymized queries only |
| Auth | AWS Cognito | MFA mandatory |

## HIPAA Requirements

**Non-negotiable**:
- [ ] AWS BAA executed before any PHI processing
- [ ] All PHI encrypted at rest and in transit
- [ ] Audit logging for all PHI access
- [ ] Agent context isolation enforced
- [ ] No PHI in external API calls (Perplexity, Slack)
- [ ] Consent captured and verifiable

## Key Architectural Decisions

See `decisions.log` for full ADRs. Key decisions:

1. **ADR-001**: Bedrock over direct Anthropic API (HIPAA BAA)
2. **ADR-002**: Self-hosted n8n (HIPAA coverage)
3. **ADR-003**: Agent isolation via separate Bedrock calls
4. **ADR-004**: Couples merge at framework-level only
5. **ADR-005**: Perplexity with mandatory anonymization

## Development Patterns

### Agent Prompt Structure
```
System: Role definition + constraints
Context: Perceptor history (agent-specific only)
Input: Client thought capture (transcribed/text)
Output: Structured JSON with frameworks, patterns, recommendations
```

### Data Flow Rules
1. Client input → encrypted S3 → n8n workflow
2. Rung analysis → therapist clinical brief
3. Beth synthesis → client-friendly guide
4. NEVER pass raw Rung output to Beth
5. Couples merge: framework extraction only

## Testing Requirements

| Area | Coverage | Notes |
|------|----------|-------|
| Agent isolation | 100% | Critical security boundary |
| PHI encryption | 100% | HIPAA mandatory |
| API endpoints | 80% | Standard requirement |
| Workflows | E2E | Full pipeline tests |
| Couples merge | 100% | Extra security review |

## File Structure

```
~/projects/Rung/
├── README.md           # Quick start and overview
├── CLAUDE.md           # This file - project context
├── AGENTS.md           # Build/run/test instructions
├── BLUEPRINT.md        # Phase tracking with checkboxes
├── decisions.log       # Architectural decision records
├── ARCHITECTURE.md     # Full technical specification
├── src/                # Source code (TBD)
├── tests/              # Test suites (TBD)
├── terraform/          # Infrastructure as code (TBD)
└── n8n/                # Workflow exports (TBD)
```

## Field Test Phases

1. **Phase 1**: Solo (Rung + Matthew + Madeline) - 4-6 sessions
2. **Phase 2**: Couples (Add Beth + Stacey) - requires Phase 1 success
3. **Phase 3**: Production hardening - HIPAA compliance verification

## Quick Reference

**Before any code changes**:
- Check `decisions.log` for existing architectural decisions
- Verify HIPAA implications of any new data flows
- Ensure agent isolation is maintained

**When stuck**:
1. Check `ARCHITECTURE.md` for technical specifications
2. Review `decisions.log` for context
3. Ask for clarification (don't guess with PHI)

## Contacts

- **Therapist**: Madeline
- **Clients**: Matthew (Rung), Stacey (Beth)
- **Company**: Me, Myself Plus AI LLC
