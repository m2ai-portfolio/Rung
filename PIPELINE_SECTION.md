```
Pipeline: pre_session.py
Trigger: FastAPI endpoint POST /sessions/{id}/voice-memo
Estimated Duration: 2-5 minutes
Implementation: src/pipelines/pre_session.py

+-------------------------------------------------------------------+
|                    PRE-SESSION PIPELINE                            |
+-------------------------------------------------------------------+
|                                                                   |
|  [1] FETCH TRANSCRIPT                                             |
|      +-----------------+                                          |
|      | Load Session    |                                          |
|      | - session_id    |                                          |
|      | - transcript_s3 |                                          |
|      | - client_id     |                                          |
|      +--------+--------+                                          |
|               |                                                   |
|               v                                                   |
|  [2] PARALLEL PROCESSING (asyncio.gather)                         |
|      +---------------------------+---------------------------+    |
|      |                           |                           |    |
|      v                           v                           |    |
|  +----------+             +----------+                       |    |
|  | Rung     |             | Perplexity|                      |    |
|  | Agent    |             | Research  |                      |    |
|  | Analysis |             | Lookup    |                      |    |
|  | (Bedrock)|             | (anonymized)|                    |    |
|  +----+-----+             +----+------+                      |    |
|       |                        |                             |    |
|       +------------------------+                             |    |
|                                |                             |    |
|                                v                             |    |
|  [3] ABSTRACTION LAYER                                       |    |
|      +-----------------+                                     |    |
|      | Strip PHI       |                                     |    |
|      | Extract Themes  |                                     |    |
|      | (Rung → Beth)   |                                     |    |
|      +--------+--------+                                     |    |
|               |                                              |    |
|               v                                              |    |
|  [4] BETH CLIENT GUIDE                                       |    |
|      +-----------------+                                     |    |
|      | Generate Guide  |                                     |    |
|      | (Bedrock)       |                                     |    |
|      +--------+--------+                                     |    |
|               |                                              |    |
|               v                                              |    |
|  [5] PERSIST & AUDIT                                         |    |
|      +---------------------------------------------------+   |    |
|      | Store clinical_briefs | Store client_guides       |   |    |
|      | (RDS with encryption) | (RDS with encryption)     |   |    |
|      +---------------------------------------------------+   |    |
|               |                                              |    |
|               v                                              |    |
|  [6] NOTIFY & COMPLETE                                       |    |
|      +-----------------+                                     |    |
|      | Audit Log       |                                     |    |
|      | Update Pipeline |                                     |    |
|      | Status: Complete|                                     |    |
|      | Slack Notify    |                                     |    |
|      +-----------------+                                     |    |
|                                                              |    |
+-------------------------------------------------------------------+
```

### Pre-Session Pipeline Implementation

```python
# src/pipelines/pre_session.py

async def run_pre_session_pipeline(
    session_id: str,
    pipeline_id: str,
    session_factory,
    *,
    transcription_service: Optional[TranscriptionService] = None,
    rung_agent: Optional[RungAgent] = None,
    research_service: Optional[ResearchService] = None,
    abstraction_layer: Optional[AbstractionLayer] = None,
    beth_agent: Optional[BethAgent] = None,
    audit_service: Optional[AuditService] = None,
) -> None:
    """Execute pre-session analysis pipeline.

    Stages:
    1. fetch_transcript - Load transcript from S3
    2. rung_analysis - Clinical analysis (Rung agent + Research parallel)
    3. abstraction - Strip PHI for Beth agent
    4. beth_guide - Generate client-facing guide
    5. persist - Store to database with encryption
    6. complete - Audit log and status update
    """

    # Stage 1: Fetch transcript
    transcript = await ts.get_transcript(transcript_s3_key)

    # Stage 2: Parallel Rung + Research
    rung_output, research_results = await asyncio.gather(
        rung.analyze(transcript, client_id),
        research.search_frameworks(query, anonymize=True)
    )

    # Stage 3: Abstraction layer
    abstracted_themes = abstraction.abstract_for_beth(rung_output)

    # Stage 4: Beth client guide
    client_guide = await beth.generate_guide(
        themes=abstracted_themes,
        research=research_results
    )

    # Stage 5: Persist with encryption
    await store_clinical_brief(rung_output, session_id)
    await store_client_guide(client_guide, session_id)

    # Stage 6: Complete with audit
    await audit.log_pipeline_complete(pipeline_id, session_id)
    await complete_pipeline(pipeline_id, PipelineStatus.COMPLETE)
```

### Post-Session Pipeline

```
Pipeline: post_session.py
Trigger: FastAPI endpoint POST /sessions/{id}/notes
Estimated Duration: 1-3 minutes
Implementation: src/pipelines/post_session.py

+-------------------------------------------------------------------+
|                    POST-SESSION PIPELINE                           |
+-------------------------------------------------------------------+
|                                                                   |
|  [1] LOAD SESSION NOTES                                           |
|      +-----------------+                                          |
|      | Decrypt Notes   |                                          |
|      | Extract Client  |                                          |
|      +--------+--------+                                          |
|               |                                                   |
|               v                                                   |
|  [2] FRAMEWORK EXTRACTION                                         |
|      +-----------------+                                          |
|      | Extract         |                                          |
|      | Frameworks      |                                          |
|      | Modalities      |                                          |
|      | Patterns        |                                          |
|      +--------+--------+                                          |
|               |                                                   |
|               v                                                   |
|  [3] LOAD CONTEXT                                                 |
|      +-----------------+                                          |
|      | Get Previous    |                                          |
|      | Development Plan|                                          |
|      | Session History |                                          |
|      +--------+--------+                                          |
|               |                                                   |
|               v                                                   |
|  [4] GENERATE DEVELOPMENT PLAN                                    |
|      +-----------------+                                          |
|      | Sprint Planning |                                          |
|      | SMART Goals     |                                          |
|      | Exercise Match  |                                          |
|      +--------+--------+                                          |
|               |                                                   |
|               v                                                   |
|  [5] PERSIST & COMPLETE                                           |
|      +-----------------+                                          |
|      | Store Plan      |                                          |
|      | Update Progress |                                          |
|      | Audit Log       |                                          |
|      | Slack Notify    |                                          |
|      +-----------------+                                          |
|                                                                   |
+-------------------------------------------------------------------+
```

### Couples Merge Pipeline

```
Pipeline: couples_merge.py
Trigger: FastAPI endpoint POST /couples/{linkId}/merge
Estimated Duration: 2-4 minutes
Implementation: src/pipelines/couples_merge.py

+-------------------------------------------------------------------+
|                    COUPLES MERGE PIPELINE                          |
+-------------------------------------------------------------------+
|                                                                   |
|  [1] VALIDATE COUPLE LINK                                         |
|      +-----------------+                                          |
|      | Check link_id   |                                          |
|      | Verify active   |                                          |
|      | Load partners   |                                          |
|      +--------+--------+                                          |
|               |                                                   |
|               v                                                   |
|  [2] PARALLEL FRAMEWORK FETCH (ISOLATION ENFORCED)                |
|      +---------------------------+---------------------------+    |
|      |                           |                           |    |
|      v                           v                           |    |
|  +----------+             +----------+                       |    |
|  | Partner A|             | Partner B|                       |    |
|  | Frameworks|            | Frameworks|                      |    |
|  | (ABSTRACTED)|          | (ABSTRACTED)|                    |    |
|  +----+-----+             +----+------+                      |    |
|       |                        |                             |    |
|       +------------------------+                             |    |
|                                |                             |    |
|                                v                             |    |
|  [3] TOPIC MATCHING                                          |    |
|      +-----------------+                                     |    |
|      | Identify Shared |                                     |    |
|      | Frameworks      |                                     |    |
|      | (Isolation Svc) |                                     |    |
|      +--------+--------+                                     |    |
|               |                                              |    |
|               v                                              |    |
|  [4] FRAMEWORK MERGE                                         |    |
|      +-----------------+                                     |    |
|      | Merge Engine    |                                     |    |
|      | (Framework Only)|                                    |    |
|      | NO RAW PHI      |                                     |    |
|      +--------+--------+                                     |    |
|               |                                              |    |
|               v                                              |    |
|  [5] PERSIST & AUDIT (CRITICAL LOGGING)                      |    |
|      +-----------------+                                     |    |
|      | Store Merge     |                                     |    |
|      | Audit: Both IDs |                                     |    |
|      | Isolation Check |                                     |    |
|      | Slack Notify    |                                     |    |
|      +-----------------+                                     |    |
|                                                              |    |
+-------------------------------------------------------------------+
```

### Pipeline Error Handling

All pipelines implement consistent error handling:

```python
# Error handling pattern
try:
    # Pipeline stages
    ...
except Exception as e:
    logger.error("pipeline_failed",
                 pipeline_id=pipeline_id,
                 stage=current_stage,
                 error=str(e))

    await fail_pipeline(
        session_factory,
        pipeline_id,
        current_stage,
        error_message=str(e)
    )

    # Log to audit
    await audit.log_pipeline_failure(
        pipeline_id=pipeline_id,
        session_id=session_id,
        stage=current_stage,
        error=str(e)
    )

    # Notify (no PHI in notification)
    await slack.notify_error(
        message=f"Pipeline {pipeline_id[:8]} failed at {current_stage}",
        severity="high" if current_stage in CRITICAL_STAGES else "medium"
    )
```

### Pipeline Status Tracking

Pipelines update status at each stage via `PipelineRun` model:

```python
# PipelineRun tracks:
- id (UUID)
- pipeline_type ('pre_session', 'post_session', 'couples_merge')
- session_id (FK)
- status ('queued', 'processing', 'complete', 'failed')
- current_stage (e.g., 'fetch_transcript', 'rung_analysis')
- error_message (if failed)
- started_at, completed_at
- metadata (JSON - stage timings, service calls)
```

Clients can poll status via:
```
GET /sessions/{id}/pre-session/status
GET /sessions/{id}/post-session/status
GET /couples/{linkId}/merge/status
```

### Deployment Architecture

Pipelines run on ECS Fargate as async background tasks:

```
Client Request → ALB → ECS (FastAPI)
                        ↓
                   Create PipelineRun (status: queued)
                   asyncio.create_task(run_pipeline)
                   Return 202 Accepted
                        ↓
                   Background: Pipeline executes
                   Updates: PipelineRun.status at each stage
                        ↓
                   Complete: PipelineRun.status = complete
                   Notify: Slack webhook (no PHI)
```

ECS Task Configuration:
- CPU: 1 vCPU
- Memory: 2 GB
- Timeout: 10 minutes (pipeline-level timeout)
- Concurrency: Up to 10 concurrent pipelines per ECS task
- Auto-scaling: Target 70% CPU utilization

---
