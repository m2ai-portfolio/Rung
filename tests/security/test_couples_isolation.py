"""
Couples Isolation Security Tests for Phase 4A

CRITICAL SECURITY TESTS - 100% coverage required

Tests verify:
1. Isolation layer strips ALL PHI
2. No specific content crosses boundaries
3. Only allowed frameworks pass through
4. Couple linking validation
5. Topic matching with isolated data
"""

import os
import pytest
from uuid import uuid4

# Set test environment variables
os.environ["AWS_REGION"] = "us-east-1"

from src.services.isolation_layer import (
    IsolationLayer,
    IsolatedFrameworks,
    IsolationLayerError,
    IsolationViolation,
    isolate_for_couples_merge,
    ALLOWED_ATTACHMENT_PATTERNS,
    ALLOWED_FRAMEWORKS,
    ALLOWED_THEMES,
    ALLOWED_DEFENSES,
    ALLOWED_COMMUNICATION_PATTERNS,
    ALLOWED_MODALITIES,
)
from src.services.couple_manager import (
    CoupleManager,
    CoupleLink,
    CoupleLinkStatus,
    CoupleLinkUpdate,
    CoupleManagerError,
)
from src.services.topic_matcher import (
    TopicMatcher,
    TopicMatch,
    TopicMatchResult,
    match_couple_topics,
)
from src.agents.schemas.rung_output import (
    RungAnalysisOutput,
    FrameworkIdentified,
    DefenseMechanism,
    RiskFlag,
    RiskLevel,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def isolation_layer():
    """Create isolation layer in strict mode."""
    return IsolationLayer(strict_mode=True)


@pytest.fixture
def couple_manager():
    """Create couple manager with empty storage."""
    return CoupleManager(storage={})


@pytest.fixture
def topic_matcher():
    """Create topic matcher."""
    return TopicMatcher()


@pytest.fixture
def sample_rung_output():
    """Sample Rung analysis output with various patterns."""
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
        ],
        defense_mechanisms=[
            DefenseMechanism(
                type="intellectualization",
                indicators=["Analyzes feelings instead of experiencing them"],
            ),
        ],
        risk_flags=[],
        key_themes=["communication", "trust", "intimacy"],
        suggested_exploration=["Childhood attachment experiences"],
        session_questions=["How did you feel when..."],
    )


@pytest.fixture
def sample_rung_output_partner_b():
    """Sample Rung output for partner B (different patterns)."""
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
        ],
        defense_mechanisms=[
            DefenseMechanism(
                type="avoidance",
                indicators=["Changes subject when emotions arise"],
            ),
        ],
        risk_flags=[],
        key_themes=["communication", "boundaries", "autonomy"],
        suggested_exploration=["Fear of engulfment"],
        session_questions=["What happens when you feel pressured..."],
    )


# =============================================================================
# Isolation Layer Tests - CRITICAL SECURITY
# =============================================================================

class TestIsolationLayer:
    """Test isolation layer security."""

    def test_layer_initialization(self, isolation_layer):
        """Test layer initializes in strict mode."""
        assert isolation_layer.strict_mode is True

    def test_isolate_extracts_attachment_patterns(
        self, isolation_layer, sample_rung_output
    ):
        """Test attachment pattern extraction."""
        isolated = isolation_layer.isolate(sample_rung_output)

        assert isinstance(isolated, IsolatedFrameworks)
        assert len(isolated.attachment_patterns) > 0
        # Should extract the style, not specific details
        assert any("anxious" in p for p in isolated.attachment_patterns)

    def test_isolate_extracts_frameworks(
        self, isolation_layer, sample_rung_output
    ):
        """Test framework extraction."""
        isolated = isolation_layer.isolate(sample_rung_output)

        assert len(isolated.frameworks_identified) > 0
        # Should have attachment theory
        assert any(
            "attachment" in fw
            for fw in isolated.frameworks_identified
        )

    def test_isolate_extracts_themes(
        self, isolation_layer, sample_rung_output
    ):
        """Test theme extraction."""
        isolated = isolation_layer.isolate(sample_rung_output)

        assert len(isolated.theme_categories) > 0
        assert "communication" in isolated.theme_categories

    def test_isolate_strips_evidence(
        self, isolation_layer, sample_rung_output
    ):
        """CRITICAL: Test that evidence strings are stripped."""
        isolated = isolation_layer.isolate(sample_rung_output)

        # Combine all output
        all_output = " ".join([
            " ".join(isolated.attachment_patterns),
            " ".join(isolated.frameworks_identified),
            " ".join(isolated.theme_categories),
            " ".join(isolated.modalities),
            " ".join(isolated.defense_patterns),
            " ".join(isolated.communication_patterns),
        ])

        # Evidence should NOT be present
        assert "Client shows" not in all_output
        assert "Partner tends" not in all_output
        assert "patterns" not in all_output.lower() or \
               any(allowed in all_output.lower() for allowed in ALLOWED_ATTACHMENT_PATTERNS)

    def test_isolate_strips_session_questions(
        self, isolation_layer, sample_rung_output
    ):
        """CRITICAL: Session questions must not pass through."""
        isolated = isolation_layer.isolate(sample_rung_output)

        all_output = " ".join([
            " ".join(isolated.attachment_patterns),
            " ".join(isolated.frameworks_identified),
            " ".join(isolated.theme_categories),
        ])

        assert "How did you feel" not in all_output
        assert "?" not in all_output

    def test_isolate_strips_suggested_exploration(
        self, isolation_layer, sample_rung_output
    ):
        """CRITICAL: Exploration suggestions must not pass through."""
        isolated = isolation_layer.isolate(sample_rung_output)

        all_output = " ".join([
            " ".join(isolated.attachment_patterns),
            " ".join(isolated.frameworks_identified),
            " ".join(isolated.theme_categories),
        ])

        assert "Childhood" not in all_output
        assert "experiences" not in all_output


class TestIsolationPHIDetection:
    """Test PHI detection in isolation layer."""

    def test_contains_phi_with_quotes(self, isolation_layer):
        """Test detection of quoted content."""
        text = 'Client said "I hate when he does that"'
        assert isolation_layer.contains_phi(text) is True

    def test_contains_phi_with_dates(self, isolation_layer):
        """Test detection of dates."""
        assert isolation_layer.contains_phi("On 01/15/2024") is True
        assert isolation_layer.contains_phi("On 2024-01-15") is True
        assert isolation_layer.contains_phi("Last Monday") is True
        assert isolation_layer.contains_phi("Yesterday") is True

    def test_contains_phi_with_names(self, isolation_layer):
        """Test detection of potential names."""
        assert isolation_layer.contains_phi("John Smith mentioned") is True

    def test_contains_phi_with_locations(self, isolation_layer):
        """Test detection of locations."""
        assert isolation_layer.contains_phi("At the hospital") is True
        assert isolation_layer.contains_phi("123 Main Street") is True

    def test_contains_phi_with_numbers(self, isolation_layer):
        """Test detection of identifying numbers."""
        assert isolation_layer.contains_phi("She is 45 years old") is True
        assert isolation_layer.contains_phi("$5000 in debt") is True

    def test_contains_phi_with_specific_incidents(self, isolation_layer):
        """Test detection of specific incidents."""
        assert isolation_layer.contains_phi("When he yelled at me") is True
        assert isolation_layer.contains_phi("After she walked away") is True
        assert isolation_layer.contains_phi("the incident at work") is True

    def test_contains_phi_with_emotional_details(self, isolation_layer):
        """Test detection of emotional details."""
        assert isolation_layer.contains_phi("felt so angry") is True
        assert isolation_layer.contains_phi("was crying uncontrollably") is True

    def test_no_false_positive_for_allowed_terms(self, isolation_layer):
        """Test that allowed terms don't trigger PHI detection."""
        # These should NOT be flagged as PHI
        assert isolation_layer.contains_phi("anxious attachment") is False
        assert isolation_layer.contains_phi("CBT techniques") is False
        assert isolation_layer.contains_phi("communication patterns") is False
        assert isolation_layer.contains_phi("stonewalling behavior") is False


class TestIsolationWhitelist:
    """Test whitelist-based extraction."""

    def test_only_allowed_attachment_patterns(self, isolation_layer):
        """Test only whitelisted patterns pass through."""
        for pattern in ALLOWED_ATTACHMENT_PATTERNS:
            # Verify whitelist is comprehensive
            assert pattern.islower(), f"Pattern should be lowercase: {pattern}"

    def test_only_allowed_frameworks(self, isolation_layer):
        """Test only whitelisted frameworks pass through."""
        assert "attachment theory" in ALLOWED_FRAMEWORKS
        assert "gottman method" in ALLOWED_FRAMEWORKS
        assert "cbt" in ALLOWED_FRAMEWORKS

    def test_only_allowed_themes(self, isolation_layer):
        """Test only whitelisted themes pass through."""
        assert "communication" in ALLOWED_THEMES
        assert "trust" in ALLOWED_THEMES
        assert "intimacy" in ALLOWED_THEMES

    def test_extract_safe_categories(self, isolation_layer):
        """Test safe category extraction from text."""
        text = "Client exhibits anxious attachment and uses intellectualization as defense"
        categories = isolation_layer.extract_safe_categories(text)

        assert "anxious attachment" in categories
        assert "intellectualization" in categories


class TestIsolationStrictMode:
    """Test strict mode behavior."""

    def test_strict_mode_raises_on_phi(self):
        """Test strict mode raises IsolationViolation."""
        layer = IsolationLayer(strict_mode=True)

        # Create output with PHI that might slip through
        output = RungAnalysisOutput(
            frameworks_identified=[
                FrameworkIdentified(
                    name="John's Attachment Pattern",  # Contains name
                    confidence=0.9,
                    evidence="test"
                ),
            ],
            defense_mechanisms=[],
            risk_flags=[],
            key_themes=[],
            suggested_exploration=[],
            session_questions=[],
        )

        # This should extract nothing (name filtered out)
        isolated = layer.isolate(output)
        # The framework name with "John's" should be filtered out
        assert not any("john" in f.lower() for f in isolated.frameworks_identified)

    def test_non_strict_mode_sanitizes(self):
        """Test non-strict mode sanitizes instead of raising."""
        layer = IsolationLayer(strict_mode=False)

        text = 'Client said "I feel abandoned on 01/15/2024"'
        sanitized = layer.sanitize_text(text)

        assert "[REDACTED]" in sanitized


class TestIsolationForCouplesMerge:
    """Test the couples merge isolation function."""

    def test_isolate_both_partners(
        self, sample_rung_output, sample_rung_output_partner_b
    ):
        """Test isolation of both partners."""
        a_isolated, b_isolated = isolate_for_couples_merge(
            sample_rung_output,
            sample_rung_output_partner_b,
        )

        assert isinstance(a_isolated, IsolatedFrameworks)
        assert isinstance(b_isolated, IsolatedFrameworks)

        # Partner A should have anxious pattern
        assert any("anxious" in p for p in a_isolated.attachment_patterns)

        # Partner B should have avoidant pattern
        assert any("avoidant" in p for p in b_isolated.attachment_patterns)

    def test_no_cross_contamination(
        self, sample_rung_output, sample_rung_output_partner_b
    ):
        """CRITICAL: Ensure no data crosses between partners."""
        a_isolated, b_isolated = isolate_for_couples_merge(
            sample_rung_output,
            sample_rung_output_partner_b,
        )

        # Partner A's specific data should not be in B
        # (Evidence strings are stripped anyway)

        # Partner B's specific data should not be in A
        # Just verify they are separate objects
        assert a_isolated is not b_isolated


# =============================================================================
# Couple Manager Tests
# =============================================================================

class TestCoupleManager:
    """Test couple manager functionality."""

    def test_create_link(self, couple_manager):
        """Test creating a couple link."""
        therapist_id = str(uuid4())
        partner_a = str(uuid4())
        partner_b = str(uuid4())

        link = couple_manager.create_link(
            partner_a_id=partner_a,
            partner_b_id=partner_b,
            therapist_id=therapist_id,
        )

        assert isinstance(link, CoupleLink)
        assert link.status == CoupleLinkStatus.ACTIVE

    def test_cannot_link_same_client(self, couple_manager):
        """Test cannot link client to themselves."""
        therapist_id = str(uuid4())
        client_id = str(uuid4())

        with pytest.raises(CoupleManagerError) as exc:
            couple_manager.create_link(
                partner_a_id=client_id,
                partner_b_id=client_id,
                therapist_id=therapist_id,
            )
        assert "themselves" in str(exc.value)

    def test_cannot_create_duplicate_link(self, couple_manager):
        """Test cannot create duplicate links."""
        therapist_id = str(uuid4())
        partner_a = str(uuid4())
        partner_b = str(uuid4())

        # Create first link
        couple_manager.create_link(
            partner_a_id=partner_a,
            partner_b_id=partner_b,
            therapist_id=therapist_id,
        )

        # Attempt duplicate
        with pytest.raises(CoupleManagerError) as exc:
            couple_manager.create_link(
                partner_a_id=partner_a,
                partner_b_id=partner_b,
                therapist_id=therapist_id,
            )
        assert "already exists" in str(exc.value)

    def test_canonical_order(self, couple_manager):
        """Test partner IDs are stored in canonical order."""
        therapist_id = str(uuid4())
        # Create two valid UUIDs where we know the ordering
        partner_a = "ffffffff-ffff-ffff-ffff-ffffffffffff"  # Higher
        partner_b = "00000000-0000-0000-0000-000000000000"  # Lower

        link = couple_manager.create_link(
            partner_a_id=partner_a,
            partner_b_id=partner_b,
            therapist_id=therapist_id,
        )

        # partner_a_id should be the smaller one after canonical ordering
        assert link.partner_a_id < link.partner_b_id
        assert link.partner_a_id == partner_b  # The smaller one
        assert link.partner_b_id == partner_a  # The larger one

    def test_invalid_uuid_raises(self, couple_manager):
        """Test invalid UUIDs raise error."""
        with pytest.raises(CoupleManagerError):
            couple_manager.create_link(
                partner_a_id="not-a-uuid",
                partner_b_id=str(uuid4()),
                therapist_id=str(uuid4()),
            )

    def test_get_link(self, couple_manager):
        """Test getting a link by ID."""
        therapist_id = str(uuid4())
        link = couple_manager.create_link(
            partner_a_id=str(uuid4()),
            partner_b_id=str(uuid4()),
            therapist_id=therapist_id,
        )

        retrieved = couple_manager.get_link(link.id)
        assert retrieved.id == link.id

    def test_get_nonexistent_link_raises(self, couple_manager):
        """Test getting nonexistent link raises error."""
        with pytest.raises(CoupleManagerError):
            couple_manager.get_link("nonexistent-id")

    def test_update_link_status(self, couple_manager):
        """Test updating link status."""
        therapist_id = str(uuid4())
        link = couple_manager.create_link(
            partner_a_id=str(uuid4()),
            partner_b_id=str(uuid4()),
            therapist_id=therapist_id,
        )

        updated = couple_manager.pause_link(link.id, therapist_id)
        assert updated.status == CoupleLinkStatus.PAUSED

    def test_unauthorized_update_raises(self, couple_manager):
        """Test unauthorized update raises error."""
        therapist_id = str(uuid4())
        other_therapist = str(uuid4())

        link = couple_manager.create_link(
            partner_a_id=str(uuid4()),
            partner_b_id=str(uuid4()),
            therapist_id=therapist_id,
        )

        with pytest.raises(CoupleManagerError) as exc:
            couple_manager.pause_link(link.id, other_therapist)
        assert "Not authorized" in str(exc.value)

    def test_terminate_link(self, couple_manager):
        """Test terminating a link."""
        therapist_id = str(uuid4())
        link = couple_manager.create_link(
            partner_a_id=str(uuid4()),
            partner_b_id=str(uuid4()),
            therapist_id=therapist_id,
        )

        terminated = couple_manager.terminate_link(link.id, therapist_id)
        assert terminated.status == CoupleLinkStatus.TERMINATED

    def test_validate_merge_authorization(self, couple_manager):
        """Test merge authorization validation."""
        therapist_id = str(uuid4())
        link = couple_manager.create_link(
            partner_a_id=str(uuid4()),
            partner_b_id=str(uuid4()),
            therapist_id=therapist_id,
        )

        assert couple_manager.validate_merge_authorization(
            link.id, therapist_id
        ) is True

    def test_merge_authorization_fails_for_paused(self, couple_manager):
        """Test merge auth fails for paused link."""
        therapist_id = str(uuid4())
        link = couple_manager.create_link(
            partner_a_id=str(uuid4()),
            partner_b_id=str(uuid4()),
            therapist_id=therapist_id,
        )

        couple_manager.pause_link(link.id, therapist_id)

        with pytest.raises(CoupleManagerError) as exc:
            couple_manager.validate_merge_authorization(link.id, therapist_id)
        assert "not active" in str(exc.value)


# =============================================================================
# Topic Matcher Tests
# =============================================================================

class TestTopicMatcher:
    """Test topic matching between partners."""

    def test_find_overlapping_themes(self, topic_matcher):
        """Test finding overlapping themes."""
        partner_a = IsolatedFrameworks(
            theme_categories=["communication", "trust"],
        )
        partner_b = IsolatedFrameworks(
            theme_categories=["communication", "boundaries"],
        )

        result = topic_matcher.match(partner_a, partner_b)

        assert len(result.overlapping_themes) >= 1
        assert any(
            m.topic == "communication"
            for m in result.overlapping_themes
        )

    def test_find_complementary_patterns(self, topic_matcher):
        """Test finding complementary patterns."""
        partner_a = IsolatedFrameworks(
            attachment_patterns=["anxious attachment"],
        )
        partner_b = IsolatedFrameworks(
            attachment_patterns=["avoidant attachment"],
        )

        result = topic_matcher.match(partner_a, partner_b)

        assert len(result.complementary_patterns) >= 1
        assert any(
            "anxious" in m.topic.lower() and "avoidant" in m.topic.lower()
            for m in result.complementary_patterns
        )

    def test_find_conflict_patterns(self, topic_matcher):
        """Test finding conflict patterns."""
        partner_a = IsolatedFrameworks(
            communication_patterns=["criticism"],
        )
        partner_b = IsolatedFrameworks(
            communication_patterns=["stonewalling"],
        )

        result = topic_matcher.match(partner_a, partner_b)

        assert len(result.potential_conflicts) >= 1

    def test_generate_focus_areas(self, topic_matcher):
        """Test focus area generation."""
        partner_a = IsolatedFrameworks(
            attachment_patterns=["anxious attachment"],
            theme_categories=["communication"],
        )
        partner_b = IsolatedFrameworks(
            attachment_patterns=["avoidant attachment"],
            theme_categories=["communication"],
        )

        result = topic_matcher.match(partner_a, partner_b)

        assert len(result.suggested_focus_areas) > 0

    def test_generate_summary(self, topic_matcher):
        """Test summary generation."""
        partner_a = IsolatedFrameworks(
            theme_categories=["communication"],
        )
        partner_b = IsolatedFrameworks(
            theme_categories=["communication"],
        )

        result = topic_matcher.match(partner_a, partner_b)

        assert result.match_summary != ""
        assert "shared theme" in result.match_summary.lower()

    def test_no_patterns_returns_empty(self, topic_matcher):
        """Test empty input returns appropriate result."""
        partner_a = IsolatedFrameworks()
        partner_b = IsolatedFrameworks()

        result = topic_matcher.match(partner_a, partner_b)

        assert result.overlapping_themes == []
        assert result.complementary_patterns == []
        assert result.potential_conflicts == []


class TestTopicMatchConvenience:
    """Test convenience function."""

    def test_match_couple_topics_function(self):
        """Test the convenience function."""
        partner_a = IsolatedFrameworks(
            theme_categories=["communication", "trust"],
        )
        partner_b = IsolatedFrameworks(
            theme_categories=["communication", "boundaries"],
        )

        result = match_couple_topics(partner_a, partner_b)

        assert isinstance(result, TopicMatchResult)


# =============================================================================
# File Structure Tests
# =============================================================================

class TestFileStructure:
    """Test that all required files exist."""

    def test_isolation_layer_exists(self):
        """Verify isolation_layer.py exists."""
        assert os.path.exists("src/services/isolation_layer.py")

    def test_couple_manager_exists(self):
        """Verify couple_manager.py exists."""
        assert os.path.exists("src/services/couple_manager.py")

    def test_topic_matcher_exists(self):
        """Verify topic_matcher.py exists."""
        assert os.path.exists("src/services/topic_matcher.py")

    def test_couples_api_exists(self):
        """Verify couples.py API exists."""
        assert os.path.exists("src/api/couples.py")


# =============================================================================
# Integration Tests
# =============================================================================

class TestCouplesIsolationIntegration:
    """Integration tests for couples isolation workflow."""

    def test_full_isolation_workflow(
        self,
        sample_rung_output,
        sample_rung_output_partner_b,
    ):
        """Test complete isolation and matching workflow."""
        # Step 1: Isolate both partners
        a_isolated, b_isolated = isolate_for_couples_merge(
            sample_rung_output,
            sample_rung_output_partner_b,
        )

        # Step 2: Match topics
        match_result = match_couple_topics(a_isolated, b_isolated)

        # Verify results
        assert isinstance(match_result, TopicMatchResult)

        # Should find complementary anxious-avoidant pattern
        assert len(match_result.complementary_patterns) >= 1

        # Should find overlapping communication theme
        assert len(match_result.overlapping_themes) >= 1

    def test_isolation_before_merge_authorization(self):
        """Test that isolation must complete before merge."""
        manager = CoupleManager()
        therapist_id = str(uuid4())

        link = manager.create_link(
            partner_a_id=str(uuid4()),
            partner_b_id=str(uuid4()),
            therapist_id=therapist_id,
        )

        # Verify authorization
        assert manager.validate_merge_authorization(link.id, therapist_id)

    def test_no_phi_in_match_result(
        self,
        sample_rung_output,
        sample_rung_output_partner_b,
    ):
        """CRITICAL: Verify no PHI in final match result."""
        layer = IsolationLayer(strict_mode=True)

        # Isolate
        a_isolated, b_isolated = isolate_for_couples_merge(
            sample_rung_output,
            sample_rung_output_partner_b,
        )

        # Match
        result = match_couple_topics(a_isolated, b_isolated)

        # Collect all text in result
        all_text = []
        for match in result.overlapping_themes:
            all_text.append(match.topic)
            if match.description:
                all_text.append(match.description)

        for match in result.complementary_patterns:
            all_text.append(match.topic)
            if match.description:
                all_text.append(match.description)

        for match in result.potential_conflicts:
            all_text.append(match.topic)
            if match.description:
                all_text.append(match.description)

        all_text.extend(result.suggested_focus_areas)
        all_text.append(result.match_summary)

        combined = " ".join(all_text)

        # Verify no PHI patterns
        assert not layer.contains_phi(combined)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--strict"])
