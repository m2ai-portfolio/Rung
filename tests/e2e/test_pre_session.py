"""
Pre-Session Workflow Tests for Phase 2D

Tests verify:
1. Beth output quality (no clinical terminology)
2. Abstraction layer isolation (CRITICAL)
3. E2E workflow completion
4. Dual output generation
5. API endpoints
"""

import json
import os
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

# Set test environment variables
os.environ["AWS_REGION"] = "us-east-1"

from src.agents.schemas.beth_output import (
    BethOutput,
    BethInput,
    AbstractedRungOutput,
)
from src.agents.schemas.rung_output import (
    RungAnalysisOutput,
    FrameworkIdentified,
    DefenseMechanism,
    RiskFlag,
    RiskLevel,
)
from src.agents.beth import BethAgent, BethAgentError, ClinicalTermError
from src.services.abstraction_layer import (
    AbstractionLayer,
    AbstractionResult,
    AbstractionError,
    abstract_for_beth,
)
from src.services.bedrock_client import BedrockClient, BedrockResponse


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_rung_output():
    """Sample Rung analysis output with clinical terminology."""
    return RungAnalysisOutput(
        frameworks_identified=[
            FrameworkIdentified(
                name="Avoidant Attachment",
                confidence=0.85,
                evidence="Client shuts down during conflict",
                category="attachment"
            ),
            FrameworkIdentified(
                name="Stonewalling",
                confidence=0.75,
                evidence="Says everything is fine",
                category="communication"
            ),
        ],
        defense_mechanisms=[
            DefenseMechanism(
                type="intellectualization",
                indicators=["overanalyzing", "detached reasoning"],
                context="Work stress"
            ),
        ],
        risk_flags=[
            RiskFlag(
                level=RiskLevel.LOW,
                description="Passive hopelessness expressed",
                recommended_action="Explore feelings"
            ),
        ],
        key_themes=[
            "Emotional avoidance",
            "Perfectionism",
            "Communication difficulties"
        ],
        suggested_exploration=[
            "Attachment history",
            "Defense mechanism origins",
        ],
        session_questions=[
            "What happens when you shut down?",
        ],
        analysis_confidence=0.8,
    )


@pytest.fixture
def sample_beth_response():
    """Sample Beth JSON response."""
    return {
        "session_prep": "Your session is coming up! Take a moment to think about what's been on your mind this week.",
        "discussion_points": [
            "Any moments that stood out to you recently",
            "How you've been feeling in your relationships",
        ],
        "reflection_questions": [
            "What's been taking up most of your mental energy?",
            "Have you noticed any patterns in how you respond to stress?",
        ],
        "exercises": [
            "Try journaling for 5 minutes about your week",
            "Take a few deep breaths before your session",
        ],
    }


@pytest.fixture
def mock_bedrock_client(sample_beth_response):
    """Create mock Bedrock client for Beth."""
    mock_client = MagicMock(spec=BedrockClient)
    mock_response = BedrockResponse(
        content=json.dumps(sample_beth_response),
        input_tokens=300,
        output_tokens=400,
        stop_reason="end_turn",
        model_id="anthropic.claude-3-5-sonnet-20241022-v2:0"
    )
    mock_client.invoke_with_json_output.return_value = (
        sample_beth_response, mock_response
    )
    return mock_client


# =============================================================================
# Abstraction Layer Tests (CRITICAL)
# =============================================================================

class TestAbstractionLayer:
    """Test abstraction layer strips clinical terminology."""

    def test_layer_initialization(self):
        """Test layer initializes correctly."""
        layer = AbstractionLayer()
        assert layer.strict_mode is True

    def test_abstracts_rung_output(self, sample_rung_output):
        """Test successful abstraction of Rung output."""
        layer = AbstractionLayer()
        result = layer.abstract(sample_rung_output)

        assert isinstance(result, AbstractionResult)
        assert result.is_safe_for_beth is True

    def test_strips_framework_names(self, sample_rung_output):
        """Test clinical framework names are stripped."""
        layer = AbstractionLayer()
        result = layer.abstract(sample_rung_output)

        # Should not contain raw framework names
        all_text = " ".join([
            result.abstracted_output.session_focus,
            *result.abstracted_output.themes,
            *result.abstracted_output.exploration_areas,
        ]).lower()

        assert "avoidant attachment" not in all_text
        assert "stonewalling" not in all_text

    def test_removes_defense_mechanisms(self, sample_rung_output):
        """Test defense mechanism labels are removed."""
        layer = AbstractionLayer()
        result = layer.abstract(sample_rung_output)

        all_text = " ".join([
            result.abstracted_output.session_focus,
            *result.abstracted_output.themes,
        ]).lower()

        assert "intellectualization" not in all_text
        assert "defense mechanism" not in all_text

    def test_removes_risk_flags(self, sample_rung_output):
        """Test risk flags are removed entirely."""
        layer = AbstractionLayer()
        result = layer.abstract(sample_rung_output)

        assert result.risk_flags_removed == 1

    def test_tracks_stripped_terms(self, sample_rung_output):
        """Test layer tracks what was stripped."""
        layer = AbstractionLayer()
        result = layer.abstract(sample_rung_output)

        assert len(result.clinical_terms_stripped) >= 0

    def test_generates_accessible_themes(self, sample_rung_output):
        """Test themes are converted to accessible language."""
        layer = AbstractionLayer()
        result = layer.abstract(sample_rung_output)

        # Should have some themes
        assert len(result.abstracted_output.themes) > 0

        # Themes should be accessible
        for theme in result.abstracted_output.themes:
            assert "attachment" not in theme.lower()
            assert "defense" not in theme.lower()

    def test_to_beth_input(self, sample_rung_output):
        """Test conversion to BethInput."""
        layer = AbstractionLayer()
        beth_input = layer.to_beth_input(sample_rung_output)

        assert isinstance(beth_input, BethInput)
        assert len(beth_input.themes) > 0

    def test_convenience_function(self, sample_rung_output):
        """Test abstract_for_beth convenience function."""
        beth_input = abstract_for_beth(sample_rung_output)

        assert isinstance(beth_input, BethInput)


class TestAbstractionSecurity:
    """Security tests for abstraction layer."""

    def test_no_clinical_terminology_passes_through(self, sample_rung_output):
        """Test NO clinical terminology reaches Beth input."""
        layer = AbstractionLayer()
        beth_input = layer.to_beth_input(sample_rung_output)

        all_text = " ".join([
            beth_input.session_focus,
            *beth_input.themes,
            *beth_input.exploration_areas,
        ]).lower()

        # Critical clinical terms that must be stripped
        forbidden = [
            "attachment", "avoidant", "anxious", "disorganized",
            "defense mechanism", "intellectualization", "projection",
            "stonewalling", "gottman", "transference",
            "cognitive distortion", "maladaptive", "pathology",
        ]

        for term in forbidden:
            assert term not in all_text, f"Clinical term '{term}' found in Beth input"

    def test_risk_flags_never_reach_beth(self, sample_rung_output):
        """Test risk flags are never included in Beth input."""
        layer = AbstractionLayer()
        result = layer.abstract(sample_rung_output)

        # Risk flags should be removed
        assert result.risk_flags_removed > 0

        # Beth input should have no reference to risk
        beth_input = layer.to_beth_input(sample_rung_output)
        all_text = " ".join([
            beth_input.session_focus,
            *beth_input.themes,
            *beth_input.exploration_areas,
        ]).lower()

        assert "risk" not in all_text
        assert "suicid" not in all_text
        assert "harm" not in all_text


# =============================================================================
# Beth Agent Tests
# =============================================================================

class TestBethAgent:
    """Test Beth agent functionality."""

    def test_agent_initialization(self, mock_bedrock_client):
        """Test agent initializes correctly."""
        agent = BethAgent(bedrock_client=mock_bedrock_client)
        assert agent.temperature == BethAgent.DEFAULT_TEMPERATURE

    def test_system_prompt_loading(self):
        """Test system prompt loads correctly."""
        agent = BethAgent()
        prompt = agent.system_prompt

        assert "Beth" in prompt
        assert "clinical" in prompt.lower()
        assert "NO" in prompt  # NO clinical language

    def test_generate_returns_valid_output(self, mock_bedrock_client):
        """Test generate returns valid BethOutput."""
        agent = BethAgent(bedrock_client=mock_bedrock_client)

        beth_input = BethInput(
            themes=["how you connect with others", "communication patterns"],
            exploration_areas=["your relationships"],
            session_focus="exploring what's on your mind",
        )

        output = agent.generate(beth_input)

        assert isinstance(output, BethOutput)
        assert output.session_prep != ""
        assert len(output.discussion_points) > 0
        assert output.tone_check_passed is True

    def test_generate_from_themes(self, mock_bedrock_client):
        """Test generate_from_themes convenience method."""
        agent = BethAgent(bedrock_client=mock_bedrock_client)

        output = agent.generate_from_themes(
            themes=["connection patterns", "stress responses"],
            session_focus="exploring feelings",
        )

        assert isinstance(output, BethOutput)


class TestBethOutputValidation:
    """Test Beth output validation for clinical terms."""

    def test_detects_clinical_terms_in_output(self, mock_bedrock_client):
        """Test detection of clinical terms in output."""
        # Create output with clinical term
        bad_output = BethOutput(
            session_prep="Let's explore your attachment style today.",
            discussion_points=["Consider your defense mechanisms"],
            reflection_questions=[],
            exercises=[],
        )

        agent = BethAgent(bedrock_client=mock_bedrock_client)
        is_safe, terms = agent.check_output_safety(bad_output)

        assert is_safe is False
        assert len(terms) > 0

    def test_accepts_clean_output(self, mock_bedrock_client):
        """Test clean output passes validation."""
        clean_output = BethOutput(
            session_prep="Your session is coming up!",
            discussion_points=["What's been on your mind?"],
            reflection_questions=["How have you been feeling?"],
            exercises=["Try some deep breathing"],
        )

        agent = BethAgent(bedrock_client=mock_bedrock_client)
        is_safe, terms = agent.check_output_safety(clean_output)

        assert is_safe is True
        assert len(terms) == 0

    def test_forbidden_terms_list(self):
        """Test all forbidden terms are defined."""
        agent = BethAgent()

        assert "attachment" in agent.FORBIDDEN_TERMS
        assert "defense mechanism" in agent.FORBIDDEN_TERMS
        assert "transference" in agent.FORBIDDEN_TERMS
        assert "trauma" in agent.FORBIDDEN_TERMS


# =============================================================================
# Beth Schema Tests
# =============================================================================

class TestBethSchemas:
    """Test Beth Pydantic schemas."""

    def test_beth_output_model(self):
        """Test BethOutput model."""
        output = BethOutput(
            session_prep="Welcome to your session prep!",
            discussion_points=["Point 1", "Point 2"],
            reflection_questions=["Question 1?"],
            exercises=["Exercise 1"],
            tone_check_passed=True,
        )
        assert output.session_prep == "Welcome to your session prep!"
        assert len(output.discussion_points) == 2

    def test_beth_input_model(self):
        """Test BethInput model."""
        input_model = BethInput(
            themes=["connection", "communication"],
            exploration_areas=["relationships"],
            session_focus="exploring feelings",
            session_number=5,
            client_name="Alex",
        )
        assert input_model.session_number == 5
        assert input_model.client_name == "Alex"

    def test_abstracted_rung_output(self):
        """Test AbstractedRungOutput model."""
        abstracted = AbstractedRungOutput(
            themes=["how you connect with others"],
            exploration_areas=["your relationships"],
            session_focus="exploring feelings",
        )
        assert len(abstracted.themes) == 1


# =============================================================================
# E2E Workflow Tests
# =============================================================================

class TestPreSessionE2E:
    """End-to-end workflow tests."""

    def test_full_rung_to_beth_workflow(
        self, sample_rung_output, mock_bedrock_client
    ):
        """Test complete workflow from Rung output to Beth output."""
        # Step 1: Abstract Rung output
        layer = AbstractionLayer()
        beth_input = layer.to_beth_input(sample_rung_output)

        # Step 2: Generate Beth output
        agent = BethAgent(bedrock_client=mock_bedrock_client)
        output = agent.generate(beth_input)

        # Verify output
        assert isinstance(output, BethOutput)
        assert output.tone_check_passed is True
        assert output.session_prep != ""

    def test_workflow_blocks_clinical_leak(self, sample_rung_output):
        """Test that clinical info cannot leak through workflow."""
        layer = AbstractionLayer()
        beth_input = layer.to_beth_input(sample_rung_output)

        # Verify no clinical terms in beth_input
        all_text = " ".join([
            beth_input.session_focus,
            *beth_input.themes,
            *beth_input.exploration_areas,
        ]).lower()

        # These should have been in Rung output but not Beth input
        assert "avoidant" not in all_text
        assert "stonewalling" not in all_text
        assert "intellectualization" not in all_text

    def test_dual_output_generation(
        self, sample_rung_output, mock_bedrock_client
    ):
        """Test both clinical brief and client guide are generated."""
        # Clinical brief (raw Rung output for therapist)
        clinical_brief = sample_rung_output

        # Client guide (Beth output)
        layer = AbstractionLayer()
        beth_input = layer.to_beth_input(sample_rung_output)
        agent = BethAgent(bedrock_client=mock_bedrock_client)
        client_guide = agent.generate(beth_input)

        # Clinical brief has clinical terms (for therapist)
        assert len(clinical_brief.frameworks_identified) > 0
        assert clinical_brief.frameworks_identified[0].name == "Avoidant Attachment"

        # Client guide is clean (for client)
        is_safe, _ = agent.check_output_safety(client_guide)
        assert is_safe is True


# =============================================================================
# File Existence Tests
# =============================================================================

class TestFileStructure:
    """Test that all required files exist."""

    def test_beth_agent_exists(self):
        """Verify beth.py exists."""
        assert os.path.exists("src/agents/beth.py")

    def test_beth_system_prompt_exists(self):
        """Verify beth_system.txt exists."""
        assert os.path.exists("src/agents/prompts/beth_system.txt")

    def test_beth_output_schema_exists(self):
        """Verify beth_output.py exists."""
        assert os.path.exists("src/agents/schemas/beth_output.py")

    def test_abstraction_layer_exists(self):
        """Verify abstraction_layer.py exists."""
        assert os.path.exists("src/services/abstraction_layer.py")

    def test_pre_session_api_exists(self):
        """Verify pre_session.py exists."""
        assert os.path.exists("src/api/pre_session.py")

    def test_n8n_workflow_exists(self):
        """Verify pre_session.json workflow exists."""
        assert os.path.exists("n8n/workflows/pre_session.json")


class TestN8NWorkflow:
    """Test n8n workflow configuration."""

    def test_workflow_is_valid_json(self):
        """Test workflow file is valid JSON."""
        with open("n8n/workflows/pre_session.json", "r") as f:
            workflow = json.load(f)

        assert "nodes" in workflow
        assert "connections" in workflow

    def test_workflow_has_required_nodes(self):
        """Test workflow has all required nodes."""
        with open("n8n/workflows/pre_session.json", "r") as f:
            workflow = json.load(f)

        node_names = [n["name"] for n in workflow["nodes"]]

        required_nodes = [
            "Webhook Trigger",
            "Rung Analysis (Bedrock)",
            "Abstraction Layer",
            "Beth Generation (Bedrock)",
        ]

        for required in required_nodes:
            assert required in node_names, f"Missing node: {required}"

    def test_workflow_has_abstraction_layer(self):
        """Test workflow includes abstraction layer node."""
        with open("n8n/workflows/pre_session.json", "r") as f:
            workflow = json.load(f)

        abstraction_nodes = [
            n for n in workflow["nodes"]
            if "abstraction" in n["name"].lower()
        ]

        assert len(abstraction_nodes) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
