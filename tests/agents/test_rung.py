"""
Rung Agent Tests for Phase 2B

Tests verify:
1. Output schema validation
2. Bedrock client integration
3. Framework detection accuracy
4. Risk flag detection
5. Prompt loading
"""

import json
import os
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

# Set test environment variables before imports
os.environ["AWS_REGION"] = "us-east-1"

from src.agents.schemas.rung_output import (
    RungAnalysisOutput,
    RungAnalysisRequest,
    FrameworkIdentified,
    DefenseMechanism,
    RiskFlag,
    RiskLevel,
    AttachmentStyle,
    DefenseMechanismType,
    CommunicationPattern,
    RelationshipDynamic,
)
from src.agents.rung import RungAgent, RungAgentError
from src.services.bedrock_client import (
    BedrockClient,
    BedrockResponse,
    BedrockClientError,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_transcript():
    """Sample client voice memo transcript."""
    return """
    I've been feeling really overwhelmed lately. My partner keeps asking me what's wrong
    and I just shut down. I know I should talk about it, but every time I try, I just
    feel like they won't understand. It's easier to just say everything is fine.

    Work has been stressful too. My boss criticized my presentation and I've been
    replaying it in my head all week. I keep thinking about how I could have done better,
    how stupid I must have looked. I know I'm probably overthinking it but I can't stop.

    I've been having trouble sleeping. I wake up at 3am and can't get back to sleep.
    Sometimes I wonder if things will ever get better. Not that I'd do anything,
    I just feel stuck.
    """


@pytest.fixture
def sample_high_risk_transcript():
    """Sample transcript with high-risk indicators."""
    return """
    I don't see the point anymore. I've been thinking about ending it all.
    I have a plan and I've been giving away some of my things.
    No one would even notice if I was gone.
    """


@pytest.fixture
def sample_analysis_response():
    """Sample JSON response from Rung analysis."""
    return {
        "frameworks_identified": [
            {
                "name": "Avoidant Attachment",
                "confidence": 0.85,
                "evidence": "Client describes shutting down when partner asks what's wrong",
                "category": "attachment"
            },
            {
                "name": "Stonewalling",
                "confidence": 0.75,
                "evidence": "Says it's easier to just say everything is fine",
                "category": "communication"
            }
        ],
        "defense_mechanisms": [
            {
                "type": "intellectualization",
                "indicators": ["replaying presentation", "analyzing how to do better"],
                "context": "Work criticism"
            },
            {
                "type": "avoidance",
                "indicators": ["shutting down", "saying everything is fine"],
                "context": "Partner communication"
            }
        ],
        "risk_flags": [
            {
                "level": "low",
                "description": "Passive hopelessness expressed ('wonder if things will ever get better')",
                "recommended_action": "Explore feelings of hopelessness, assess for suicidal ideation"
            }
        ],
        "key_themes": [
            "Emotional avoidance",
            "Perfectionism and self-criticism",
            "Sleep disturbance",
            "Relationship communication difficulties"
        ],
        "suggested_exploration": [
            "Attachment history and patterns in relationships",
            "Origin of perfectionist tendencies",
            "Coping strategies for overwhelm"
        ],
        "session_questions": [
            "When you shut down with your partner, what are you feeling in that moment?",
            "What would it mean if your partner truly understood what you're going through?",
            "Tell me more about these thoughts of 'things not getting better' - what comes up for you?"
        ],
        "analysis_confidence": 0.78
    }


@pytest.fixture
def mock_bedrock_client(sample_analysis_response):
    """Create mock Bedrock client."""
    mock_client = MagicMock(spec=BedrockClient)
    mock_response = BedrockResponse(
        content=json.dumps(sample_analysis_response),
        input_tokens=500,
        output_tokens=800,
        stop_reason="end_turn",
        model_id="anthropic.claude-3-5-sonnet-20241022-v2:0"
    )
    mock_client.invoke_with_json_output.return_value = (sample_analysis_response, mock_response)
    return mock_client


# =============================================================================
# Schema Tests
# =============================================================================

class TestRungOutputSchema:
    """Test Pydantic schema models."""

    def test_risk_level_enum(self):
        """Test RiskLevel enum values."""
        assert RiskLevel.LOW == "low"
        assert RiskLevel.MEDIUM == "medium"
        assert RiskLevel.HIGH == "high"

    def test_attachment_style_enum(self):
        """Test AttachmentStyle enum values."""
        assert AttachmentStyle.SECURE == "secure"
        assert AttachmentStyle.ANXIOUS == "anxious"
        assert AttachmentStyle.AVOIDANT == "avoidant"
        assert AttachmentStyle.DISORGANIZED == "disorganized"

    def test_defense_mechanism_types(self):
        """Test DefenseMechanismType enum."""
        assert DefenseMechanismType.INTELLECTUALIZATION == "intellectualization"
        assert DefenseMechanismType.PROJECTION == "projection"
        assert DefenseMechanismType.DENIAL == "denial"

    def test_communication_patterns(self):
        """Test Gottman patterns enum."""
        assert CommunicationPattern.CRITICISM == "criticism"
        assert CommunicationPattern.CONTEMPT == "contempt"
        assert CommunicationPattern.DEFENSIVENESS == "defensiveness"
        assert CommunicationPattern.STONEWALLING == "stonewalling"

    def test_relationship_dynamics(self):
        """Test RelationshipDynamic enum."""
        assert RelationshipDynamic.PURSUER_DISTANCER == "pursuer_distancer"
        assert RelationshipDynamic.PARENT_CHILD == "parent_child"

    def test_framework_identified_model(self):
        """Test FrameworkIdentified model."""
        framework = FrameworkIdentified(
            name="Avoidant Attachment",
            confidence=0.85,
            evidence="Client shuts down during conflict",
            category="attachment"
        )
        assert framework.name == "Avoidant Attachment"
        assert framework.confidence == 0.85
        assert framework.category == "attachment"

    def test_framework_confidence_validation(self):
        """Test confidence must be 0.0-1.0."""
        with pytest.raises(ValueError):
            FrameworkIdentified(
                name="Test",
                confidence=1.5,  # Invalid
                evidence="test"
            )

    def test_defense_mechanism_model(self):
        """Test DefenseMechanism model."""
        defense = DefenseMechanism(
            type="intellectualization",
            indicators=["overanalyzing", "detached reasoning"],
            context="Discussing relationship"
        )
        assert defense.type == "intellectualization"
        assert len(defense.indicators) == 2

    def test_risk_flag_model(self):
        """Test RiskFlag model."""
        risk = RiskFlag(
            level=RiskLevel.MEDIUM,
            description="Expressed hopelessness",
            recommended_action="Assess for suicidal ideation"
        )
        assert risk.level == RiskLevel.MEDIUM
        assert "hopelessness" in risk.description

    def test_analysis_output_model(self):
        """Test complete RungAnalysisOutput model."""
        output = RungAnalysisOutput(
            frameworks_identified=[
                FrameworkIdentified(name="Test", confidence=0.8, evidence="test")
            ],
            key_themes=["Theme 1", "Theme 2"],
            session_questions=["Question 1?"],
            analysis_confidence=0.75
        )
        assert len(output.frameworks_identified) == 1
        assert len(output.key_themes) == 2
        assert output.analysis_confidence == 0.75

    def test_analysis_request_model(self):
        """Test RungAnalysisRequest model."""
        request = RungAnalysisRequest(
            session_id=str(uuid4()),
            client_id=str(uuid4()),
            transcript="Test transcript",
            session_number=5
        )
        assert request.transcript == "Test transcript"
        assert request.session_number == 5


# =============================================================================
# Bedrock Client Tests
# =============================================================================

class TestBedrockClient:
    """Test Bedrock client functionality."""

    def test_client_initialization(self):
        """Test client initializes with defaults."""
        client = BedrockClient()
        assert client.model_id == BedrockClient.DEFAULT_MODEL_ID
        assert client.max_tokens == 4096
        assert client.temperature == 0.3

    def test_client_custom_params(self):
        """Test client with custom parameters."""
        client = BedrockClient(
            model_id="custom-model",
            max_tokens=2048,
            temperature=0.5,
            region="us-west-2"
        )
        assert client.model_id == "custom-model"
        assert client.max_tokens == 2048
        assert client.temperature == 0.5
        assert client.region == "us-west-2"

    @patch("src.services.bedrock_client._get_client")
    def test_invoke_success(self, mock_get_client):
        """Test successful invoke."""
        mock_boto_client = MagicMock()
        mock_get_client.return_value = mock_boto_client

        mock_boto_client.invoke_model.return_value = {
            "body": MagicMock(read=lambda: json.dumps({
                "content": [{"type": "text", "text": "Response"}],
                "usage": {"input_tokens": 100, "output_tokens": 50},
                "stop_reason": "end_turn"
            }).encode())
        }

        client = BedrockClient()
        response = client.invoke("System prompt", "User message")

        assert response.content == "Response"
        assert response.input_tokens == 100
        assert response.output_tokens == 50

    @patch("src.services.bedrock_client._get_client")
    def test_invoke_with_json_output(self, mock_get_client):
        """Test JSON parsing in invoke."""
        mock_boto_client = MagicMock()
        mock_get_client.return_value = mock_boto_client

        json_response = {"key": "value", "number": 42}
        mock_boto_client.invoke_model.return_value = {
            "body": MagicMock(read=lambda: json.dumps({
                "content": [{"type": "text", "text": json.dumps(json_response)}],
                "usage": {"input_tokens": 100, "output_tokens": 50},
                "stop_reason": "end_turn"
            }).encode())
        }

        client = BedrockClient()
        parsed, response = client.invoke_with_json_output("System", "User")

        assert parsed["key"] == "value"
        assert parsed["number"] == 42

    @patch("src.services.bedrock_client._get_client")
    def test_invoke_handles_markdown_json(self, mock_get_client):
        """Test JSON extraction from markdown code blocks."""
        mock_boto_client = MagicMock()
        mock_get_client.return_value = mock_boto_client

        json_response = {"result": "success"}
        markdown_json = f"```json\n{json.dumps(json_response)}\n```"

        mock_boto_client.invoke_model.return_value = {
            "body": MagicMock(read=lambda: json.dumps({
                "content": [{"type": "text", "text": markdown_json}],
                "usage": {"input_tokens": 100, "output_tokens": 50},
                "stop_reason": "end_turn"
            }).encode())
        }

        client = BedrockClient()
        parsed, _ = client.invoke_with_json_output("System", "User")

        assert parsed["result"] == "success"


# =============================================================================
# Rung Agent Tests
# =============================================================================

class TestRungAgent:
    """Test Rung agent functionality."""

    def test_agent_initialization(self, mock_bedrock_client):
        """Test agent initializes correctly."""
        agent = RungAgent(bedrock_client=mock_bedrock_client)
        assert agent.bedrock_client == mock_bedrock_client
        assert agent.temperature == RungAgent.DEFAULT_TEMPERATURE

    def test_system_prompt_loading(self):
        """Test system prompt loads correctly."""
        agent = RungAgent()
        prompt = agent.system_prompt

        assert "Rung" in prompt
        assert "clinical analysis" in prompt.lower()
        assert "JSON" in prompt

    def test_analyze_returns_valid_output(
        self, mock_bedrock_client, sample_transcript
    ):
        """Test analyze returns valid RungAnalysisOutput."""
        agent = RungAgent(bedrock_client=mock_bedrock_client)

        request = RungAnalysisRequest(
            session_id=str(uuid4()),
            client_id=str(uuid4()),
            transcript=sample_transcript
        )

        output = agent.analyze(request)

        assert isinstance(output, RungAnalysisOutput)
        assert len(output.frameworks_identified) > 0
        assert len(output.key_themes) > 0

    def test_analyze_text_convenience_method(
        self, mock_bedrock_client, sample_transcript
    ):
        """Test analyze_text convenience method."""
        agent = RungAgent(bedrock_client=mock_bedrock_client)
        output = agent.analyze_text(sample_transcript)

        assert isinstance(output, RungAnalysisOutput)

    def test_detect_frameworks(
        self, mock_bedrock_client, sample_transcript
    ):
        """Test framework detection."""
        agent = RungAgent(bedrock_client=mock_bedrock_client)
        frameworks = agent.detect_frameworks(sample_transcript)

        assert len(frameworks) > 0
        assert all(isinstance(f, FrameworkIdentified) for f in frameworks)
        assert any("Avoidant" in f.name for f in frameworks)

    def test_assess_risk(
        self, mock_bedrock_client, sample_transcript
    ):
        """Test risk assessment."""
        agent = RungAgent(bedrock_client=mock_bedrock_client)
        risks = agent.assess_risk(sample_transcript)

        assert isinstance(risks, list)
        assert all(isinstance(r, RiskFlag) for r in risks)

    def test_has_high_risk_false(
        self, mock_bedrock_client, sample_transcript
    ):
        """Test has_high_risk returns False for low-risk content."""
        agent = RungAgent(bedrock_client=mock_bedrock_client)
        result = agent.has_high_risk(sample_transcript)

        assert result is False

    def test_user_message_includes_transcript(
        self, mock_bedrock_client, sample_transcript
    ):
        """Test user message is built correctly."""
        agent = RungAgent(bedrock_client=mock_bedrock_client)

        request = RungAnalysisRequest(
            session_id=str(uuid4()),
            client_id=str(uuid4()),
            transcript=sample_transcript,
            historical_context="Previous session notes",
            session_number=3
        )

        message = agent._build_user_message(request)

        assert sample_transcript in message
        assert "Previous session notes" in message
        assert "session #3" in message

    def test_output_includes_metadata(
        self, mock_bedrock_client, sample_transcript
    ):
        """Test output includes analysis metadata."""
        agent = RungAgent(bedrock_client=mock_bedrock_client)
        output = agent.analyze_text(sample_transcript)

        assert output.raw_text_length == len(sample_transcript)
        assert output.analysis_confidence is not None


class TestRungFrameworkDetection:
    """Test specific framework detection capabilities."""

    def test_detects_avoidant_attachment(self, mock_bedrock_client, sample_transcript):
        """Test detection of avoidant attachment patterns."""
        agent = RungAgent(bedrock_client=mock_bedrock_client)
        frameworks = agent.detect_frameworks(sample_transcript)

        avoidant = [f for f in frameworks if "avoidant" in f.name.lower()]
        assert len(avoidant) > 0
        assert avoidant[0].confidence > 0.5

    def test_detects_stonewalling(self, mock_bedrock_client, sample_transcript):
        """Test detection of Gottman stonewalling pattern."""
        agent = RungAgent(bedrock_client=mock_bedrock_client)
        frameworks = agent.detect_frameworks(sample_transcript)

        stonewalling = [f for f in frameworks if "stonewalling" in f.name.lower()]
        assert len(stonewalling) > 0


class TestRungRiskDetection:
    """Test risk flag detection."""

    def test_detects_high_risk_indicators(self, sample_high_risk_transcript):
        """Test detection of high-risk content."""
        # Create mock that returns high risk
        mock_client = MagicMock(spec=BedrockClient)
        high_risk_response = {
            "frameworks_identified": [],
            "defense_mechanisms": [],
            "risk_flags": [
                {
                    "level": "high",
                    "description": "Active suicidal ideation with plan",
                    "recommended_action": "Immediate safety assessment required"
                }
            ],
            "key_themes": ["Suicidal ideation", "Hopelessness"],
            "suggested_exploration": [],
            "session_questions": [],
            "analysis_confidence": 0.95
        }
        mock_response = BedrockResponse(
            content=json.dumps(high_risk_response),
            input_tokens=200,
            output_tokens=300,
            stop_reason="end_turn",
            model_id="test"
        )
        mock_client.invoke_with_json_output.return_value = (high_risk_response, mock_response)

        agent = RungAgent(bedrock_client=mock_client)
        result = agent.has_high_risk(sample_high_risk_transcript)

        assert result is True


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestRungErrorHandling:
    """Test error handling in Rung agent."""

    def test_handles_bedrock_error(self):
        """Test handling of Bedrock API errors."""
        mock_client = MagicMock(spec=BedrockClient)
        mock_client.invoke_with_json_output.side_effect = BedrockClientError("API Error")

        agent = RungAgent(bedrock_client=mock_client)

        with pytest.raises(RungAgentError) as exc_info:
            agent.analyze_text("Test")

        assert "Bedrock API call failed" in str(exc_info.value)

    def test_handles_invalid_json_response(self):
        """Test handling of invalid JSON from Bedrock."""
        mock_client = MagicMock(spec=BedrockClient)
        # Return invalid structure
        mock_client.invoke_with_json_output.return_value = (
            {"invalid": "structure"},
            BedrockResponse(
                content="{}",
                input_tokens=100,
                output_tokens=50,
                stop_reason="end_turn",
                model_id="test"
            )
        )

        agent = RungAgent(bedrock_client=mock_client)
        # Should still work with empty lists
        output = agent.analyze_text("Test")
        assert output.frameworks_identified == []


# =============================================================================
# File Existence Tests
# =============================================================================

class TestFileStructure:
    """Test that all required files exist."""

    def test_rung_agent_exists(self):
        """Verify rung.py exists."""
        path = "src/agents/rung.py"
        assert os.path.exists(path), f"Missing {path}"

    def test_rung_system_prompt_exists(self):
        """Verify rung_system.txt exists."""
        path = "src/agents/prompts/rung_system.txt"
        assert os.path.exists(path), f"Missing {path}"

    def test_rung_output_schema_exists(self):
        """Verify rung_output.py exists."""
        path = "src/agents/schemas/rung_output.py"
        assert os.path.exists(path), f"Missing {path}"

    def test_bedrock_client_exists(self):
        """Verify bedrock_client.py exists."""
        path = "src/services/bedrock_client.py"
        assert os.path.exists(path), f"Missing {path}"


# =============================================================================
# Integration Tests (Mock-Based)
# =============================================================================

class TestRungIntegration:
    """Integration tests with mocked Bedrock."""

    def test_full_analysis_workflow(
        self, mock_bedrock_client, sample_transcript
    ):
        """Test complete analysis workflow."""
        agent = RungAgent(bedrock_client=mock_bedrock_client)

        request = RungAnalysisRequest(
            session_id=str(uuid4()),
            client_id=str(uuid4()),
            transcript=sample_transcript,
            historical_context="Client has history of avoidant attachment",
            session_number=5
        )

        output = agent.analyze(request)

        # Verify complete output
        assert isinstance(output, RungAnalysisOutput)
        assert len(output.frameworks_identified) >= 1
        assert len(output.defense_mechanisms) >= 1
        assert len(output.key_themes) >= 1
        assert len(output.session_questions) >= 1
        assert output.analysis_confidence is not None

    def test_multiple_analyses_use_cached_prompt(self, mock_bedrock_client):
        """Test that system prompt is cached."""
        agent = RungAgent(bedrock_client=mock_bedrock_client)

        # Access prompt twice
        prompt1 = agent.system_prompt
        prompt2 = agent.system_prompt

        # Should be same object (cached)
        assert prompt1 is prompt2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
