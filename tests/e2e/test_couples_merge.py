"""
Couples Merge Workflow E2E Tests for Phase 4B

Tests the complete couples merge workflow:
1. Merge workflow E2E (full pipeline)
2. Audit log completeness
3. Isolation verification at merge time

CRITICAL: 100% coverage required for security boundaries
"""

import os
import pytest
from uuid import uuid4
from datetime import datetime

# Set test environment variables
os.environ["AWS_REGION"] = "us-east-1"

from src.services.merge_engine import (
    MergeEngine,
    MergedFrameworks,
    MergeAuditEntry,
    MergeEngineError,
    COUPLES_EXERCISES,
)
from src.services.isolation_layer import (
    IsolationLayer,
    IsolatedFrameworks,
    isolate_for_couples_merge,
    IsolationViolation,
)
from src.services.couple_manager import (
    CoupleManager,
    CoupleLink,
    CoupleLinkStatus,
    CoupleManagerError,
)
from src.services.topic_matcher import (
    TopicMatcher,
    TopicMatchResult,
)
from src.agents.schemas.rung_output import (
    RungAnalysisOutput,
    FrameworkIdentified,
    DefenseMechanism,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def therapist_id():
    """Generate therapist ID."""
    return str(uuid4())


@pytest.fixture
def partner_a_id():
    """Generate partner A ID."""
    return str(uuid4())


@pytest.fixture
def partner_b_id():
    """Generate partner B ID."""
    return str(uuid4())


@pytest.fixture
def session_id():
    """Generate session ID."""
    return str(uuid4())


@pytest.fixture
def couple_link(therapist_id, partner_a_id, partner_b_id):
    """Create couple manager with pre-configured link and return link."""
    manager = CoupleManager(storage={})
    # Create link with canonical ordering
    link = manager.create_link(
        therapist_id=therapist_id,
        partner_a_id=partner_a_id,
        partner_b_id=partner_b_id,
    )
    return link, manager


@pytest.fixture
def couple_manager(couple_link):
    """Get couple manager from couple_link fixture."""
    return couple_link[1]


@pytest.fixture
def couple_link_id(couple_link):
    """Get the couple link ID."""
    return couple_link[0].id


@pytest.fixture
def isolation_layer():
    """Create isolation layer in strict mode."""
    return IsolationLayer(strict_mode=True)


@pytest.fixture
def topic_matcher():
    """Create topic matcher."""
    return TopicMatcher()


@pytest.fixture
def merge_engine(couple_manager, isolation_layer, topic_matcher):
    """Create merge engine with dependencies."""
    return MergeEngine(
        couple_manager=couple_manager,
        isolation_layer=isolation_layer,
        topic_matcher=topic_matcher,
    )


@pytest.fixture
def partner_a_analysis():
    """Rung analysis for partner A (anxious attachment pattern)."""
    return RungAnalysisOutput(
        frameworks_identified=[
            FrameworkIdentified(
                name="Attachment Theory - Anxious",
                confidence=0.9,
                evidence="Client shows anxious attachment patterns"
            ),
            FrameworkIdentified(
                name="Gottman Four Horsemen - Criticism",
                confidence=0.85,
                evidence="Partner tends to criticize during conflict"
            ),
            FrameworkIdentified(
                name="EFT - Pursue-Withdraw Cycle",
                confidence=0.8,
                evidence="Classic pursuer behavior observed"
            ),
        ],
        defense_mechanisms=[
            DefenseMechanism(
                type="intellectualization",
                indicators=["Analyzes feelings instead of experiencing them"],
            ),
        ],
        risk_flags=[],
        key_themes=["communication", "trust", "intimacy", "attachment"],
        suggested_exploration=["Childhood attachment experiences"],
        session_questions=["How did you feel when partner withdrew?"],
    )


@pytest.fixture
def partner_b_analysis():
    """Rung analysis for partner B (avoidant attachment pattern)."""
    return RungAnalysisOutput(
        frameworks_identified=[
            FrameworkIdentified(
                name="Attachment Theory - Avoidant",
                confidence=0.88,
                evidence="Client withdraws when partner expresses needs"
            ),
            FrameworkIdentified(
                name="Gottman Four Horsemen - Stonewalling",
                confidence=0.8,
                evidence="Shuts down during arguments"
            ),
            FrameworkIdentified(
                name="EFT - Pursue-Withdraw Cycle",
                confidence=0.85,
                evidence="Classic withdrawer behavior"
            ),
        ],
        defense_mechanisms=[
            DefenseMechanism(
                type="avoidance",
                indicators=["Changes subject when emotions arise"],
            ),
        ],
        risk_flags=[],
        key_themes=["communication", "boundaries", "autonomy", "safety"],
        suggested_exploration=["Fear of engulfment"],
        session_questions=["What happens when you feel pressured?"],
    )


# =============================================================================
# Merge Workflow E2E Tests
# =============================================================================

class TestMergeWorkflowE2E:
    """End-to-end tests for the complete merge workflow."""

    def test_full_merge_workflow_success(
        self,
        merge_engine,
        couple_link_id,
        session_id,
        therapist_id,
        partner_a_analysis,
        partner_b_analysis,
    ):
        """Test complete merge workflow executes successfully."""
        result = merge_engine.merge(
            couple_link_id=couple_link_id,
            session_id=session_id,
            therapist_id=therapist_id,
            partner_a_analysis=partner_a_analysis,
            partner_b_analysis=partner_b_analysis,
            ip_address="192.168.1.1",
        )

        # Verify result structure
        assert isinstance(result, MergedFrameworks)
        assert result.couple_link_id == couple_link_id
        assert result.session_id == session_id
        assert result.id is not None
        assert result.created_at is not None

    def test_merge_produces_partner_frameworks(
        self,
        merge_engine,
        couple_link_id,
        session_id,
        therapist_id,
        partner_a_analysis,
        partner_b_analysis,
    ):
        """Test merge extracts frameworks for both partners."""
        result = merge_engine.merge(
            couple_link_id=couple_link_id,
            session_id=session_id,
            therapist_id=therapist_id,
            partner_a_analysis=partner_a_analysis,
            partner_b_analysis=partner_b_analysis,
        )

        # Both partners should have frameworks
        assert len(result.partner_a_frameworks) > 0
        assert len(result.partner_b_frameworks) > 0

        # Partner A should have anxious attachment related
        partner_a_lower = [f.lower() for f in result.partner_a_frameworks]
        assert any("anxious" in f or "attachment" in f for f in partner_a_lower)

        # Partner B should have avoidant related
        partner_b_lower = [f.lower() for f in result.partner_b_frameworks]
        assert any("avoidant" in f or "attachment" in f for f in partner_b_lower)

    def test_merge_identifies_overlapping_themes(
        self,
        merge_engine,
        couple_link_id,
        session_id,
        therapist_id,
        partner_a_analysis,
        partner_b_analysis,
    ):
        """Test merge finds overlapping themes between partners."""
        result = merge_engine.merge(
            couple_link_id=couple_link_id,
            session_id=session_id,
            therapist_id=therapist_id,
            partner_a_analysis=partner_a_analysis,
            partner_b_analysis=partner_b_analysis,
        )

        # Both partners have "communication" theme
        assert "communication" in result.overlapping_themes

    def test_merge_identifies_complementary_patterns(
        self,
        merge_engine,
        couple_link_id,
        session_id,
        therapist_id,
        partner_a_analysis,
        partner_b_analysis,
    ):
        """Test merge finds complementary patterns (anxious-avoidant dynamic)."""
        result = merge_engine.merge(
            couple_link_id=couple_link_id,
            session_id=session_id,
            therapist_id=therapist_id,
            partner_a_analysis=partner_a_analysis,
            partner_b_analysis=partner_b_analysis,
        )

        # Anxious-avoidant is THE classic complementary pattern
        # The topic matcher should detect this
        assert len(result.complementary_patterns) > 0

    def test_merge_generates_couples_exercises(
        self,
        merge_engine,
        couple_link_id,
        session_id,
        therapist_id,
        partner_a_analysis,
        partner_b_analysis,
    ):
        """Test merge generates appropriate couples exercises."""
        result = merge_engine.merge(
            couple_link_id=couple_link_id,
            session_id=session_id,
            therapist_id=therapist_id,
            partner_a_analysis=partner_a_analysis,
            partner_b_analysis=partner_b_analysis,
        )

        # Should have exercises
        assert len(result.couples_exercises) > 0
        # Should be from our exercise library
        all_exercises = []
        for category in COUPLES_EXERCISES.values():
            all_exercises.extend(category)

        for exercise in result.couples_exercises:
            assert exercise in all_exercises

    def test_merge_generates_match_summary(
        self,
        merge_engine,
        couple_link_id,
        session_id,
        therapist_id,
        partner_a_analysis,
        partner_b_analysis,
    ):
        """Test merge produces a summary."""
        result = merge_engine.merge(
            couple_link_id=couple_link_id,
            session_id=session_id,
            therapist_id=therapist_id,
            partner_a_analysis=partner_a_analysis,
            partner_b_analysis=partner_b_analysis,
        )

        assert result.match_summary is not None
        assert len(result.match_summary) > 0

    def test_merge_with_invalid_couple_link_fails(
        self,
        merge_engine,
        session_id,
        therapist_id,
        partner_a_analysis,
        partner_b_analysis,
    ):
        """Test merge fails with invalid couple link."""
        with pytest.raises(MergeEngineError) as exc_info:
            merge_engine.merge(
                couple_link_id="invalid-link-id",
                session_id=session_id,
                therapist_id=therapist_id,
                partner_a_analysis=partner_a_analysis,
                partner_b_analysis=partner_b_analysis,
            )

        assert "Invalid couple link" in str(exc_info.value)

    def test_merge_with_wrong_therapist_fails(
        self,
        merge_engine,
        couple_link_id,
        session_id,
        partner_a_analysis,
        partner_b_analysis,
    ):
        """Test merge fails when therapist is not authorized."""
        wrong_therapist_id = str(uuid4())

        with pytest.raises(MergeEngineError) as exc_info:
            merge_engine.merge(
                couple_link_id=couple_link_id,
                session_id=session_id,
                therapist_id=wrong_therapist_id,
                partner_a_analysis=partner_a_analysis,
                partner_b_analysis=partner_b_analysis,
            )

        assert "Authorization failed" in str(exc_info.value)


# =============================================================================
# Audit Log Completeness Tests
# =============================================================================

class TestAuditLogCompleteness:
    """Test audit logging for compliance requirements."""

    def test_successful_merge_creates_audit_entry(
        self,
        merge_engine,
        couple_link_id,
        session_id,
        therapist_id,
        partner_a_analysis,
        partner_b_analysis,
    ):
        """Test successful merge creates audit log entry."""
        merge_engine.merge(
            couple_link_id=couple_link_id,
            session_id=session_id,
            therapist_id=therapist_id,
            partner_a_analysis=partner_a_analysis,
            partner_b_analysis=partner_b_analysis,
            ip_address="10.0.0.1",
        )

        audit_log = merge_engine.get_audit_log(couple_link_id)
        assert len(audit_log) == 1

        entry = audit_log[0]
        assert entry.action == "merge_completed"

    def test_audit_entry_captures_all_required_fields(
        self,
        merge_engine,
        couple_link_id,
        session_id,
        therapist_id,
        partner_a_id,
        partner_b_id,
        partner_a_analysis,
        partner_b_analysis,
    ):
        """Test audit entry contains all required compliance fields."""
        merge_engine.merge(
            couple_link_id=couple_link_id,
            session_id=session_id,
            therapist_id=therapist_id,
            partner_a_analysis=partner_a_analysis,
            partner_b_analysis=partner_b_analysis,
            ip_address="10.0.0.1",
        )

        audit_log = merge_engine.get_audit_log(couple_link_id)
        entry = audit_log[0]

        # Required fields for HIPAA compliance
        assert entry.id is not None
        assert entry.event_type == "couples_merge"
        assert entry.couple_link_id == couple_link_id
        assert entry.session_id == session_id
        assert entry.therapist_id == therapist_id
        assert entry.action == "merge_completed"
        # Partner IDs in canonical order
        assert entry.partner_a_id is not None
        assert entry.partner_b_id is not None
        assert entry.isolation_invoked is True  # CRITICAL
        assert entry.ip_address == "10.0.0.1"
        assert entry.created_at is not None

    def test_audit_entry_records_frameworks_accessed(
        self,
        merge_engine,
        couple_link_id,
        session_id,
        therapist_id,
        partner_a_analysis,
        partner_b_analysis,
    ):
        """Test audit tracks what data was accessed."""
        merge_engine.merge(
            couple_link_id=couple_link_id,
            session_id=session_id,
            therapist_id=therapist_id,
            partner_a_analysis=partner_a_analysis,
            partner_b_analysis=partner_b_analysis,
        )

        audit_log = merge_engine.get_audit_log(couple_link_id)
        entry = audit_log[0]

        # Should record what was accessed from each partner
        assert "partner_a" in entry.frameworks_accessed
        assert "partner_b" in entry.frameworks_accessed
        assert "attachment_patterns" in entry.frameworks_accessed["partner_a"]
        assert "frameworks" in entry.frameworks_accessed["partner_a"]
        assert "themes" in entry.frameworks_accessed["partner_a"]

    def test_audit_entry_records_result_summary(
        self,
        merge_engine,
        couple_link_id,
        session_id,
        therapist_id,
        partner_a_analysis,
        partner_b_analysis,
    ):
        """Test audit records result summary."""
        merge_engine.merge(
            couple_link_id=couple_link_id,
            session_id=session_id,
            therapist_id=therapist_id,
            partner_a_analysis=partner_a_analysis,
            partner_b_analysis=partner_b_analysis,
        )

        audit_log = merge_engine.get_audit_log(couple_link_id)
        entry = audit_log[0]

        assert entry.result_summary is not None
        assert "Merged" in entry.result_summary
        assert "frameworks" in entry.result_summary

    def test_failed_merge_creates_audit_entry(
        self,
        merge_engine,
        couple_link_id,
        session_id,
        partner_a_analysis,
        partner_b_analysis,
    ):
        """Test failed merge still creates audit entry."""
        wrong_therapist = str(uuid4())

        with pytest.raises(MergeEngineError):
            merge_engine.merge(
                couple_link_id=couple_link_id,
                session_id=session_id,
                therapist_id=wrong_therapist,
                partner_a_analysis=partner_a_analysis,
                partner_b_analysis=partner_b_analysis,
            )

        audit_log = merge_engine.get_audit_log(couple_link_id)
        assert len(audit_log) == 1

        entry = audit_log[0]
        assert entry.action == "merge_failed"
        assert entry.error_message is not None
        assert "Authorization" in entry.error_message

    def test_isolation_always_invoked_flag(
        self,
        merge_engine,
        couple_link_id,
        session_id,
        therapist_id,
        partner_a_analysis,
        partner_b_analysis,
    ):
        """CRITICAL: Verify isolation_invoked is always True for completed merges."""
        merge_engine.merge(
            couple_link_id=couple_link_id,
            session_id=session_id,
            therapist_id=therapist_id,
            partner_a_analysis=partner_a_analysis,
            partner_b_analysis=partner_b_analysis,
        )

        audit_log = merge_engine.get_audit_log(couple_link_id)
        entry = audit_log[0]

        # This is CRITICAL for HIPAA - isolation MUST be invoked
        assert entry.isolation_invoked is True

    def test_get_merge_history(
        self,
        merge_engine,
        couple_link_id,
        session_id,
        therapist_id,
        partner_a_analysis,
        partner_b_analysis,
    ):
        """Test get_merge_history returns completed merges only."""
        # Do multiple merges
        for i in range(3):
            merge_engine.merge(
                couple_link_id=couple_link_id,
                session_id=f"session-{i}",
                therapist_id=therapist_id,
                partner_a_analysis=partner_a_analysis,
                partner_b_analysis=partner_b_analysis,
            )

        history = merge_engine.get_merge_history(couple_link_id)
        assert len(history) == 3

        for entry in history:
            assert entry.action == "merge_completed"


# =============================================================================
# Isolation Verification Tests at Merge Time
# =============================================================================

class TestIsolationAtMergeTime:
    """CRITICAL: Verify isolation layer is properly enforced during merge."""

    def test_merge_output_contains_no_evidence(
        self,
        merge_engine,
        couple_link_id,
        session_id,
        therapist_id,
        partner_a_analysis,
        partner_b_analysis,
    ):
        """Test merge output contains no evidence strings."""
        result = merge_engine.merge(
            couple_link_id=couple_link_id,
            session_id=session_id,
            therapist_id=therapist_id,
            partner_a_analysis=partner_a_analysis,
            partner_b_analysis=partner_b_analysis,
        )

        # Combine all string outputs
        all_output = " ".join([
            " ".join(result.partner_a_frameworks),
            " ".join(result.partner_b_frameworks),
            " ".join(result.overlapping_themes),
            " ".join(result.complementary_patterns),
            " ".join(result.potential_conflicts),
            " ".join(result.suggested_focus_areas),
            " ".join(result.couples_exercises),
        ])

        # Evidence from original analysis should NOT be present
        assert "Client shows" not in all_output
        assert "Client withdraws" not in all_output
        assert "Partner tends" not in all_output
        assert "Shuts down" not in all_output

    def test_merge_output_contains_no_session_questions(
        self,
        merge_engine,
        couple_link_id,
        session_id,
        therapist_id,
        partner_a_analysis,
        partner_b_analysis,
    ):
        """Test merge output contains no session questions."""
        result = merge_engine.merge(
            couple_link_id=couple_link_id,
            session_id=session_id,
            therapist_id=therapist_id,
            partner_a_analysis=partner_a_analysis,
            partner_b_analysis=partner_b_analysis,
        )

        all_output = " ".join([
            " ".join(result.partner_a_frameworks),
            " ".join(result.partner_b_frameworks),
            " ".join(result.overlapping_themes),
            " ".join(result.suggested_focus_areas),
        ])

        # Session-specific questions should NOT be present
        assert "How did you feel" not in all_output
        assert "What happens when" not in all_output

    def test_merge_output_contains_no_exploration_suggestions(
        self,
        merge_engine,
        couple_link_id,
        session_id,
        therapist_id,
        partner_a_analysis,
        partner_b_analysis,
    ):
        """Test merge output contains no exploration suggestions."""
        result = merge_engine.merge(
            couple_link_id=couple_link_id,
            session_id=session_id,
            therapist_id=therapist_id,
            partner_a_analysis=partner_a_analysis,
            partner_b_analysis=partner_b_analysis,
        )

        all_output = " ".join([
            " ".join(result.partner_a_frameworks),
            " ".join(result.partner_b_frameworks),
            " ".join(result.suggested_focus_areas),
        ])

        # Exploration suggestions should NOT cross boundaries
        assert "Childhood" not in all_output
        assert "Fear of engulfment" not in all_output

    def test_merge_output_contains_no_indicator_details(
        self,
        merge_engine,
        couple_link_id,
        session_id,
        therapist_id,
        partner_a_analysis,
        partner_b_analysis,
    ):
        """Test merge output contains no defense mechanism indicators."""
        result = merge_engine.merge(
            couple_link_id=couple_link_id,
            session_id=session_id,
            therapist_id=therapist_id,
            partner_a_analysis=partner_a_analysis,
            partner_b_analysis=partner_b_analysis,
        )

        all_output = " ".join([
            " ".join(result.partner_a_frameworks),
            " ".join(result.partner_b_frameworks),
        ])

        # Specific indicators should NOT be present
        assert "Analyzes feelings" not in all_output
        assert "Changes subject" not in all_output

    def test_frameworks_are_whitelisted_only(
        self,
        merge_engine,
        couple_link_id,
        session_id,
        therapist_id,
        partner_a_analysis,
        partner_b_analysis,
    ):
        """Test all frameworks in output are from whitelist."""
        from src.services.isolation_layer import (
            ALLOWED_ATTACHMENT_PATTERNS,
            ALLOWED_FRAMEWORKS,
            ALLOWED_THEMES,
            ALLOWED_DEFENSES,
            ALLOWED_COMMUNICATION_PATTERNS,
            ALLOWED_MODALITIES,
        )

        all_allowed = (
            ALLOWED_ATTACHMENT_PATTERNS |
            ALLOWED_FRAMEWORKS |
            ALLOWED_THEMES |
            ALLOWED_DEFENSES |
            ALLOWED_COMMUNICATION_PATTERNS |
            ALLOWED_MODALITIES
        )

        result = merge_engine.merge(
            couple_link_id=couple_link_id,
            session_id=session_id,
            therapist_id=therapist_id,
            partner_a_analysis=partner_a_analysis,
            partner_b_analysis=partner_b_analysis,
        )

        # Check partner frameworks are from whitelist
        for fw in result.partner_a_frameworks:
            assert fw.lower() in all_allowed, f"Non-whitelisted: {fw}"

        for fw in result.partner_b_frameworks:
            assert fw.lower() in all_allowed, f"Non-whitelisted: {fw}"

    def test_themes_are_whitelisted_only(
        self,
        merge_engine,
        couple_link_id,
        session_id,
        therapist_id,
        partner_a_analysis,
        partner_b_analysis,
    ):
        """Test all themes in output are from allowed sets."""
        from src.services.isolation_layer import (
            ALLOWED_THEMES,
            ALLOWED_FRAMEWORKS,
            ALLOWED_ATTACHMENT_PATTERNS,
        )

        # Overlapping themes may include framework matches, not just theme categories
        all_allowed = ALLOWED_THEMES | ALLOWED_FRAMEWORKS | ALLOWED_ATTACHMENT_PATTERNS

        result = merge_engine.merge(
            couple_link_id=couple_link_id,
            session_id=session_id,
            therapist_id=therapist_id,
            partner_a_analysis=partner_a_analysis,
            partner_b_analysis=partner_b_analysis,
        )

        for theme in result.overlapping_themes:
            assert theme.lower() in all_allowed, f"Non-whitelisted: {theme}"


# =============================================================================
# Edge Cases and Security Boundary Tests
# =============================================================================

class TestMergeSecurityBoundaries:
    """Test security boundaries are enforced."""

    def test_merge_with_phi_in_framework_name_strips_it(
        self,
        merge_engine,
        couple_link_id,
        session_id,
        therapist_id,
    ):
        """Test PHI in framework name is stripped."""
        # Analysis with PHI leaked into framework name
        partner_a = RungAnalysisOutput(
            frameworks_identified=[
                FrameworkIdentified(
                    name="John mentioned anxious attachment on 01/15/2024",
                    confidence=0.9,
                    evidence="Evidence"
                ),
            ],
            defense_mechanisms=[],
            risk_flags=[],
            key_themes=["communication"],
            suggested_exploration=[],
            session_questions=[],
        )

        partner_b = RungAnalysisOutput(
            frameworks_identified=[
                FrameworkIdentified(
                    name="Avoidant attachment",
                    confidence=0.9,
                    evidence="Evidence"
                ),
            ],
            defense_mechanisms=[],
            risk_flags=[],
            key_themes=["communication"],
            suggested_exploration=[],
            session_questions=[],
        )

        result = merge_engine.merge(
            couple_link_id=couple_link_id,
            session_id=session_id,
            therapist_id=therapist_id,
            partner_a_analysis=partner_a,
            partner_b_analysis=partner_b,
        )

        # PHI should be stripped - only whitelisted terms pass
        all_output = " ".join(result.partner_a_frameworks)
        assert "John" not in all_output
        assert "01/15/2024" not in all_output

    def test_merge_with_empty_analyses(
        self,
        merge_engine,
        couple_link_id,
        session_id,
        therapist_id,
    ):
        """Test merge handles empty analyses gracefully."""
        empty_analysis = RungAnalysisOutput(
            frameworks_identified=[],
            defense_mechanisms=[],
            risk_flags=[],
            key_themes=[],
            suggested_exploration=[],
            session_questions=[],
        )

        result = merge_engine.merge(
            couple_link_id=couple_link_id,
            session_id=session_id,
            therapist_id=therapist_id,
            partner_a_analysis=empty_analysis,
            partner_b_analysis=empty_analysis,
        )

        assert result is not None
        assert result.partner_a_frameworks == []
        assert result.partner_b_frameworks == []

    def test_create_manual_audit_entry(
        self,
        merge_engine,
        couple_link_id,
        session_id,
        therapist_id,
        partner_a_id,
        partner_b_id,
    ):
        """Test manual audit entry creation for compliance."""
        entry = merge_engine.create_audit_entry(
            couple_link_id=couple_link_id,
            session_id=session_id,
            therapist_id=therapist_id,
            action="manual_review",
            partner_a_id=partner_a_id,
            partner_b_id=partner_b_id,
            result_summary="Manual review completed",
            ip_address="10.0.0.1",
        )

        assert entry.action == "manual_review"
        assert entry.couple_link_id == couple_link_id

        # Should be in audit log
        audit_log = merge_engine.get_audit_log(couple_link_id)
        assert len(audit_log) == 1


# =============================================================================
# API Endpoint Tests (if FastAPI available)
# =============================================================================

@pytest.fixture
def skip_if_no_fastapi():
    """Skip tests if FastAPI not installed."""
    pytest.importorskip("fastapi")


class TestMergeAPIEndpoints:
    """Test API endpoints for merge operations."""

    def test_api_imports(self, skip_if_no_fastapi):
        """Test API module imports successfully."""
        from src.api.merged_frameworks import router
        assert router is not None

    def test_api_router_has_merge_endpoint(self, skip_if_no_fastapi):
        """Test router has merge endpoint."""
        from src.api.merged_frameworks import router

        routes = [r.path for r in router.routes]
        assert "/merge" in routes or any("/merge" in r for r in routes)

    def test_api_router_has_merged_frameworks_endpoint(self, skip_if_no_fastapi):
        """Test router has merged-frameworks endpoint."""
        from src.api.merged_frameworks import router

        routes = [r.path for r in router.routes]
        assert any("merged-frameworks" in r for r in routes)

    def test_api_router_has_audit_log_endpoint(self, skip_if_no_fastapi):
        """Test router has audit-log endpoint."""
        from src.api.merged_frameworks import router

        routes = [r.path for r in router.routes]
        assert any("audit-log" in r for r in routes)
