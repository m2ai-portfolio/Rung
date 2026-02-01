-- Rung Database Schema - Indexes Migration
-- Performance and query optimization indexes

-- ============================================================================
-- Therapists Indexes
-- ============================================================================

-- Lookup by Cognito sub (authentication)
CREATE UNIQUE INDEX idx_therapists_cognito_sub ON therapists(cognito_sub);

-- ============================================================================
-- Clients Indexes
-- ============================================================================

-- Find clients by therapist
CREATE INDEX idx_clients_therapist_id ON clients(therapist_id);

-- Filter by consent status
CREATE INDEX idx_clients_consent_status ON clients(consent_status);

-- Composite for therapist's active clients
CREATE INDEX idx_clients_therapist_active ON clients(therapist_id, consent_status)
    WHERE consent_status = 'active';

-- ============================================================================
-- Sessions Indexes
-- ============================================================================

-- Find sessions by client
CREATE INDEX idx_sessions_client_id ON sessions(client_id);

-- Filter by status
CREATE INDEX idx_sessions_status ON sessions(status);

-- Find sessions by date range
CREATE INDEX idx_sessions_session_date ON sessions(session_date);

-- Composite for upcoming sessions
CREATE INDEX idx_sessions_client_upcoming ON sessions(client_id, session_date, status)
    WHERE status IN ('scheduled', 'in_progress');

-- Find sessions within date range (common query)
CREATE INDEX idx_sessions_date_range ON sessions(session_date DESC);

-- ============================================================================
-- Agents Indexes
-- ============================================================================

-- Find agents by client
CREATE INDEX idx_agents_client_id ON agents(client_id);

-- Find agents by name
CREATE INDEX idx_agents_name ON agents(name);

-- ============================================================================
-- Clinical Briefs Indexes
-- ============================================================================

-- Find briefs by session
CREATE INDEX idx_clinical_briefs_session_id ON clinical_briefs(session_id);

-- Find briefs by agent
CREATE INDEX idx_clinical_briefs_agent_id ON clinical_briefs(agent_id);

-- Find recent briefs
CREATE INDEX idx_clinical_briefs_created_at ON clinical_briefs(created_at DESC);

-- GIN index for JSONB framework search
CREATE INDEX idx_clinical_briefs_frameworks ON clinical_briefs
    USING GIN (frameworks_identified);

-- GIN index for risk flags (for risk monitoring queries)
CREATE INDEX idx_clinical_briefs_risk_flags ON clinical_briefs
    USING GIN (risk_flags);

-- ============================================================================
-- Client Guides Indexes
-- ============================================================================

-- Find guides by session
CREATE INDEX idx_client_guides_session_id ON client_guides(session_id);

-- Find guides by agent
CREATE INDEX idx_client_guides_agent_id ON client_guides(agent_id);

-- Find recent guides
CREATE INDEX idx_client_guides_created_at ON client_guides(created_at DESC);

-- ============================================================================
-- Development Plans Indexes
-- ============================================================================

-- Find plans by client
CREATE INDEX idx_development_plans_client_id ON development_plans(client_id);

-- Find current sprint (most recent)
CREATE INDEX idx_development_plans_client_sprint ON development_plans(client_id, sprint_number DESC);

-- GIN index for goals search
CREATE INDEX idx_development_plans_goals ON development_plans
    USING GIN (goals);

-- ============================================================================
-- Couple Links Indexes
-- ============================================================================

-- Find links by partner A
CREATE INDEX idx_couple_links_partner_a ON couple_links(partner_a_id);

-- Find links by partner B
CREATE INDEX idx_couple_links_partner_b ON couple_links(partner_b_id);

-- Find links by therapist
CREATE INDEX idx_couple_links_therapist ON couple_links(therapist_id);

-- Find active couples
CREATE INDEX idx_couple_links_active ON couple_links(status)
    WHERE status = 'active';

-- ============================================================================
-- Framework Merges Indexes
-- ============================================================================

-- Find merges by couple link
CREATE INDEX idx_framework_merges_couple_link ON framework_merges(couple_link_id);

-- Find merges by session
CREATE INDEX idx_framework_merges_session ON framework_merges(session_id);

-- Find recent merges
CREATE INDEX idx_framework_merges_created_at ON framework_merges(created_at DESC);

-- ============================================================================
-- Audit Logs Indexes (CRITICAL for HIPAA compliance queries)
-- ============================================================================

-- Find logs by event type
CREATE INDEX idx_audit_logs_event_type ON audit_logs(event_type);

-- Find logs by user
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);

-- Find logs by resource
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);

-- Find logs by action
CREATE INDEX idx_audit_logs_action ON audit_logs(action);

-- Time-based queries (most common for audits)
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);

-- Composite for user activity audit
CREATE INDEX idx_audit_logs_user_activity ON audit_logs(user_id, created_at DESC)
    WHERE user_id IS NOT NULL;

-- Composite for resource history
CREATE INDEX idx_audit_logs_resource_history ON audit_logs(resource_type, resource_id, created_at DESC);

-- GIN index for details search (for forensic queries)
CREATE INDEX idx_audit_logs_details ON audit_logs
    USING GIN (details);

-- ============================================================================
-- Partial Indexes for Common Queries
-- ============================================================================

-- Active clients only (common filter)
CREATE INDEX idx_clients_active_only ON clients(therapist_id)
    WHERE consent_status = 'active';

-- Scheduled sessions (dashboard query)
CREATE INDEX idx_sessions_scheduled ON sessions(client_id, session_date)
    WHERE status = 'scheduled';

-- Completed sessions (reporting)
CREATE INDEX idx_sessions_completed ON sessions(client_id, session_date)
    WHERE status = 'completed';

-- High-risk briefs (monitoring)
CREATE INDEX idx_clinical_briefs_high_risk ON clinical_briefs(session_id, created_at)
    WHERE jsonb_array_length(risk_flags) > 0;
