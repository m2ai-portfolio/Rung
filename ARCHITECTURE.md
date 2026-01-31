# Rung - Psychology Agent Orchestration System
## Backend Architecture Design Document

**Version**: 1.0.0
**Date**: 2026-01-31
**Status**: Design Phase
**Author**: Backend Architect

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Service Architecture](#service-architecture)
4. [Data Models](#data-models)
5. [API Specifications](#api-specifications)
6. [n8n Workflow Architecture](#n8n-workflow-architecture)
7. [Security Architecture](#security-architecture)
8. [Infrastructure Components](#infrastructure-components)
9. [Implementation Phases](#implementation-phases)

---

## Executive Summary

Rung is a HIPAA-compliant multi-agent system designed to augment therapy sessions through AI-powered clinical analysis. The system orchestrates two specialized agents (Rung and Beth) with strict context isolation, integrating voice memo transcription, evidence-based research, and longitudinal context tracking.

### Core Capabilities

- **Dual-Agent Architecture**: Rung (clinical framework analyst) and Beth (client communication specialist) with firewall isolation
- **Pre-Session Pipeline**: Voice memo to actionable clinical briefs and client guides
- **Post-Session Pipeline**: Session notes to development sprint plans
- **Couples Merge**: Framework-level synthesis without cross-client data exposure
- **HIPAA Compliance**: End-to-end encryption, audit logging, BAA-covered services only

### Technical Constraints

| Constraint | Implementation |
|------------|----------------|
| LLM Provider | AWS Bedrock (Claude) - HIPAA BAA |
| Orchestration | n8n Cloud (self-hosted with BAA) |
| Storage | S3 (encrypted) + RDS PostgreSQL |
| Context Persistence | Perceptor MCP |
| Research API | Perplexity Labs (anonymized queries only) |
| Notifications | Slack (workflow status only, no PHI) |

---

## System Overview

### Architecture Diagram (Text-Based)

```
+-----------------------------------------------------------------------------------+
|                              RUNG SYSTEM BOUNDARY                                  |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  +-----------+     +------------------+     +------------------+                  |
|  |  Client   |---->|   API Gateway    |---->|  Auth Service    |                  |
|  | (Therapist)|    |  (AWS API GW)    |     | (Cognito + JWT)  |                  |
|  +-----------+     +------------------+     +------------------+                  |
|                            |                        |                             |
|                            v                        v                             |
|  +------------------------------------------------------------------------+      |
|  |                         n8n ORCHESTRATION LAYER                         |      |
|  |  +---------------+  +------------------+  +------------------+          |      |
|  |  | Pre-Session   |  | Post-Session     |  | Couples Merge    |          |      |
|  |  | Workflow      |  | Workflow         |  | Workflow         |          |      |
|  |  +-------+-------+  +--------+---------+  +--------+---------+          |      |
|  |          |                   |                     |                    |      |
|  +----------|-------------------|---------------------|--------------------+      |
|             |                   |                     |                           |
|             v                   v                     v                           |
|  +------------------------------------------------------------------------+      |
|  |                         AGENT ISOLATION LAYER                           |      |
|  |  +-----------------------------+  +-----------------------------+       |      |
|  |  |      RUNG AGENT CONTEXT     |  |      BETH AGENT CONTEXT     |       |      |
|  |  |  (Clinical Analysis)        |  |  (Client Communication)     |       |      |
|  |  |  +-----------------------+  |  |  +-----------------------+  |       |      |
|  |  |  | - Framework Extraction|  |  |  | - Language Adaptation |  |       |      |
|  |  |  | - Pattern Analysis    |  |  |  | - Psychoeducation    |  |       |      |
|  |  |  | - Clinical Scoring    |  |  |  | - Exercise Design    |  |       |      |
|  |  |  | - Risk Assessment     |  |  |  | - Progress Tracking  |  |       |      |
|  |  |  +-----------------------+  |  |  +-----------------------+  |       |      |
|  |  +-------------+---------------+  +---------------+-------------+       |      |
|  |                |                                  |                     |      |
|  |                |      FIREWALL (No PHI Cross)     |                     |      |
|  |                +----------------------------------+                     |      |
|  +------------------------------------------------------------------------+      |
|                    |                   |                   |                      |
|                    v                   v                   v                      |
|  +------------------------------------------------------------------------+      |
|  |                         SERVICE LAYER                                   |      |
|  |  +-------------+  +-------------+  +-------------+  +-------------+    |      |
|  |  | Transcribe  |  | Bedrock     |  | Perplexity  |  | Perceptor   |    |      |
|  |  | Service     |  | LLM Service |  | Research    |  | Context     |    |      |
|  |  | (AWS)       |  | (Claude)    |  | Service     |  | MCP         |    |      |
|  |  +-------------+  +-------------+  +-------------+  +-------------+    |      |
|  +------------------------------------------------------------------------+      |
|                    |                   |                   |                      |
|                    v                   v                   v                      |
|  +------------------------------------------------------------------------+      |
|  |                         DATA LAYER                                      |      |
|  |  +--------------------+  +--------------------+  +------------------+   |      |
|  |  |    RDS PostgreSQL  |  |    S3 Encrypted    |  |   Perceptor     |   |      |
|  |  |    (Structured)    |  |    (Voice/Files)   |  |   (Contexts)    |   |      |
|  |  +--------------------+  +--------------------+  +------------------+   |      |
|  +------------------------------------------------------------------------+      |
|                                                                                   |
+-----------------------------------------------------------------------------------+
                                        |
                                        v
                              +-------------------+
                              |  Slack Webhooks   |
                              | (Status Only)     |
                              +-------------------+
```

### Component Responsibilities

| Component | Responsibility | HIPAA Role |
|-----------|---------------|------------|
| API Gateway | Request routing, rate limiting, auth validation | Access Control |
| Auth Service | JWT validation, therapist identity, session mgmt | Authentication |
| n8n Orchestration | Workflow execution, step sequencing | Processing |
| Agent Isolation Layer | Context separation, agent routing | Data Segregation |
| Rung Agent | Clinical analysis, framework extraction | Processing |
| Beth Agent | Client-facing content generation | Processing |
| Transcribe Service | Voice-to-text conversion | Processing |
| Bedrock LLM Service | AI inference (Claude) | Processing |
| Perplexity Research | Evidence-based framework lookup | Processing |
| Perceptor MCP | Longitudinal context persistence | Storage |
| RDS PostgreSQL | Structured data (clients, sessions, briefs) | Storage |
| S3 Encrypted | Binary storage (voice memos, exports) | Storage |

---

## Service Architecture

### Service Boundary Definitions

#### 1. Gateway Service
```
Domain: Request routing and access control
Bounded Context: Authentication & Authorization
Technology: AWS API Gateway + Lambda Authorizer

Responsibilities:
- JWT validation
- Rate limiting (100 req/min per therapist)
- Request logging (no PHI in logs)
- Route to appropriate n8n webhook
```

#### 2. Orchestration Service (n8n)
```
Domain: Workflow execution
Bounded Context: Process Management
Technology: n8n Cloud (self-hosted)

Responsibilities:
- Workflow triggering
- Step sequencing
- Error handling and retry
- Slack notifications
```

#### 3. Agent Service
```
Domain: AI-powered analysis
Bounded Context: Clinical Intelligence
Technology: AWS Lambda + Bedrock

Responsibilities:
- Agent context management
- Prompt construction
- Response parsing
- Context isolation enforcement
```

#### 4. Transcription Service
```
Domain: Voice processing
Bounded Context: Media Processing
Technology: AWS Transcribe Medical

Responsibilities:
- Voice memo transcription
- Speaker diarization
- Medical terminology handling
- Transcript storage
```

#### 5. Research Service
```
Domain: Evidence lookup
Bounded Context: Knowledge Retrieval
Technology: Lambda + Perplexity API

Responsibilities:
- Query anonymization (strip PHI before API call)
- Framework search
- Citation formatting
- Response caching (non-PHI only)
```

#### 6. Context Service
```
Domain: Longitudinal tracking
Bounded Context: Client History
Technology: Perceptor MCP

Responsibilities:
- Session context persistence
- Cross-session pattern retrieval
- Development tracking
- Context summarization
```

#### 7. Storage Service
```
Domain: Data persistence
Bounded Context: Data Management
Technology: RDS PostgreSQL + S3

Responsibilities:
- Encrypted data storage
- Backup management
- Data lifecycle (retention policies)
- Export generation
```

### Inter-Service Communication Patterns

```
+------------------+     +------------------+     +------------------+
|                  |     |                  |     |                  |
|  Sync Pattern    |     |  Async Pattern   |     |  Event Pattern   |
|  (REST/gRPC)     |     |  (SQS/Lambda)    |     |  (EventBridge)   |
|                  |     |                  |     |                  |
+------------------+     +------------------+     +------------------+
        |                        |                        |
        v                        v                        v
+------------------+     +------------------+     +------------------+
| - Auth requests  |     | - Transcription  |     | - Workflow done  |
| - Context reads  |     | - LLM inference  |     | - Brief ready    |
| - Status checks  |     | - Research calls |     | - Error alerts   |
+------------------+     +------------------+     +------------------+
```

---

## Data Models

### Entity Relationship Diagram

```
+----------------+       +----------------+       +----------------+
|    Therapist   |       |     Client     |       |    Session     |
+----------------+       +----------------+       +----------------+
| therapist_id PK|<----->| client_id PK   |<----->| session_id PK  |
| email          |       | therapist_id FK|       | client_id FK   |
| name           |       | agent_id       |       | date           |
| practice_id    |       | created_at     |       | type           |
| encryption_key |       | encrypted_name |       | status         |
| created_at     |       | encrypted_dob  |       | voice_memo_s3  |
+----------------+       | context_ref    |       | transcript_s3  |
                         +----------------+       | notes_enc      |
                                                  +----------------+
                                                         |
                    +------------------------------------+
                    |                    |               |
                    v                    v               v
            +----------------+   +----------------+   +----------------+
            |   VoiceMemo    |   | ClinicalBrief  |   |  ClientGuide   |
            +----------------+   +----------------+   +----------------+
            | memo_id PK     |   | brief_id PK    |   | guide_id PK    |
            | session_id FK  |   | session_id FK  |   | session_id FK  |
            | s3_uri         |   | frameworks[]   |   | content_enc    |
            | duration_sec   |   | patterns[]     |   | exercises[]    |
            | uploaded_at    |   | risk_flags[]   |   | psychoed_enc   |
            | transcribed_at |   | citations[]    |   | created_at     |
            +----------------+   | content_enc    |   +----------------+
                                 | created_at     |
                                 +----------------+

+----------------+       +----------------+       +----------------+
|     Agent      |       |  AgentContext  |       | DevelopmentPlan|
+----------------+       +----------------+       +----------------+
| agent_id PK    |<----->| context_id PK  |       | plan_id PK     |
| name (Rung/Beth|       | agent_id FK    |       | client_id FK   |
| system_prompt  |       | client_id FK   |       | sprint_num     |
| capabilities[] |       | perceptor_ref  |       | goals_enc[]    |
| created_at     |       | summary_enc    |       | exercises_enc[]|
+----------------+       | updated_at     |       | progress_enc   |
                         +----------------+       | created_at     |
                                                  +----------------+

+----------------+       +----------------+
|   CoupleLink   |       |  FrameworkMerge|
+----------------+       +----------------+
| link_id PK     |       | merge_id PK    |
| client_a_id FK |       | link_id FK     |
| client_b_id FK |       | topic          |
| therapist_id FK|       | framework_only |
| status         |       | merged_content |
| created_at     |       | created_at     |
+----------------+       +----------------+

+----------------+
|   AuditLog     |
+----------------+
| log_id PK      |
| timestamp      |
| actor_id       |
| actor_type     |
| action         |
| resource_type  |
| resource_id    |
| ip_address     |
| user_agent     |
| result         |
+----------------+
```

### Detailed Schema Definitions

```sql
-- Core Tables

CREATE TABLE therapists (
    therapist_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name_encrypted BYTEA NOT NULL,
    practice_id UUID REFERENCES practices(practice_id),
    encryption_key_ref VARCHAR(255) NOT NULL,  -- AWS KMS key ARN
    cognito_sub VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE clients (
    client_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    therapist_id UUID NOT NULL REFERENCES therapists(therapist_id),
    agent_id UUID NOT NULL REFERENCES agents(agent_id),
    external_id_encrypted BYTEA,  -- Practice's client ID
    name_encrypted BYTEA NOT NULL,
    dob_encrypted BYTEA,
    context_ref VARCHAR(255),  -- Perceptor context ID
    metadata_encrypted JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(client_id),
    session_date DATE NOT NULL,
    session_type VARCHAR(50) NOT NULL,  -- 'individual', 'couples', 'family'
    status VARCHAR(50) DEFAULT 'scheduled',  -- 'scheduled', 'voice_received', 'processing', 'complete'
    voice_memo_s3_uri VARCHAR(512),
    transcript_s3_uri VARCHAR(512),
    notes_encrypted BYTEA,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_session_type CHECK (session_type IN ('individual', 'couples', 'family')),
    CONSTRAINT valid_status CHECK (status IN ('scheduled', 'voice_received', 'processing', 'complete', 'error'))
);

CREATE TABLE agents (
    agent_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,  -- 'Rung' or 'Beth'
    system_prompt_encrypted BYTEA NOT NULL,
    capabilities JSONB NOT NULL DEFAULT '[]',
    bedrock_model_id VARCHAR(100) NOT NULL,
    max_tokens INTEGER DEFAULT 4096,
    temperature DECIMAL(3,2) DEFAULT 0.7,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE agent_contexts (
    context_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(agent_id),
    client_id UUID NOT NULL REFERENCES clients(client_id),
    perceptor_context_ref VARCHAR(255),
    summary_encrypted BYTEA,
    last_session_id UUID REFERENCES sessions(session_id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(agent_id, client_id)
);

-- Workflow Output Tables

CREATE TABLE clinical_briefs (
    brief_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(session_id),
    frameworks JSONB NOT NULL DEFAULT '[]',
    patterns JSONB NOT NULL DEFAULT '[]',
    risk_flags JSONB NOT NULL DEFAULT '[]',
    citations JSONB NOT NULL DEFAULT '[]',
    content_encrypted BYTEA NOT NULL,
    agent_id UUID REFERENCES agents(agent_id),
    workflow_run_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE client_guides (
    guide_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(session_id),
    content_encrypted BYTEA NOT NULL,
    exercises JSONB NOT NULL DEFAULT '[]',
    psychoeducation_encrypted BYTEA,
    agent_id UUID REFERENCES agents(agent_id),
    workflow_run_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE development_plans (
    plan_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(client_id),
    sprint_number INTEGER NOT NULL,
    goals_encrypted BYTEA NOT NULL,
    exercises_encrypted BYTEA,
    progress_encrypted BYTEA,
    start_date DATE,
    end_date DATE,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(client_id, sprint_number)
);

-- Couples Tables

CREATE TABLE couple_links (
    link_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_a_id UUID NOT NULL REFERENCES clients(client_id),
    client_b_id UUID NOT NULL REFERENCES clients(client_id),
    therapist_id UUID NOT NULL REFERENCES therapists(therapist_id),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT different_clients CHECK (client_a_id != client_b_id),
    CONSTRAINT valid_link_status CHECK (status IN ('active', 'paused', 'terminated'))
);

CREATE TABLE framework_merges (
    merge_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    link_id UUID NOT NULL REFERENCES couple_links(link_id),
    topic VARCHAR(255) NOT NULL,
    framework_only BOOLEAN DEFAULT TRUE,  -- CRITICAL: Only framework, no raw data
    merged_content_encrypted BYTEA NOT NULL,
    source_session_a_id UUID REFERENCES sessions(session_id),
    source_session_b_id UUID REFERENCES sessions(session_id),
    workflow_run_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit Table

CREATE TABLE audit_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    actor_id UUID NOT NULL,
    actor_type VARCHAR(50) NOT NULL,  -- 'therapist', 'system', 'agent'
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID,
    ip_address INET,
    user_agent VARCHAR(500),
    request_id VARCHAR(255),
    result VARCHAR(50) NOT NULL,  -- 'success', 'failure', 'denied'
    details JSONB,

    CONSTRAINT valid_actor_type CHECK (actor_type IN ('therapist', 'system', 'agent')),
    CONSTRAINT valid_result CHECK (result IN ('success', 'failure', 'denied'))
);

-- Indexes for Performance

CREATE INDEX idx_clients_therapist ON clients(therapist_id);
CREATE INDEX idx_sessions_client ON sessions(client_id);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_date ON sessions(session_date);
CREATE INDEX idx_briefs_session ON clinical_briefs(session_id);
CREATE INDEX idx_guides_session ON client_guides(session_id);
CREATE INDEX idx_plans_client ON development_plans(client_id);
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_actor ON audit_logs(actor_id);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
```

### Encryption Strategy

```
+------------------------------------------------------------------+
|                    ENCRYPTION ARCHITECTURE                        |
+------------------------------------------------------------------+
|                                                                   |
|  +------------------------+    +------------------------+         |
|  |   Data at Rest         |    |   Data in Transit      |         |
|  +------------------------+    +------------------------+         |
|  | - RDS: AES-256-GCM     |    | - TLS 1.3 (all comms)  |         |
|  | - S3: SSE-KMS          |    | - mTLS (service-to-svc)|         |
|  | - Field-level: KMS     |    | - Certificate pinning  |         |
|  +------------------------+    +------------------------+         |
|                                                                   |
|  +---------------------------------------------------------------+|
|  |                    Key Hierarchy                               ||
|  |  +------------------+                                          ||
|  |  | AWS KMS CMK      | <-- Root key (AWS managed, HIPAA)       ||
|  |  +--------+---------+                                          ||
|  |           |                                                    ||
|  |           v                                                    ||
|  |  +------------------+                                          ||
|  |  | Therapist DEK    | <-- Per-therapist data encryption key   ||
|  |  +--------+---------+                                          ||
|  |           |                                                    ||
|  |           v                                                    ||
|  |  +------------------+                                          ||
|  |  | Client DEK       | <-- Per-client field encryption         ||
|  |  +------------------+                                          ||
|  +---------------------------------------------------------------+|
|                                                                   |
|  Encrypted Fields (BYTEA):                                        |
|  - therapist.name_encrypted                                       |
|  - client.name_encrypted, dob_encrypted, metadata_encrypted       |
|  - session.notes_encrypted                                        |
|  - clinical_brief.content_encrypted                               |
|  - client_guide.content_encrypted, psychoeducation_encrypted      |
|  - development_plan.goals_encrypted, exercises_encrypted          |
|  - framework_merge.merged_content_encrypted                       |
|                                                                   |
+------------------------------------------------------------------+
```

---

## API Specifications

### OpenAPI 3.0 Specification

```yaml
openapi: 3.0.3
info:
  title: Rung Psychology Agent API
  description: HIPAA-compliant therapy augmentation API
  version: 1.0.0
  contact:
    email: support@rung.health

servers:
  - url: https://api.rung.health/v1
    description: Production
  - url: https://api-staging.rung.health/v1
    description: Staging

security:
  - bearerAuth: []

paths:
  # === Pre-Session Workflow ===

  /sessions/{sessionId}/voice-memo:
    post:
      summary: Upload voice memo for pre-session analysis
      tags: [Pre-Session]
      operationId: uploadVoiceMemo
      parameters:
        - name: sessionId
          in: path
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              required:
                - file
              properties:
                file:
                  type: string
                  format: binary
                  description: Audio file (mp3, m4a, wav)
                duration_seconds:
                  type: integer
                  minimum: 1
                  maximum: 3600
      responses:
        '202':
          description: Voice memo accepted for processing
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/WorkflowStatus'
        '400':
          $ref: '#/components/responses/BadRequest'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '413':
          description: File too large (max 100MB)

  /sessions/{sessionId}/pre-session/status:
    get:
      summary: Get pre-session workflow status
      tags: [Pre-Session]
      operationId: getPreSessionStatus
      parameters:
        - name: sessionId
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Workflow status
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PreSessionStatus'
        '404':
          $ref: '#/components/responses/NotFound'

  /sessions/{sessionId}/clinical-brief:
    get:
      summary: Get clinical brief for therapist
      tags: [Pre-Session]
      operationId: getClinicalBrief
      parameters:
        - name: sessionId
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Clinical brief
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ClinicalBrief'
        '404':
          $ref: '#/components/responses/NotFound'
        '425':
          description: Brief not yet ready (workflow in progress)

  /sessions/{sessionId}/client-guide:
    get:
      summary: Get client preparation guide
      tags: [Pre-Session]
      operationId: getClientGuide
      parameters:
        - name: sessionId
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Client guide
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ClientGuide'
        '404':
          $ref: '#/components/responses/NotFound'

  # === Post-Session Workflow ===

  /sessions/{sessionId}/notes:
    post:
      summary: Submit session notes for post-session processing
      tags: [Post-Session]
      operationId: submitSessionNotes
      parameters:
        - name: sessionId
          in: path
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - notes
              properties:
                notes:
                  type: string
                  minLength: 50
                  maxLength: 50000
                  description: Session notes (will be encrypted)
                session_duration_minutes:
                  type: integer
                  minimum: 5
                  maximum: 180
                modalities_used:
                  type: array
                  items:
                    type: string
                    enum: [CBT, DBT, ACT, EFT, Gottman, IFS, Psychodynamic, Other]
      responses:
        '202':
          description: Notes accepted for processing
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/WorkflowStatus'

  /sessions/{sessionId}/post-session/status:
    get:
      summary: Get post-session workflow status
      tags: [Post-Session]
      operationId: getPostSessionStatus
      parameters:
        - name: sessionId
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Workflow status
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PostSessionStatus'

  /clients/{clientId}/development-plan:
    get:
      summary: Get current development sprint plan
      tags: [Post-Session]
      operationId: getDevelopmentPlan
      parameters:
        - name: clientId
          in: path
          required: true
          schema:
            type: string
            format: uuid
        - name: sprint
          in: query
          schema:
            type: integer
            minimum: 1
          description: Sprint number (defaults to current)
      responses:
        '200':
          description: Development plan
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/DevelopmentPlan'

  # === Couples Merge Workflow ===

  /couples/{linkId}/merge:
    post:
      summary: Trigger couples framework merge
      tags: [Couples]
      operationId: triggerCouplesMerge
      parameters:
        - name: linkId
          in: path
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - topic
              properties:
                topic:
                  type: string
                  minLength: 3
                  maxLength: 200
                  description: Topic for framework merge (e.g., "communication patterns")
                session_a_id:
                  type: string
                  format: uuid
                  description: Optional specific session from partner A
                session_b_id:
                  type: string
                  format: uuid
                  description: Optional specific session from partner B
      responses:
        '202':
          description: Merge workflow triggered
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/WorkflowStatus'

  /couples/{linkId}/merged-frameworks:
    get:
      summary: Get merged framework insights
      tags: [Couples]
      operationId: getMergedFrameworks
      parameters:
        - name: linkId
          in: path
          required: true
          schema:
            type: string
            format: uuid
        - name: topic
          in: query
          schema:
            type: string
      responses:
        '200':
          description: Merged frameworks
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/FrameworkMerge'

  # === Client Management ===

  /clients:
    post:
      summary: Create new client
      tags: [Clients]
      operationId: createClient
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ClientCreate'
      responses:
        '201':
          description: Client created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Client'

    get:
      summary: List therapist's clients
      tags: [Clients]
      operationId: listClients
      parameters:
        - name: page
          in: query
          schema:
            type: integer
            default: 1
        - name: limit
          in: query
          schema:
            type: integer
            default: 20
            maximum: 100
        - name: active_only
          in: query
          schema:
            type: boolean
            default: true
      responses:
        '200':
          description: Client list
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ClientList'

  /clients/{clientId}:
    get:
      summary: Get client details
      tags: [Clients]
      operationId: getClient
      parameters:
        - name: clientId
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Client details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Client'

  /clients/{clientId}/context:
    get:
      summary: Get client's longitudinal context summary
      tags: [Clients]
      operationId: getClientContext
      parameters:
        - name: clientId
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Context summary from Perceptor
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ClientContext'

  # === Session Management ===

  /sessions:
    post:
      summary: Schedule a new session
      tags: [Sessions]
      operationId: createSession
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SessionCreate'
      responses:
        '201':
          description: Session created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Session'

  /clients/{clientId}/sessions:
    get:
      summary: List client sessions
      tags: [Sessions]
      operationId: listClientSessions
      parameters:
        - name: clientId
          in: path
          required: true
          schema:
            type: string
            format: uuid
        - name: status
          in: query
          schema:
            type: string
            enum: [scheduled, voice_received, processing, complete, error]
        - name: from_date
          in: query
          schema:
            type: string
            format: date
        - name: to_date
          in: query
          schema:
            type: string
            format: date
      responses:
        '200':
          description: Session list
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SessionList'

  # === Couples Management ===

  /couples:
    post:
      summary: Link two clients as a couple
      tags: [Couples]
      operationId: createCoupleLink
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - client_a_id
                - client_b_id
              properties:
                client_a_id:
                  type: string
                  format: uuid
                client_b_id:
                  type: string
                  format: uuid
      responses:
        '201':
          description: Couple linked
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CoupleLink'

components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
      description: Cognito-issued JWT token

  schemas:
    WorkflowStatus:
      type: object
      properties:
        workflow_id:
          type: string
        status:
          type: string
          enum: [queued, running, completed, failed]
        started_at:
          type: string
          format: date-time
        completed_at:
          type: string
          format: date-time
        current_step:
          type: string
        progress_percent:
          type: integer
          minimum: 0
          maximum: 100

    PreSessionStatus:
      allOf:
        - $ref: '#/components/schemas/WorkflowStatus'
        - type: object
          properties:
            steps:
              type: object
              properties:
                transcription:
                  $ref: '#/components/schemas/StepStatus'
                rung_analysis:
                  $ref: '#/components/schemas/StepStatus'
                research_lookup:
                  $ref: '#/components/schemas/StepStatus'
                beth_synthesis:
                  $ref: '#/components/schemas/StepStatus'

    PostSessionStatus:
      allOf:
        - $ref: '#/components/schemas/WorkflowStatus'
        - type: object
          properties:
            steps:
              type: object
              properties:
                framework_extraction:
                  $ref: '#/components/schemas/StepStatus'
                pattern_analysis:
                  $ref: '#/components/schemas/StepStatus'
                sprint_planning:
                  $ref: '#/components/schemas/StepStatus'
                context_archive:
                  $ref: '#/components/schemas/StepStatus'

    StepStatus:
      type: object
      properties:
        status:
          type: string
          enum: [pending, running, completed, failed, skipped]
        started_at:
          type: string
          format: date-time
        completed_at:
          type: string
          format: date-time
        error_message:
          type: string

    ClinicalBrief:
      type: object
      properties:
        brief_id:
          type: string
          format: uuid
        session_id:
          type: string
          format: uuid
        created_at:
          type: string
          format: date-time
        frameworks:
          type: array
          items:
            $ref: '#/components/schemas/Framework'
        patterns:
          type: array
          items:
            $ref: '#/components/schemas/Pattern'
        risk_flags:
          type: array
          items:
            $ref: '#/components/schemas/RiskFlag'
        citations:
          type: array
          items:
            $ref: '#/components/schemas/Citation'
        content:
          type: string
          description: Full clinical brief content

    Framework:
      type: object
      properties:
        name:
          type: string
          example: "Gottman Four Horsemen"
        relevance_score:
          type: number
          format: float
          minimum: 0
          maximum: 1
        application_notes:
          type: string
        evidence_quotes:
          type: array
          items:
            type: string

    Pattern:
      type: object
      properties:
        pattern_type:
          type: string
          enum: [communication, conflict, attachment, behavioral, cognitive, relational]
        description:
          type: string
        frequency:
          type: string
          enum: [emerging, recurring, chronic]
        sessions_observed:
          type: integer
        intervention_suggestions:
          type: array
          items:
            type: string

    RiskFlag:
      type: object
      properties:
        risk_type:
          type: string
          enum: [safety, crisis, deterioration, dropout, ethical]
        severity:
          type: string
          enum: [low, medium, high, critical]
        description:
          type: string
        recommended_action:
          type: string

    Citation:
      type: object
      properties:
        title:
          type: string
        authors:
          type: string
        source:
          type: string
        year:
          type: integer
        relevance:
          type: string
        url:
          type: string
          format: uri

    ClientGuide:
      type: object
      properties:
        guide_id:
          type: string
          format: uuid
        session_id:
          type: string
          format: uuid
        created_at:
          type: string
          format: date-time
        content:
          type: string
          description: Client-friendly preparation guide
        exercises:
          type: array
          items:
            $ref: '#/components/schemas/Exercise'
        psychoeducation:
          type: string
          description: Educational content for client

    Exercise:
      type: object
      properties:
        title:
          type: string
        description:
          type: string
        duration_minutes:
          type: integer
        difficulty:
          type: string
          enum: [beginner, intermediate, advanced]
        framework:
          type: string
        instructions:
          type: array
          items:
            type: string

    DevelopmentPlan:
      type: object
      properties:
        plan_id:
          type: string
          format: uuid
        client_id:
          type: string
          format: uuid
        sprint_number:
          type: integer
        start_date:
          type: string
          format: date
        end_date:
          type: string
          format: date
        status:
          type: string
          enum: [active, completed, paused]
        goals:
          type: array
          items:
            $ref: '#/components/schemas/Goal'
        exercises:
          type: array
          items:
            $ref: '#/components/schemas/Exercise'
        progress:
          $ref: '#/components/schemas/Progress'

    Goal:
      type: object
      properties:
        goal_id:
          type: string
        description:
          type: string
        target_date:
          type: string
          format: date
        status:
          type: string
          enum: [not_started, in_progress, achieved, deferred]
        metrics:
          type: array
          items:
            type: string

    Progress:
      type: object
      properties:
        overall_percent:
          type: integer
          minimum: 0
          maximum: 100
        goals_achieved:
          type: integer
        goals_total:
          type: integer
        notes:
          type: string

    FrameworkMerge:
      type: object
      properties:
        merge_id:
          type: string
          format: uuid
        link_id:
          type: string
          format: uuid
        topic:
          type: string
        created_at:
          type: string
          format: date-time
        merged_content:
          type: string
          description: Framework-level insights only (no raw client data)
        shared_patterns:
          type: array
          items:
            type: string
        divergent_patterns:
          type: array
          items:
            type: string
        recommended_interventions:
          type: array
          items:
            type: string

    Client:
      type: object
      properties:
        client_id:
          type: string
          format: uuid
        name:
          type: string
        agent_assigned:
          type: string
          enum: [Rung, Beth]
        created_at:
          type: string
          format: date-time
        session_count:
          type: integer
        last_session_date:
          type: string
          format: date
        is_active:
          type: boolean

    ClientCreate:
      type: object
      required:
        - name
      properties:
        name:
          type: string
          minLength: 1
          maxLength: 200
        external_id:
          type: string
          description: Practice's internal client ID
        date_of_birth:
          type: string
          format: date
        agent_preference:
          type: string
          enum: [Rung, Beth]
          default: Rung
        metadata:
          type: object
          additionalProperties: true

    ClientList:
      type: object
      properties:
        clients:
          type: array
          items:
            $ref: '#/components/schemas/Client'
        pagination:
          $ref: '#/components/schemas/Pagination'

    ClientContext:
      type: object
      properties:
        client_id:
          type: string
          format: uuid
        summary:
          type: string
          description: Longitudinal context summary from Perceptor
        session_count:
          type: integer
        key_themes:
          type: array
          items:
            type: string
        active_patterns:
          type: array
          items:
            $ref: '#/components/schemas/Pattern'
        current_goals:
          type: array
          items:
            $ref: '#/components/schemas/Goal'
        last_updated:
          type: string
          format: date-time

    Session:
      type: object
      properties:
        session_id:
          type: string
          format: uuid
        client_id:
          type: string
          format: uuid
        session_date:
          type: string
          format: date
        session_type:
          type: string
          enum: [individual, couples, family]
        status:
          type: string
          enum: [scheduled, voice_received, processing, complete, error]
        has_voice_memo:
          type: boolean
        has_clinical_brief:
          type: boolean
        has_client_guide:
          type: boolean
        created_at:
          type: string
          format: date-time

    SessionCreate:
      type: object
      required:
        - client_id
        - session_date
        - session_type
      properties:
        client_id:
          type: string
          format: uuid
        session_date:
          type: string
          format: date
        session_type:
          type: string
          enum: [individual, couples, family]

    SessionList:
      type: object
      properties:
        sessions:
          type: array
          items:
            $ref: '#/components/schemas/Session'
        pagination:
          $ref: '#/components/schemas/Pagination'

    CoupleLink:
      type: object
      properties:
        link_id:
          type: string
          format: uuid
        client_a:
          $ref: '#/components/schemas/Client'
        client_b:
          $ref: '#/components/schemas/Client'
        status:
          type: string
          enum: [active, paused, terminated]
        created_at:
          type: string
          format: date-time

    Pagination:
      type: object
      properties:
        page:
          type: integer
        limit:
          type: integer
        total:
          type: integer
        has_next:
          type: boolean

  responses:
    BadRequest:
      description: Invalid request
      content:
        application/json:
          schema:
            type: object
            properties:
              error:
                type: string
              details:
                type: array
                items:
                  type: string

    Unauthorized:
      description: Authentication required
      content:
        application/json:
          schema:
            type: object
            properties:
              error:
                type: string
                example: "Invalid or expired token"

    NotFound:
      description: Resource not found
      content:
        application/json:
          schema:
            type: object
            properties:
              error:
                type: string
                example: "Resource not found"
```

---

## n8n Workflow Architecture

### Pre-Session Workflow

```
Workflow: pre_session_pipeline
Trigger: Webhook (POST /n8n/pre-session)
Estimated Duration: 2-5 minutes

+-------------------------------------------------------------------+
|                    PRE-SESSION WORKFLOW                            |
+-------------------------------------------------------------------+
|                                                                   |
|  [1] WEBHOOK TRIGGER                                              |
|      +-----------------+                                          |
|      | Receive Request |                                          |
|      | - session_id    |                                          |
|      | - s3_uri        |                                          |
|      | - client_id     |                                          |
|      +--------+--------+                                          |
|               |                                                   |
|               v                                                   |
|  [2] VALIDATE & FETCH                                             |
|      +-----------------+     +-----------------+                  |
|      | Validate JWT    |---->| Fetch S3 Audio  |                  |
|      | (HTTP Request)  |     | (AWS S3 Node)   |                  |
|      +-----------------+     +--------+--------+                  |
|                                       |                           |
|               +-----------------------+                           |
|               |                                                   |
|               v                                                   |
|  [3] TRANSCRIPTION                                                |
|      +-----------------+                                          |
|      | AWS Transcribe  |                                          |
|      | Medical         |                                          |
|      | - Wait for job  |                                          |
|      +--------+--------+                                          |
|               |                                                   |
|               v                                                   |
|  [4] PARALLEL PROCESSING                                          |
|      +---------------------------+---------------------------+    |
|      |                           |                           |    |
|      v                           v                           v    |
|  +----------+             +----------+              +----------+  |
|  | Perceptor|             | Rung     |              | Perplexity|  |
|  | Load     |             | Agent    |              | Research  |  |
|  | Context  |             | Analysis |              | Lookup    |  |
|  +----+-----+             +----+-----+              +----+------+  |
|       |                        |                        |         |
|       +------------------------+------------------------+         |
|                                |                                  |
|                                v                                  |
|  [5] SYNTHESIS                                                    |
|      +-----------------+                                          |
|      | Merge Results   |                                          |
|      | - Context       |                                          |
|      | - Analysis      |                                          |
|      | - Research      |                                          |
|      +--------+--------+                                          |
|               |                                                   |
|               v                                                   |
|  [6] DUAL OUTPUT GENERATION                                       |
|      +---------------------------+---------------------------+    |
|      |                           |                           |    |
|      v                           v                           |    |
|  +----------------+       +----------------+                 |    |
|  | RUNG: Clinical |       | BETH: Client   |                 |    |
|  | Brief Generator|       | Guide Generator|                 |    |
|  | (Bedrock)      |       | (Bedrock)      |                 |    |
|  +-------+--------+       +-------+--------+                 |    |
|          |                        |                          |    |
|          +------------------------+                          |    |
|                     |                                        |    |
|                     v                                        |    |
|  [7] PERSIST & NOTIFY                                        |    |
|      +---------------------------------------------------+   |    |
|      | Store to RDS | Store to S3 | Update Perceptor     |   |    |
|      +---------------------------+---------------------------+    |
|                     |                                             |
|                     v                                             |
|      +-----------------+                                          |
|      | Slack Notify    |                                          |
|      | (Status Only)   |                                          |
|      +-----------------+                                          |
|                                                                   |
+-------------------------------------------------------------------+
```

### Pre-Session Workflow Nodes (Detailed)

```yaml
# n8n Workflow JSON Structure
workflow_name: "pre_session_pipeline"
nodes:

  # 1. Webhook Trigger
  - name: "Webhook Trigger"
    type: "n8n-nodes-base.webhook"
    parameters:
      httpMethod: "POST"
      path: "pre-session"
      authentication: "headerAuth"
      responseMode: "responseNode"
    position: [100, 300]

  # 2. Validate JWT
  - name: "Validate JWT"
    type: "n8n-nodes-base.httpRequest"
    parameters:
      url: "https://cognito-idp.us-east-1.amazonaws.com/"
      method: "POST"
      headers:
        X-Amz-Target: "AWSCognitoIdentityProviderService.GetUser"
        Content-Type: "application/x-amz-json-1.1"
      body: "={{ JSON.stringify({ AccessToken: $json.headers.authorization.split(' ')[1] }) }}"
    position: [300, 300]

  # 3. Fetch Audio from S3
  - name: "Fetch S3 Audio"
    type: "n8n-nodes-base.awsS3"
    parameters:
      operation: "download"
      bucketName: "rung-voice-memos"
      fileKey: "={{ $json.body.s3_uri }}"
    position: [500, 300]

  # 4. AWS Transcribe
  - name: "Start Transcription"
    type: "n8n-nodes-base.awsTranscribe"
    parameters:
      operation: "transcribe"
      languageCode: "en-US"
      mediaFormat: "mp3"
      specialty: "PRIMARYCARE"  # Medical vocabulary
      outputBucketName: "rung-transcripts"
    position: [700, 300]

  # 5. Wait for Transcription
  - name: "Wait Transcription"
    type: "n8n-nodes-base.wait"
    parameters:
      unit: "seconds"
      amount: 30
    position: [900, 300]

  # 6. Poll Transcription Status
  - name: "Poll Transcription"
    type: "n8n-nodes-base.httpRequest"
    parameters:
      url: "https://transcribe.us-east-1.amazonaws.com"
      method: "POST"
      # Poll until complete
    position: [1100, 300]

  # 7. Load Perceptor Context (Parallel Branch A)
  - name: "Load Perceptor Context"
    type: "n8n-nodes-base.httpRequest"
    parameters:
      url: "http://perceptor-mcp:8080/load"
      method: "POST"
      body:
        client_id: "={{ $json.client_id }}"
        limit: 5
    position: [1300, 100]

  # 8. Rung Agent Analysis (Parallel Branch B)
  - name: "Rung Analysis"
    type: "n8n-nodes-base.httpRequest"
    parameters:
      url: "https://bedrock-runtime.us-east-1.amazonaws.com/model/anthropic.claude-3-5-sonnet-20241022-v2:0/invoke"
      method: "POST"
      body:
        system: "={{ $node['Load Rung Prompt'].json.system_prompt }}"
        messages:
          - role: "user"
            content: "Analyze this pre-session voice memo transcript for clinical insights:\n\n{{ $json.transcript }}"
        max_tokens: 4096
        temperature: 0.7
    position: [1300, 300]

  # 9. Perplexity Research (Parallel Branch C)
  - name: "Research Lookup"
    type: "n8n-nodes-base.httpRequest"
    parameters:
      url: "https://api.perplexity.ai/chat/completions"
      method: "POST"
      headers:
        Authorization: "Bearer {{ $credentials.perplexityApiKey }}"
      body:
        model: "llama-3.1-sonar-large-128k-online"
        messages:
          - role: "user"
            content: "Find evidence-based frameworks and citations for: {{ $json.anonymized_query }}"
    position: [1300, 500]

  # 10. Merge Results
  - name: "Merge Results"
    type: "n8n-nodes-base.merge"
    parameters:
      mode: "combine"
      mergeByFields: "session_id"
    position: [1500, 300]

  # 11. Generate Clinical Brief (Rung Output)
  - name: "Generate Clinical Brief"
    type: "n8n-nodes-base.httpRequest"
    parameters:
      url: "https://bedrock-runtime.us-east-1.amazonaws.com/model/anthropic.claude-3-5-sonnet-20241022-v2:0/invoke"
      method: "POST"
      body:
        system: "You are Rung, a clinical psychology AI assistant. Generate a clinical brief for the therapist."
        messages:
          - role: "user"
            content: |
              Based on the following analysis, context, and research, generate a clinical brief:

              TRANSCRIPT ANALYSIS:
              {{ $json.rung_analysis }}

              LONGITUDINAL CONTEXT:
              {{ $json.perceptor_context }}

              RESEARCH CITATIONS:
              {{ $json.research_results }}
        max_tokens: 4096
    position: [1700, 200]

  # 12. Generate Client Guide (Beth Output)
  - name: "Generate Client Guide"
    type: "n8n-nodes-base.httpRequest"
    parameters:
      url: "https://bedrock-runtime.us-east-1.amazonaws.com/model/anthropic.claude-3-5-sonnet-20241022-v2:0/invoke"
      method: "POST"
      body:
        system: "You are Beth, a warm and supportive psychology assistant. Generate a client preparation guide using accessible, non-clinical language."
        messages:
          - role: "user"
            content: |
              Based on the clinical analysis (but NOT using clinical jargon), generate a preparation guide for the client:

              KEY THEMES:
              {{ $json.themes }}

              RECOMMENDED EXERCISES:
              {{ $json.exercises }}
    position: [1700, 400]

  # 13. Store Clinical Brief
  - name: "Store Clinical Brief"
    type: "n8n-nodes-base.postgres"
    parameters:
      operation: "insert"
      table: "clinical_briefs"
      columns: "session_id, frameworks, patterns, risk_flags, citations, content_encrypted, agent_id, workflow_run_id"
    position: [1900, 200]

  # 14. Store Client Guide
  - name: "Store Client Guide"
    type: "n8n-nodes-base.postgres"
    parameters:
      operation: "insert"
      table: "client_guides"
      columns: "session_id, content_encrypted, exercises, psychoeducation_encrypted, agent_id, workflow_run_id"
    position: [1900, 400]

  # 15. Update Perceptor
  - name: "Update Perceptor"
    type: "n8n-nodes-base.httpRequest"
    parameters:
      url: "http://perceptor-mcp:8080/save"
      method: "POST"
      body:
        title: "Pre-Session Analysis - {{ $json.session_date }}"
        client_id: "={{ $json.client_id }}"
        content: "={{ $json.clinical_brief_summary }}"
    position: [1900, 300]

  # 16. Slack Notification
  - name: "Slack Notify"
    type: "n8n-nodes-base.slack"
    parameters:
      channel: "#rung-workflows"
      text: "Pre-session workflow complete for session {{ $json.session_id }}. Clinical brief and client guide ready."
      # NO PHI in notification
    position: [2100, 300]

  # 17. Update Session Status
  - name: "Update Session Status"
    type: "n8n-nodes-base.postgres"
    parameters:
      operation: "update"
      table: "sessions"
      updateKey: "session_id"
      columns: "status"
      values:
        status: "complete"
    position: [2100, 400]

connections:
  "Webhook Trigger":
    main:
      - - node: "Validate JWT"
  "Validate JWT":
    main:
      - - node: "Fetch S3 Audio"
  "Fetch S3 Audio":
    main:
      - - node: "Start Transcription"
  "Start Transcription":
    main:
      - - node: "Wait Transcription"
  "Wait Transcription":
    main:
      - - node: "Poll Transcription"
  "Poll Transcription":
    main:
      - - node: "Load Perceptor Context"
        - node: "Rung Analysis"
        - node: "Research Lookup"
  "Load Perceptor Context":
    main:
      - - node: "Merge Results"
  "Rung Analysis":
    main:
      - - node: "Merge Results"
  "Research Lookup":
    main:
      - - node: "Merge Results"
  "Merge Results":
    main:
      - - node: "Generate Clinical Brief"
        - node: "Generate Client Guide"
  "Generate Clinical Brief":
    main:
      - - node: "Store Clinical Brief"
  "Generate Client Guide":
    main:
      - - node: "Store Client Guide"
  "Store Clinical Brief":
    main:
      - - node: "Update Perceptor"
  "Store Client Guide":
    main:
      - - node: "Update Perceptor"
  "Update Perceptor":
    main:
      - - node: "Slack Notify"
        - node: "Update Session Status"
```

### Post-Session Workflow

```
Workflow: post_session_pipeline
Trigger: Webhook (POST /n8n/post-session)
Estimated Duration: 1-3 minutes

+-------------------------------------------------------------------+
|                    POST-SESSION WORKFLOW                           |
+-------------------------------------------------------------------+
|                                                                   |
|  [1] WEBHOOK TRIGGER                                              |
|      +-----------------+                                          |
|      | Receive Request |                                          |
|      | - session_id    |                                          |
|      | - notes         |                                          |
|      | - modalities    |                                          |
|      +--------+--------+                                          |
|               |                                                   |
|               v                                                   |
|  [2] VALIDATE & ENCRYPT                                           |
|      +-----------------+     +-----------------+                  |
|      | Validate JWT    |---->| Encrypt Notes   |                  |
|      |                 |     | (KMS)           |                  |
|      +-----------------+     +--------+--------+                  |
|                                       |                           |
|               +-----------------------+                           |
|               |                                                   |
|               v                                                   |
|  [3] FRAMEWORK EXTRACTION (RUNG)                                  |
|      +-----------------+                                          |
|      | Rung Agent      |                                          |
|      | - Extract       |                                          |
|      |   frameworks    |                                          |
|      | - Identify      |                                          |
|      |   patterns      |                                          |
|      +--------+--------+                                          |
|               |                                                   |
|               v                                                   |
|  [4] LOAD EXISTING PLAN                                           |
|      +-----------------+                                          |
|      | Fetch Current   |                                          |
|      | Development Plan|                                          |
|      | (if exists)     |                                          |
|      +--------+--------+                                          |
|               |                                                   |
|               v                                                   |
|  [5] SPRINT PLANNING (RUNG)                                       |
|      +-----------------+                                          |
|      | Generate/Update |                                          |
|      | Development     |                                          |
|      | Sprint Plan     |                                          |
|      +--------+--------+                                          |
|               |                                                   |
|               v                                                   |
|  [6] PERSIST                                                      |
|      +---------------------------+---------------------------+    |
|      |                           |                           |    |
|      v                           v                           v    |
|  +----------+             +----------+              +----------+  |
|  | Store    |             | Update   |              | Archive  |  |
|  | Session  |             | Dev Plan |              | to       |  |
|  | Notes    |             |          |              | Perceptor|  |
|  +----------+             +----------+              +----------+  |
|      |                           |                        |       |
|      +---------------------------+------------------------+       |
|                                  |                                |
|                                  v                                |
|  [7] NOTIFY                                                       |
|      +-----------------+                                          |
|      | Slack Notify    |                                          |
|      | (Status Only)   |                                          |
|      +-----------------+                                          |
|                                                                   |
+-------------------------------------------------------------------+
```

### Couples Merge Workflow

```
Workflow: couples_merge_pipeline
Trigger: Webhook (POST /n8n/couples-merge)
Estimated Duration: 1-2 minutes

+-------------------------------------------------------------------+
|                    COUPLES MERGE WORKFLOW                          |
+-------------------------------------------------------------------+
|                                                                   |
|  [1] WEBHOOK TRIGGER                                              |
|      +-----------------+                                          |
|      | Receive Request |                                          |
|      | - link_id       |                                          |
|      | - topic         |                                          |
|      +--------+--------+                                          |
|               |                                                   |
|               v                                                   |
|  [2] VALIDATE COUPLE LINK                                         |
|      +-----------------+                                          |
|      | Verify link     |                                          |
|      | exists & active |                                          |
|      +--------+--------+                                          |
|               |                                                   |
|               v                                                   |
|  [3] FETCH FRAMEWORK DATA (PARALLEL - ISOLATED)                   |
|      +---------------------------+---------------------------+    |
|      |                           |                           |    |
|      v                           v                           |    |
|  +----------------+       +----------------+                 |    |
|  | Partner A      |       | Partner B      |                 |    |
|  | Framework Only |       | Framework Only |                 |    |
|  | - NO raw notes |       | - NO raw notes |                 |    |
|  | - NO PHI       |       | - NO PHI       |                 |    |
|  +-------+--------+       +-------+--------+                 |    |
|          |                        |                          |    |
|          +------------------------+                          |    |
|                     |                                        |    |
|                     v                                        |    |
|  [4] TOPIC MATCHING                                          |    |
|      +-----------------+                                     |    |
|      | Detect Shared   |                                     |    |
|      | Topics/Patterns |                                     |    |
|      | (Framework Only)|                                     |    |
|      +--------+--------+                                     |    |
|               |                                              |    |
|               +----> No Match? ---> [Exit: No merge needed]  |    |
|               |                                              |    |
|               v                                              |    |
|  [5] FRAMEWORK MERGE (RUNG)                                  |    |
|      +-----------------+                                     |    |
|      | Merge at        |                                     |    |
|      | Framework Level |                                     |    |
|      | ONLY            |                                     |    |
|      |                 |                                     |    |
|      | CRITICAL:       |                                     |    |
|      | No raw client   |                                     |    |
|      | data crosses    |                                     |    |
|      +--------+--------+                                     |    |
|               |                                              |    |
|               v                                              |    |
|  [6] PERSIST MERGE                                           |    |
|      +-----------------+                                     |    |
|      | Store to        |                                     |    |
|      | framework_merges|                                     |    |
|      | table           |                                     |    |
|      +--------+--------+                                     |    |
|               |                                              |    |
|               v                                              |    |
|  [7] NOTIFY                                                  |    |
|      +-----------------+                                     |    |
|      | Slack Notify    |                                     |    |
|      +-----------------+                                     |    |
|                                                              |    |
+-------------------------------------------------------------------+

CRITICAL ISOLATION RULES FOR COUPLES MERGE:
-------------------------------------------
1. NEVER pass raw session notes between partner contexts
2. NEVER include direct quotes from individual sessions
3. ONLY merge abstract framework patterns (e.g., "attachment anxiety pattern")
4. Framework patterns must be generalized before merge
5. Audit log every merge operation for compliance
6. framework_only flag MUST be TRUE in all merge records
```

### Workflow Error Handling

```yaml
# Error Handling Pattern for all n8n workflows

error_handling:
  global:
    - type: "error_trigger"
      node: "Error Handler"
      actions:
        - log_to_cloudwatch
        - update_session_status_to_error
        - slack_notify_error  # No PHI in error message
        - retry_with_backoff  # Max 3 retries

  retry_policy:
    max_retries: 3
    backoff_type: "exponential"
    initial_delay_ms: 1000
    max_delay_ms: 30000
    retryable_errors:
      - "TIMEOUT"
      - "RATE_LIMIT"
      - "SERVICE_UNAVAILABLE"
    non_retryable_errors:
      - "VALIDATION_ERROR"
      - "AUTHENTICATION_ERROR"
      - "ENCRYPTION_ERROR"

  dead_letter:
    queue: "rung-dlq"
    retention_days: 14
    alert_threshold: 5  # Alert if 5+ failures in 1 hour
```

---

## Security Architecture

### Authentication & Authorization

```
+-------------------------------------------------------------------+
|                    AUTHENTICATION FLOW                             |
+-------------------------------------------------------------------+
|                                                                   |
|  [1] Therapist Login                                              |
|      +-----------------+                                          |
|      | Cognito Hosted  |                                          |
|      | UI / SDK        |                                          |
|      +--------+--------+                                          |
|               |                                                   |
|               v                                                   |
|  [2] Token Issuance                                               |
|      +-----------------+                                          |
|      | Cognito Issues  |                                          |
|      | - ID Token      |                                          |
|      | - Access Token  |                                          |
|      | - Refresh Token |                                          |
|      +--------+--------+                                          |
|               |                                                   |
|               v                                                   |
|  [3] API Request                                                  |
|      +-----------------+                                          |
|      | Client sends    |                                          |
|      | Authorization:  |                                          |
|      | Bearer <token>  |                                          |
|      +--------+--------+                                          |
|               |                                                   |
|               v                                                   |
|  [4] Gateway Validation                                           |
|      +-----------------+                                          |
|      | API Gateway     |                                          |
|      | Lambda          |                                          |
|      | Authorizer      |                                          |
|      +--------+--------+                                          |
|               |                                                   |
|               +---> Invalid? ---> 401 Unauthorized                |
|               |                                                   |
|               v                                                   |
|  [5] Resource Authorization                                       |
|      +-----------------+                                          |
|      | Check therapist |                                          |
|      | owns resource   |                                          |
|      | (client/session)|                                          |
|      +--------+--------+                                          |
|               |                                                   |
|               +---> Denied? ---> 403 Forbidden                    |
|               |                                                   |
|               v                                                   |
|  [6] Process Request                                              |
|                                                                   |
+-------------------------------------------------------------------+
```

### Authorization Model (RBAC)

```yaml
roles:
  therapist:
    description: "Licensed therapist with client caseload"
    permissions:
      - "clients:create"
      - "clients:read:own"
      - "clients:update:own"
      - "sessions:create"
      - "sessions:read:own"
      - "sessions:update:own"
      - "briefs:read:own"
      - "guides:read:own"
      - "couples:create"
      - "couples:read:own"
      - "couples:merge:own"

  practice_admin:
    description: "Practice administrator with oversight"
    inherits: "therapist"
    permissions:
      - "therapists:read:practice"
      - "audit:read:practice"
      - "reports:read:practice"

  system:
    description: "System processes (n8n, Lambda)"
    permissions:
      - "sessions:update:status"
      - "briefs:create"
      - "guides:create"
      - "context:read"
      - "context:write"
      - "audit:write"

resource_ownership:
  client:
    owner_field: "therapist_id"
    ownership_check: "jwt.sub == resource.therapist_id"

  session:
    owner_field: "client.therapist_id"
    ownership_check: "jwt.sub == resource.client.therapist_id"

  couple_link:
    owner_field: "therapist_id"
    ownership_check: "jwt.sub == resource.therapist_id"
```

### Encryption Architecture

```
+-------------------------------------------------------------------+
|                    ENCRYPTION LAYERS                               |
+-------------------------------------------------------------------+
|                                                                   |
|  LAYER 1: Transport Encryption                                    |
|  +---------------------------------------------------------------+|
|  | TLS 1.3 for all external communication                        ||
|  | mTLS for service-to-service (within VPC)                      ||
|  | Certificate pinning on mobile/web clients                     ||
|  +---------------------------------------------------------------+|
|                                                                   |
|  LAYER 2: Storage Encryption (At Rest)                            |
|  +---------------------------------------------------------------+|
|  | RDS: AWS-managed encryption (AES-256)                         ||
|  | S3: Server-Side Encryption with KMS (SSE-KMS)                 ||
|  | EBS: Encrypted volumes for Lambda/EC2                         ||
|  +---------------------------------------------------------------+|
|                                                                   |
|  LAYER 3: Field-Level Encryption (PHI Fields)                     |
|  +---------------------------------------------------------------+|
|  | Algorithm: AES-256-GCM                                        ||
|  | Key Management: AWS KMS                                       ||
|  | Key Hierarchy:                                                ||
|  |   CMK (Customer Master Key) - AWS managed                     ||
|  |     |                                                         ||
|  |     +-> Therapist DEK (Data Encryption Key)                   ||
|  |           |                                                   ||
|  |           +-> Client DEK (per-client key)                     ||
|  |                                                               ||
|  | Encrypted Fields:                                             ||
|  |   - therapist.name_encrypted                                  ||
|  |   - client.name_encrypted, dob_encrypted, metadata_encrypted  ||
|  |   - session.notes_encrypted                                   ||
|  |   - clinical_brief.content_encrypted                          ||
|  |   - client_guide.content_encrypted, psychoeducation_encrypted ||
|  |   - development_plan.goals_encrypted, exercises_encrypted     ||
|  |   - framework_merge.merged_content_encrypted                  ||
|  +---------------------------------------------------------------+|
|                                                                   |
|  LAYER 4: Application-Level Encryption                            |
|  +---------------------------------------------------------------+|
|  | Voice memos: Encrypted before S3 upload                       ||
|  | Transcripts: Encrypted before storage                         ||
|  | Agent context: Encrypted in Perceptor                         ||
|  +---------------------------------------------------------------+|
|                                                                   |
+-------------------------------------------------------------------+
```

### Audit Logging

```yaml
audit_events:
  # Authentication Events
  - event: "auth.login"
    fields: [actor_id, timestamp, ip_address, user_agent, result]

  - event: "auth.logout"
    fields: [actor_id, timestamp]

  - event: "auth.token_refresh"
    fields: [actor_id, timestamp, result]

  # Data Access Events
  - event: "client.create"
    fields: [actor_id, timestamp, client_id, result]

  - event: "client.read"
    fields: [actor_id, timestamp, client_id, fields_accessed, result]

  - event: "session.read"
    fields: [actor_id, timestamp, session_id, result]

  - event: "brief.read"
    fields: [actor_id, timestamp, brief_id, result]

  - event: "guide.read"
    fields: [actor_id, timestamp, guide_id, result]

  # Workflow Events
  - event: "workflow.pre_session.start"
    fields: [actor_id, timestamp, session_id, workflow_id]

  - event: "workflow.pre_session.complete"
    fields: [actor_id, timestamp, session_id, workflow_id, duration_ms]

  - event: "workflow.couples_merge.execute"
    fields: [actor_id, timestamp, link_id, topic, result]

  # PHI Access Events (HIPAA Required)
  - event: "phi.decrypt"
    fields: [actor_id, timestamp, resource_type, resource_id, fields_decrypted, purpose]

  - event: "phi.export"
    fields: [actor_id, timestamp, resource_type, resource_id, export_format, result]

audit_storage:
  primary: "RDS audit_logs table"
  backup: "CloudWatch Logs (encrypted)"
  retention: "7 years (HIPAA requirement)"

audit_alerts:
  - condition: "5+ failed auth attempts in 5 minutes"
    action: "Lock account, notify admin"

  - condition: "PHI access outside business hours"
    action: "Flag for review"

  - condition: "Bulk PHI export"
    action: "Notify admin immediately"
```

### Agent Isolation Security

```
+-------------------------------------------------------------------+
|                    AGENT ISOLATION MODEL                           |
+-------------------------------------------------------------------+
|                                                                   |
|  +-----------------------------+  +-----------------------------+ |
|  |     RUNG AGENT CONTEXT      |  |     BETH AGENT CONTEXT      | |
|  |     (Clinical Analysis)     |  |  (Client Communication)     | |
|  +-----------------------------+  +-----------------------------+ |
|  |                             |  |                             | |
|  | Inputs:                     |  | Inputs:                     | |
|  | - Transcripts               |  | - Themes (abstracted)       | |
|  | - Session notes             |  | - Exercise templates        | |
|  | - Clinical history          |  | - Psychoeducation lib       | |
|  | - Research citations        |  | - Client language level     | |
|  |                             |  |                             | |
|  | Outputs:                    |  | Outputs:                    | |
|  | - Clinical briefs           |  | - Client guides             | |
|  | - Framework analysis        |  | - Exercises                 | |
|  | - Risk assessments          |  | - Accessible explanations   | |
|  | - Pattern detection         |  | - Progress tracking         | |
|  |                             |  |                             | |
|  +-------------+---------------+  +---------------+-------------+ |
|                |                                  |               |
|                |        FIREWALL RULES            |               |
|                +----------------------------------+               |
|                                                                   |
|  ISOLATION RULES:                                                 |
|  1. Beth NEVER receives raw session transcripts                   |
|  2. Beth NEVER receives clinical terminology                      |
|  3. Beth receives ONLY:                                           |
|     - Abstracted themes (e.g., "communication challenges")        |
|     - Exercise recommendations (pre-defined library)              |
|     - Client's preferred language level                           |
|  4. Rung NEVER generates client-facing content directly           |
|  5. All cross-agent data must pass through abstraction layer      |
|                                                                   |
|  IMPLEMENTATION:                                                  |
|  - Separate Bedrock inference calls (different system prompts)    |
|  - Different encryption keys per agent context                    |
|  - Audit logging of all agent inputs/outputs                      |
|  - Schema validation on agent boundaries                          |
|                                                                   |
+-------------------------------------------------------------------+
```

### HIPAA Compliance Checklist

```yaml
hipaa_compliance:

  administrative_safeguards:
    - control: "Security Management Process"
      implementation: "Risk assessments, security policies, sanctions"
      status: "Designed"

    - control: "Workforce Security"
      implementation: "Background checks, role-based access"
      status: "Designed"

    - control: "Information Access Management"
      implementation: "RBAC, minimum necessary access"
      status: "Designed"

    - control: "Security Awareness Training"
      implementation: "Therapist onboarding, annual refresh"
      status: "Planned"

    - control: "Contingency Plan"
      implementation: "Backup, disaster recovery, emergency mode"
      status: "Designed"

  physical_safeguards:
    - control: "Facility Access Controls"
      implementation: "AWS physical security (SOC2, HIPAA BAA)"
      status: "Inherited from AWS"

    - control: "Workstation Security"
      implementation: "Encrypted endpoints, auto-lock"
      status: "Policy required"

  technical_safeguards:
    - control: "Access Control"
      implementation: "Cognito auth, JWT, RBAC"
      status: "Designed"

    - control: "Audit Controls"
      implementation: "CloudWatch, RDS audit_logs, 7-year retention"
      status: "Designed"

    - control: "Integrity Controls"
      implementation: "Checksums, version control, change detection"
      status: "Designed"

    - control: "Transmission Security"
      implementation: "TLS 1.3, mTLS, VPN for admin"
      status: "Designed"

    - control: "Encryption"
      implementation: "AES-256-GCM, KMS, field-level PHI encryption"
      status: "Designed"

  business_associate_agreements:
    - vendor: "AWS"
      services: "RDS, S3, Lambda, Bedrock, Cognito, KMS, Transcribe"
      baa_status: "Required before production"

    - vendor: "n8n"
      services: "Workflow orchestration"
      baa_status: "Self-hosted required OR n8n cloud with BAA"

    - vendor: "Perplexity"
      services: "Research API"
      baa_status: "NOT COVERED - queries must be anonymized"
      mitigation: "Strip all PHI before API calls"
```

---

## Infrastructure Components

### AWS Infrastructure

```
+-------------------------------------------------------------------+
|                    AWS INFRASTRUCTURE                              |
+-------------------------------------------------------------------+
|                                                                   |
|  REGION: us-east-1 (Primary)                                      |
|                                                                   |
|  +---------------------------------------------------------------+|
|  |                         VPC                                   ||
|  |  CIDR: 10.0.0.0/16                                            ||
|  |                                                               ||
|  |  +-------------------------+  +-------------------------+     ||
|  |  |    Public Subnets       |  |    Private Subnets      |     ||
|  |  |    10.0.1.0/24 (AZ-a)   |  |    10.0.10.0/24 (AZ-a)  |     ||
|  |  |    10.0.2.0/24 (AZ-b)   |  |    10.0.20.0/24 (AZ-b)  |     ||
|  |  +-------------------------+  +-------------------------+     ||
|  |           |                            |                      ||
|  |           v                            v                      ||
|  |  +----------------+           +------------------+             ||
|  |  | NAT Gateway    |           | RDS PostgreSQL   |             ||
|  |  | (for Lambda    |           | (Multi-AZ)       |             ||
|  |  |  egress)       |           | - db.r6g.large   |             ||
|  |  +----------------+           | - Encrypted      |             ||
|  |                               | - 100GB gp3      |             ||
|  |                               +------------------+             ||
|  |                                                               ||
|  +---------------------------------------------------------------+|
|                                                                   |
|  COMPUTE:                                                         |
|  +---------------------------------------------------------------+|
|  | Lambda Functions (in VPC):                                    ||
|  | - api-authorizer     (128MB, 10s timeout)                     ||
|  | - voice-processor    (1024MB, 300s timeout)                   ||
|  | - bedrock-invoker    (512MB, 120s timeout)                    ||
|  | - encryption-service (256MB, 30s timeout)                     ||
|  | - audit-logger       (128MB, 10s timeout)                     ||
|  +---------------------------------------------------------------+|
|                                                                   |
|  STORAGE:                                                         |
|  +---------------------------------------------------------------+|
|  | S3 Buckets:                                                   ||
|  | - rung-voice-memos      (SSE-KMS, versioning, lifecycle)      ||
|  | - rung-transcripts      (SSE-KMS, versioning)                 ||
|  | - rung-exports          (SSE-KMS, versioning)                 ||
|  | - rung-n8n-data         (SSE-KMS, n8n workflow storage)       ||
|  +---------------------------------------------------------------+|
|                                                                   |
|  SECURITY:                                                        |
|  +---------------------------------------------------------------+|
|  | Cognito User Pool:                                            ||
|  | - MFA required                                                ||
|  | - Password policy (12+ chars, complexity)                     ||
|  | - Token expiration (1hr access, 30d refresh)                  ||
|  |                                                               ||
|  | KMS Keys:                                                     ||
|  | - rung-master-key       (CMK for all encryption)              ||
|  | - rung-rds-key          (RDS encryption)                      ||
|  | - rung-s3-key           (S3 encryption)                       ||
|  |                                                               ||
|  | WAF:                                                          ||
|  | - Rate limiting (100 req/min per IP)                          ||
|  | - SQL injection protection                                    ||
|  | - XSS protection                                              ||
|  | - Geo-blocking (US only initially)                            ||
|  +---------------------------------------------------------------+|
|                                                                   |
|  AI/ML:                                                           |
|  +---------------------------------------------------------------+|
|  | Bedrock:                                                      ||
|  | - Model: anthropic.claude-3-5-sonnet-20241022-v2:0            ||
|  | - Provisioned throughput: On-demand initially                 ||
|  |                                                               ||
|  | Transcribe Medical:                                           ||
|  | - Real-time and batch transcription                           ||
|  | - Medical vocabulary enabled                                  ||
|  +---------------------------------------------------------------+|
|                                                                   |
|  MONITORING:                                                      |
|  +---------------------------------------------------------------+|
|  | CloudWatch:                                                   ||
|  | - Logs (all Lambda, API Gateway, n8n)                         ||
|  | - Metrics (custom + AWS)                                      ||
|  | - Alarms (error rate, latency, costs)                         ||
|  |                                                               ||
|  | X-Ray:                                                        ||
|  | - Distributed tracing                                         ||
|  | - Service map                                                 ||
|  +---------------------------------------------------------------+|
|                                                                   |
+-------------------------------------------------------------------+
```

### n8n Deployment

```yaml
n8n_deployment:
  option: "Self-hosted on EC2"  # Required for HIPAA BAA coverage

  infrastructure:
    instance_type: "t3.medium"
    storage: "100GB gp3 (encrypted)"
    ami: "Amazon Linux 2023"

  networking:
    vpc: "rung-vpc"
    subnet: "private-subnet-a"
    security_group:
      inbound:
        - port: 5678
          source: "ALB security group"
      outbound:
        - port: 443
          destination: "0.0.0.0/0"  # For AWS APIs
        - port: 5432
          destination: "RDS security group"

  high_availability:
    auto_scaling_group:
      min: 1
      max: 2
      desired: 1
    health_check: "/healthz"

  configuration:
    N8N_ENCRYPTION_KEY: "${secrets_manager.n8n_encryption_key}"
    N8N_BASIC_AUTH_ACTIVE: "true"
    N8N_BASIC_AUTH_USER: "${secrets_manager.n8n_admin_user}"
    N8N_BASIC_AUTH_PASSWORD: "${secrets_manager.n8n_admin_password}"
    DB_TYPE: "postgresdb"
    DB_POSTGRESDB_HOST: "${rds_endpoint}"
    DB_POSTGRESDB_DATABASE: "n8n"
    DB_POSTGRESDB_USER: "n8n_user"
    DB_POSTGRESDB_PASSWORD: "${secrets_manager.n8n_db_password}"
    EXECUTIONS_DATA_SAVE_ON_ERROR: "all"
    EXECUTIONS_DATA_SAVE_ON_SUCCESS: "all"
    EXECUTIONS_DATA_SAVE_MANUAL_EXECUTIONS: "true"

  backup:
    rds_snapshots: "Daily, 7-day retention"
    workflow_export: "Daily to S3"
```

### Perceptor MCP Integration

```yaml
perceptor_integration:
  deployment: "Sidecar container in n8n EC2"

  configuration:
    PERCEPTOR_STORAGE: "s3://rung-perceptor-contexts"
    PERCEPTOR_ENCRYPTION: "AES-256-GCM"
    PERCEPTOR_KMS_KEY: "${kms.perceptor_key_arn}"

  api_endpoints:
    - endpoint: "/load"
      method: "POST"
      purpose: "Load client context for session"

    - endpoint: "/save"
      method: "POST"
      purpose: "Save session summary to context"

    - endpoint: "/search"
      method: "POST"
      purpose: "Search across client contexts"

  data_structure:
    context_document:
      id: "client_{client_id}_session_{session_id}"
      title: "Session Summary - {date}"
      tags: ["client:{client_id}", "therapist:{therapist_id}", "type:{session_type}"]
      content_encrypted: true
      metadata:
        client_id: "uuid"
        session_id: "uuid"
        frameworks_used: ["list"]
        patterns_identified: ["list"]
        created_at: "timestamp"
```

### Component Summary Table

| Component | Service | Configuration | HIPAA Status |
|-----------|---------|---------------|--------------|
| API Gateway | AWS API Gateway | REST API, Lambda authorizer | BAA Required |
| Authentication | Cognito | User pool, MFA required | BAA Required |
| Database | RDS PostgreSQL | db.r6g.large, Multi-AZ, encrypted | BAA Required |
| Object Storage | S3 | SSE-KMS, versioning, lifecycle | BAA Required |
| LLM Inference | Bedrock (Claude) | claude-3-5-sonnet-20241022-v2:0 | BAA Required |
| Transcription | Transcribe Medical | Medical vocabulary, batch | BAA Required |
| Orchestration | n8n (self-hosted) | EC2, private subnet | Self-hosted |
| Context Store | Perceptor MCP | Sidecar, S3 backend | Custom |
| Research | Perplexity API | Anonymized queries only | NOT COVERED |
| Notifications | Slack | Status only, no PHI | NOT COVERED |
| Key Management | KMS | CMK, DEK hierarchy | BAA Required |
| Monitoring | CloudWatch | Logs, metrics, alarms | BAA Required |
| Tracing | X-Ray | Distributed tracing | BAA Required |

---

## Implementation Phases

### Phase Overview

```
+-------------------------------------------------------------------+
|                    IMPLEMENTATION ROADMAP                          |
+-------------------------------------------------------------------+
|                                                                   |
|  Phase 1: Foundation (Weeks 1-4)                                  |
|  +---------------------------------------------------------------+|
|  | - Infrastructure setup (VPC, RDS, S3, Cognito)                ||
|  | - Core data models and migrations                             ||
|  | - Basic API endpoints (clients, sessions)                     ||
|  | - n8n deployment and configuration                            ||
|  | - KMS key hierarchy setup                                     ||
|  +---------------------------------------------------------------+|
|                           |                                       |
|                           v                                       |
|  Phase 2: Pre-Session Pipeline (Weeks 5-8)                        |
|  +---------------------------------------------------------------+|
|  | - Voice memo upload and S3 storage                            ||
|  | - AWS Transcribe Medical integration                          ||
|  | - Rung agent implementation (Bedrock)                         ||
|  | - Perplexity research integration                             ||
|  | - Clinical brief generation                                   ||
|  | - Beth agent implementation (Bedrock)                         ||
|  | - Client guide generation                                     ||
|  | - Pre-session n8n workflow                                    ||
|  +---------------------------------------------------------------+|
|                           |                                       |
|                           v                                       |
|  Phase 3: Post-Session Pipeline (Weeks 9-11)                      |
|  +---------------------------------------------------------------+|
|  | - Session notes submission                                    ||
|  | - Framework extraction logic                                  ||
|  | - Development sprint planning                                 ||
|  | - Perceptor MCP integration                                   ||
|  | - Post-session n8n workflow                                   ||
|  +---------------------------------------------------------------+|
|                           |                                       |
|                           v                                       |
|  Phase 4: Couples Merge (Weeks 12-14)                             |
|  +---------------------------------------------------------------+|
|  | - Couple linking API                                          ||
|  | - Framework isolation layer                                   ||
|  | - Topic matching algorithm                                    ||
|  | - Merge workflow with strict isolation                        ||
|  | - Couples merge n8n workflow                                  ||
|  +---------------------------------------------------------------+|
|                           |                                       |
|                           v                                       |
|  Phase 5: Security & Compliance (Weeks 15-17)                     |
|  +---------------------------------------------------------------+|
|  | - Comprehensive audit logging                                 ||
|  | - Penetration testing                                         ||
|  | - HIPAA compliance audit                                      ||
|  | - BAA execution with AWS                                      ||
|  | - Security documentation                                      ||
|  +---------------------------------------------------------------+|
|                           |                                       |
|                           v                                       |
|  Phase 6: Production Readiness (Weeks 18-20)                      |
|  +---------------------------------------------------------------+|
|  | - Load testing                                                ||
|  | - Disaster recovery testing                                   ||
|  | - Monitoring and alerting setup                               ||
|  | - Runbook documentation                                       ||
|  | - Beta therapist onboarding                                   ||
|  +---------------------------------------------------------------+|
|                                                                   |
+-------------------------------------------------------------------+
```

### Phase 1: Foundation (Weeks 1-4)

```yaml
phase_1:
  name: "Foundation"
  duration: "4 weeks"

  milestones:
    - milestone: "Infrastructure Provisioned"
      week: 1
      deliverables:
        - "VPC with public/private subnets"
        - "RDS PostgreSQL instance (encrypted)"
        - "S3 buckets with SSE-KMS"
        - "Cognito user pool"
        - "KMS keys created"
      completion_criteria:
        - "All resources created in Terraform"
        - "Connectivity verified between components"
        - "Encryption verified on all storage"

    - milestone: "Database Schema Deployed"
      week: 2
      deliverables:
        - "All tables created (therapists, clients, sessions, etc.)"
        - "Indexes created"
        - "Encryption functions deployed"
      completion_criteria:
        - "Migrations run successfully"
        - "Sample data inserted and encrypted"
        - "Queries return expected results"

    - milestone: "Basic API Operational"
      week: 3
      deliverables:
        - "API Gateway configured"
        - "Lambda authorizer deployed"
        - "CRUD endpoints for clients"
        - "CRUD endpoints for sessions"
      completion_criteria:
        - "Postman collection passes all tests"
        - "Auth flow works end-to-end"
        - "Audit logs generated for all operations"

    - milestone: "n8n Operational"
      week: 4
      deliverables:
        - "n8n deployed on EC2"
        - "Connected to RDS"
        - "Basic health check workflow"
        - "Slack integration configured"
      completion_criteria:
        - "n8n UI accessible via ALB"
        - "Test workflow executes successfully"
        - "Slack notification received"

  tests:
    - name: "Infrastructure smoke test"
      command: "pytest tests/infrastructure/"
      criteria: "All 15 tests pass"

    - name: "API integration test"
      command: "pytest tests/api/"
      criteria: "All 25 tests pass"

    - name: "Encryption verification"
      command: "pytest tests/security/encryption_test.py"
      criteria: "All fields encrypted correctly"
```

### Phase 2: Pre-Session Pipeline (Weeks 5-8)

```yaml
phase_2:
  name: "Pre-Session Pipeline"
  duration: "4 weeks"
  dependencies: ["Phase 1 complete"]

  milestones:
    - milestone: "Voice Processing Operational"
      week: 5
      deliverables:
        - "Voice memo upload endpoint"
        - "S3 upload with client-side encryption"
        - "AWS Transcribe job triggering"
        - "Transcript retrieval"
      completion_criteria:
        - "5-minute voice memo transcribed in <3 minutes"
        - "Medical terminology correctly transcribed"
        - "Transcript stored encrypted in S3"

    - milestone: "Rung Agent Operational"
      week: 6
      deliverables:
        - "Rung system prompt configured"
        - "Bedrock inference integration"
        - "Clinical analysis output parsing"
        - "Framework extraction logic"
      completion_criteria:
        - "Analysis generated for sample transcript"
        - "Frameworks correctly identified"
        - "Risk flags detected when present"

    - milestone: "Research Integration"
      week: 7
      deliverables:
        - "Perplexity API integration"
        - "Query anonymization function"
        - "Citation parsing and storage"
      completion_criteria:
        - "Research returns relevant citations"
        - "No PHI in Perplexity requests (verified)"
        - "Citations correctly formatted"

    - milestone: "Pre-Session Workflow Complete"
      week: 8
      deliverables:
        - "Beth agent implementation"
        - "Client guide generation"
        - "Full n8n workflow"
        - "Status endpoint"
      completion_criteria:
        - "End-to-end workflow executes in <5 minutes"
        - "Clinical brief matches expected format"
        - "Client guide uses non-clinical language"
        - "Slack notification received on completion"

  tests:
    - name: "Voice processing test"
      command: "pytest tests/voice/"
      criteria: "All 10 tests pass"

    - name: "Rung agent test"
      command: "pytest tests/agents/rung_test.py"
      criteria: "All 15 tests pass"

    - name: "Pre-session E2E test"
      command: "pytest tests/workflows/pre_session_test.py"
      criteria: "Full workflow completes successfully"
```

### Phase 3: Post-Session Pipeline (Weeks 9-11)

```yaml
phase_3:
  name: "Post-Session Pipeline"
  duration: "3 weeks"
  dependencies: ["Phase 2 complete"]

  milestones:
    - milestone: "Notes Processing"
      week: 9
      deliverables:
        - "Notes submission endpoint"
        - "Notes encryption"
        - "Framework extraction from notes"
      completion_criteria:
        - "Notes encrypted and stored"
        - "Frameworks correctly extracted"

    - milestone: "Development Planning"
      week: 10
      deliverables:
        - "Sprint planning logic"
        - "Goal generation"
        - "Exercise recommendation"
        - "Progress tracking model"
      completion_criteria:
        - "Sprint plan generated"
        - "Goals are SMART format"
        - "Exercises match identified frameworks"

    - milestone: "Post-Session Workflow Complete"
      week: 11
      deliverables:
        - "Perceptor context saving"
        - "Full n8n workflow"
        - "Archive functionality"
      completion_criteria:
        - "Context saved to Perceptor"
        - "Longitudinal data retrievable"
        - "Full workflow executes in <3 minutes"

  tests:
    - name: "Post-session E2E test"
      command: "pytest tests/workflows/post_session_test.py"
      criteria: "Full workflow completes successfully"

    - name: "Perceptor integration test"
      command: "pytest tests/perceptor/"
      criteria: "Context save/load works correctly"
```

### Phase 4: Couples Merge (Weeks 12-14)

```yaml
phase_4:
  name: "Couples Merge"
  duration: "3 weeks"
  dependencies: ["Phase 3 complete"]

  milestones:
    - milestone: "Couple Linking"
      week: 12
      deliverables:
        - "Couple link creation endpoint"
        - "Link validation (same therapist)"
        - "Link status management"
      completion_criteria:
        - "Couples can be linked"
        - "Invalid links rejected"

    - milestone: "Framework Isolation"
      week: 13
      deliverables:
        - "Framework-only data extraction"
        - "PHI stripping verification"
        - "Topic matching algorithm"
      completion_criteria:
        - "No raw notes in framework data"
        - "Topics correctly matched"
        - "Isolation verified by security review"

    - milestone: "Merge Workflow Complete"
      week: 14
      deliverables:
        - "Full couples merge n8n workflow"
        - "Merged insights generation"
        - "Audit logging for merges"
      completion_criteria:
        - "Merge produces useful insights"
        - "No PHI crosses client boundaries (verified)"
        - "Full audit trail exists"

  tests:
    - name: "Couples isolation test"
      command: "pytest tests/security/couples_isolation_test.py"
      criteria: "All isolation rules enforced"

    - name: "Couples merge E2E test"
      command: "pytest tests/workflows/couples_merge_test.py"
      criteria: "Merge workflow completes successfully"
```

### Phase 5: Security & Compliance (Weeks 15-17)

```yaml
phase_5:
  name: "Security & Compliance"
  duration: "3 weeks"
  dependencies: ["Phase 4 complete"]

  milestones:
    - milestone: "Audit System Complete"
      week: 15
      deliverables:
        - "Comprehensive audit logging"
        - "Audit log analysis tools"
        - "Anomaly detection alerts"
      completion_criteria:
        - "All HIPAA-required events logged"
        - "7-year retention configured"
        - "Alerts trigger correctly"

    - milestone: "Security Testing"
      week: 16
      deliverables:
        - "Penetration test report"
        - "Vulnerability remediation"
        - "Security documentation"
      completion_criteria:
        - "No critical/high vulnerabilities"
        - "All medium vulnerabilities remediated or accepted"

    - milestone: "HIPAA Compliance"
      week: 17
      deliverables:
        - "HIPAA compliance checklist completed"
        - "AWS BAA executed"
        - "Risk assessment document"
        - "Policies and procedures"
      completion_criteria:
        - "All HIPAA controls addressed"
        - "BAA signed with AWS"
        - "Documentation complete"

  tests:
    - name: "Security scan"
      command: "OWASP ZAP scan"
      criteria: "No critical/high findings"

    - name: "Compliance checklist"
      command: "Manual review"
      criteria: "All 45 controls addressed"
```

### Phase 6: Production Readiness (Weeks 18-20)

```yaml
phase_6:
  name: "Production Readiness"
  duration: "3 weeks"
  dependencies: ["Phase 5 complete"]

  milestones:
    - milestone: "Performance Validated"
      week: 18
      deliverables:
        - "Load test results"
        - "Performance optimizations"
        - "Capacity planning document"
      completion_criteria:
        - "100 concurrent users supported"
        - "P95 latency <5s for workflows"
        - "No memory leaks identified"

    - milestone: "DR Validated"
      week: 19
      deliverables:
        - "Disaster recovery runbook"
        - "DR test execution"
        - "RTO/RPO documented"
      completion_criteria:
        - "RTO <4 hours achieved"
        - "RPO <1 hour achieved"
        - "DR test successful"

    - milestone: "Beta Launch"
      week: 20
      deliverables:
        - "Beta therapist onboarding"
        - "Monitoring dashboards"
        - "Support runbooks"
        - "Feedback collection"
      completion_criteria:
        - "3-5 beta therapists onboarded"
        - "No critical issues in first week"
        - "Feedback mechanism operational"

  tests:
    - name: "Load test"
      command: "k6 run load_test.js"
      criteria: "100 VUs, <5% error rate"

    - name: "DR test"
      command: "Manual execution"
      criteria: "Recovery within 4 hours"
```

---

## Appendix

### A. Technology Stack Summary

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| API Gateway | AWS API Gateway | - | Request routing |
| Auth | AWS Cognito | - | Identity management |
| Compute | AWS Lambda | Python 3.11 | Serverless functions |
| Database | PostgreSQL | 15 | Primary data store |
| Object Store | AWS S3 | - | Binary storage |
| Orchestration | n8n | 1.x | Workflow automation |
| LLM | AWS Bedrock | Claude 3.5 Sonnet | AI inference |
| Transcription | AWS Transcribe | Medical | Voice-to-text |
| Research | Perplexity API | - | Evidence lookup |
| Context | Perceptor MCP | - | Longitudinal tracking |
| Encryption | AWS KMS | - | Key management |
| Monitoring | CloudWatch | - | Logs and metrics |
| Tracing | AWS X-Ray | - | Distributed tracing |

### B. Environment Variables

```bash
# Application
RUNG_ENV=production
RUNG_LOG_LEVEL=INFO
RUNG_API_VERSION=v1

# AWS
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012

# Database
DB_HOST=rung-db.cluster-xxx.us-east-1.rds.amazonaws.com
DB_PORT=5432
DB_NAME=rung
DB_USER=rung_app
# DB_PASSWORD in Secrets Manager

# Cognito
COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
COGNITO_CLIENT_ID=XXXXXXXXXXXXXXXXXXXXXXXXXX

# KMS
KMS_MASTER_KEY_ARN=arn:aws:kms:us-east-1:123456789012:key/xxx

# Bedrock
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0

# Perplexity
# PERPLEXITY_API_KEY in Secrets Manager

# n8n
N8N_WEBHOOK_BASE_URL=https://n8n.rung.health
# N8N_ENCRYPTION_KEY in Secrets Manager

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx
```

### C. API Rate Limits

| Endpoint | Rate Limit | Burst |
|----------|------------|-------|
| /sessions/*/voice-memo | 10/min | 20 |
| /sessions/*/notes | 30/min | 50 |
| /clients | 100/min | 150 |
| /sessions | 100/min | 150 |
| /couples/*/merge | 5/min | 10 |
| Status endpoints | 200/min | 300 |

### D. Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| RUNG_001 | 400 | Invalid request body |
| RUNG_002 | 400 | Invalid file format (voice memo) |
| RUNG_003 | 401 | Authentication required |
| RUNG_004 | 401 | Token expired |
| RUNG_005 | 403 | Access denied to resource |
| RUNG_006 | 404 | Resource not found |
| RUNG_007 | 409 | Workflow already in progress |
| RUNG_008 | 413 | File too large |
| RUNG_009 | 425 | Resource not ready (workflow pending) |
| RUNG_010 | 429 | Rate limit exceeded |
| RUNG_011 | 500 | Internal server error |
| RUNG_012 | 502 | Upstream service error (Bedrock, Perplexity) |
| RUNG_013 | 503 | Service temporarily unavailable |

---

*Document generated by Backend Architect. Last updated: 2026-01-31*
