-- Rung Database Schema - Initial Migration
-- HIPAA-compliant schema with field-level encryption for PHI
-- PostgreSQL 15+

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- ENUM Types
-- ============================================================================

CREATE TYPE consent_status AS ENUM ('pending', 'active', 'revoked');
CREATE TYPE session_type AS ENUM ('individual', 'couples');
CREATE TYPE session_status AS ENUM ('scheduled', 'in_progress', 'completed', 'cancelled');
CREATE TYPE couple_status AS ENUM ('active', 'paused', 'terminated');
CREATE TYPE agent_name AS ENUM ('rung', 'beth');

-- ============================================================================
-- 1. Therapists Table
-- ============================================================================

CREATE TABLE therapists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cognito_sub VARCHAR(255) NOT NULL UNIQUE,
    email_encrypted BYTEA NOT NULL,  -- PHI: encrypted with field-level key
    practice_name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE therapists IS 'Licensed therapists using the Rung system';
COMMENT ON COLUMN therapists.email_encrypted IS 'PHI: Email encrypted with KMS field-level key';

-- ============================================================================
-- 2. Clients Table
-- ============================================================================

CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    therapist_id UUID NOT NULL REFERENCES therapists(id) ON DELETE RESTRICT,
    name_encrypted BYTEA NOT NULL,  -- PHI: encrypted
    contact_encrypted BYTEA,  -- PHI: encrypted (optional)
    consent_status consent_status NOT NULL DEFAULT 'pending',
    consent_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT consent_date_required_when_active
        CHECK (consent_status != 'active' OR consent_date IS NOT NULL)
);

COMMENT ON TABLE clients IS 'Therapy clients with encrypted PHI';
COMMENT ON COLUMN clients.name_encrypted IS 'PHI: Client name encrypted with KMS field-level key';
COMMENT ON COLUMN clients.contact_encrypted IS 'PHI: Contact info encrypted with KMS field-level key';

-- ============================================================================
-- 3. Sessions Table
-- ============================================================================

CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    session_type session_type NOT NULL DEFAULT 'individual',
    session_date TIMESTAMP WITH TIME ZONE NOT NULL,
    status session_status NOT NULL DEFAULT 'scheduled',
    notes_encrypted BYTEA,  -- PHI: encrypted session notes
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE sessions IS 'Therapy sessions with encrypted notes';
COMMENT ON COLUMN sessions.notes_encrypted IS 'PHI: Session notes encrypted with KMS field-level key';

-- ============================================================================
-- 4. Agents Table
-- ============================================================================

CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name agent_name NOT NULL,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    system_prompt TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Each client can have at most one of each agent type
    CONSTRAINT unique_agent_per_client UNIQUE (client_id, name)
);

COMMENT ON TABLE agents IS 'AI agents (Rung for therapist, Beth for client)';
COMMENT ON COLUMN agents.name IS 'Agent type: rung (clinical) or beth (client-facing)';

-- ============================================================================
-- 5. Clinical Briefs Table
-- ============================================================================

CREATE TABLE clinical_briefs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE RESTRICT,
    content_encrypted BYTEA NOT NULL,  -- PHI: encrypted clinical analysis
    frameworks_identified JSONB NOT NULL DEFAULT '[]'::jsonb,
    risk_flags JSONB NOT NULL DEFAULT '[]'::jsonb,
    research_citations JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE clinical_briefs IS 'Clinical analysis from Rung agent (therapist-facing)';
COMMENT ON COLUMN clinical_briefs.content_encrypted IS 'PHI: Clinical brief encrypted with KMS field-level key';
COMMENT ON COLUMN clinical_briefs.frameworks_identified IS 'Psychological frameworks detected in session';
COMMENT ON COLUMN clinical_briefs.risk_flags IS 'Risk indicators flagged for therapist attention';

-- ============================================================================
-- 6. Client Guides Table
-- ============================================================================

CREATE TABLE client_guides (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE RESTRICT,
    content_encrypted BYTEA NOT NULL,  -- PHI: encrypted client guide
    key_points JSONB NOT NULL DEFAULT '[]'::jsonb,
    exercises_suggested JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE client_guides IS 'Session preparation guides from Beth agent (client-facing)';
COMMENT ON COLUMN client_guides.content_encrypted IS 'PHI: Client guide encrypted with KMS field-level key';

-- ============================================================================
-- 7. Development Plans Table
-- ============================================================================

CREATE TABLE development_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    sprint_number INTEGER NOT NULL DEFAULT 1,
    goals JSONB NOT NULL DEFAULT '[]'::jsonb,
    exercises JSONB NOT NULL DEFAULT '[]'::jsonb,
    progress JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Each client has one plan per sprint
    CONSTRAINT unique_sprint_per_client UNIQUE (client_id, sprint_number)
);

COMMENT ON TABLE development_plans IS 'Sprint-based development plans for clients';
COMMENT ON COLUMN development_plans.sprint_number IS 'Sequential sprint number (1-2 week cycles)';

-- ============================================================================
-- 8. Couple Links Table
-- ============================================================================

CREATE TABLE couple_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    partner_a_id UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    partner_b_id UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    therapist_id UUID NOT NULL REFERENCES therapists(id) ON DELETE RESTRICT,
    status couple_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Prevent duplicate links (always store smaller ID as partner_a)
    CONSTRAINT partner_a_less_than_b CHECK (partner_a_id < partner_b_id),
    CONSTRAINT unique_couple UNIQUE (partner_a_id, partner_b_id),
    -- Partners must have the same therapist
    CONSTRAINT different_partners CHECK (partner_a_id != partner_b_id)
);

COMMENT ON TABLE couple_links IS 'Links between partners for couples therapy';
COMMENT ON COLUMN couple_links.partner_a_id IS 'First partner (ID < partner_b_id to prevent duplicates)';

-- ============================================================================
-- 9. Framework Merges Table
-- ============================================================================

CREATE TABLE framework_merges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    couple_link_id UUID NOT NULL REFERENCES couple_links(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    partner_a_frameworks JSONB NOT NULL DEFAULT '[]'::jsonb,  -- Abstracted only
    partner_b_frameworks JSONB NOT NULL DEFAULT '[]'::jsonb,  -- Abstracted only
    merged_insights JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE framework_merges IS 'Merged framework analysis for couples sessions';
COMMENT ON COLUMN framework_merges.partner_a_frameworks IS 'Abstracted frameworks only - NO specific content';
COMMENT ON COLUMN framework_merges.partner_b_frameworks IS 'Abstracted frameworks only - NO specific content';

-- ============================================================================
-- 10. Audit Logs Table
-- ============================================================================

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(100) NOT NULL,
    user_id UUID,  -- Nullable for system events
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID,
    action VARCHAR(50) NOT NULL,
    ip_address VARCHAR(45),  -- IPv6 max length
    user_agent TEXT,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE audit_logs IS 'HIPAA-required audit trail for all PHI access';
COMMENT ON COLUMN audit_logs.event_type IS 'Category of event (access, modify, delete, export, etc.)';
COMMENT ON COLUMN audit_logs.details IS 'Additional context about the event';

-- ============================================================================
-- Trigger Functions for updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers to relevant tables
CREATE TRIGGER update_therapists_updated_at
    BEFORE UPDATE ON therapists
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_clients_updated_at
    BEFORE UPDATE ON clients
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agents_updated_at
    BEFORE UPDATE ON agents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_development_plans_updated_at
    BEFORE UPDATE ON development_plans
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_couple_links_updated_at
    BEFORE UPDATE ON couple_links
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
