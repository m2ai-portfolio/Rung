"""
Post-Session Tests for Phase 3A

Tests verify:
1. Notes encryption (placeholder)
2. Framework extraction accuracy
3. API endpoint validation
4. Homework extraction
5. Progress tracking
"""

import json
import os
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

# Set test environment variables
os.environ["AWS_REGION"] = "us-east-1"

from src.services.framework_extractor import (
    FrameworkExtractor,
    FrameworkExtractionOutput,
    HomeworkAssignment,
    FrameworkExtractorError,
)
from src.services.notes_processor import (
    NotesProcessor,
    NotesInput,
    NotesProcessingResult,
    NotesProcessorError,
)
from src.services.bedrock_client import BedrockClient, BedrockResponse


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_session_notes():
    """Sample therapist session notes."""
    return """
    Session with client today focused on communication patterns in their relationship.
    We explored attachment theory concepts, particularly how anxious attachment style
    manifests in their interactions with their partner.

    Used CBT techniques to identify cognitive distortions around rejection fears.
    Also incorporated some mindfulness exercises for grounding during anxiety.

    Client had a breakthrough moment when they recognized the pursuer-distancer
    dynamic in their relationship. This was a significant insight.

    Progress: Client is showing increased awareness of their emotional triggers.
    They successfully used the STOP technique twice this week when feeling overwhelmed.

    Homework assigned:
    - Journal about moments when they feel the urge to pursue partner (daily)
    - Practice 5-minute breathing exercise before difficult conversations
    - Read chapter 3 of "Hold Me Tight" by next session

    Next session: Explore childhood experiences that may have shaped attachment patterns.
    """


@pytest.fixture
def sample_extraction_response():
    """Sample extraction response from Claude."""
    return {
        "frameworks_discussed": [
            "Attachment Theory",
            "Anxious Attachment",
            "Pursuer-Distancer Dynamic"
        ],
        "modalities_used": [
            "CBT",
            "Mindfulness"
        ],
        "homework_assigned": [
            {
                "task": "Journal about moments when they feel the urge to pursue partner",
                "due": "daily",
                "category": "reflection"
            },
            {
                "task": "Practice 5-minute breathing exercise before difficult conversations",
                "due": "ongoing",
                "category": "practice"
            },
            {
                "task": "Read chapter 3 of 'Hold Me Tight'",
                "due": "next session",
                "category": "reading"
            }
        ],
        "breakthroughs": [
            "Client recognized the pursuer-distancer dynamic in their relationship"
        ],
        "progress_indicators": [
            "Increased awareness of emotional triggers",
            "Successfully used STOP technique twice this week"
        ],
        "areas_for_next_session": [
            "Explore childhood experiences that may have shaped attachment patterns"
        ],
        "session_summary": "Productive session focused on communication patterns and attachment theory. Client showed significant insight and progress.",
        "extraction_confidence": 0.9
    }


@pytest.fixture
def mock_bedrock_client(sample_extraction_response):
    """Create mock Bedrock client."""
    mock_client = MagicMock(spec=BedrockClient)
    mock_response = BedrockResponse(
        content=json.dumps(sample_extraction_response),
        input_tokens=500,
        output_tokens=600,
        stop_reason="end_turn",
        model_id="anthropic.claude-3-5-sonnet-20241022-v2:0"
    )
    mock_client.invoke_with_json_output.return_value = (
        sample_extraction_response, mock_response
    )
    return mock_client


# =============================================================================
# Framework Extractor Tests
# =============================================================================

class TestFrameworkExtractor:
    """Test framework extraction functionality."""

    def test_extractor_initialization(self, mock_bedrock_client):
        """Test extractor initializes correctly."""
        extractor = FrameworkExtractor(bedrock_client=mock_bedrock_client)
        assert extractor.temperature == FrameworkExtractor.DEFAULT_TEMPERATURE

    def test_extract_returns_valid_output(
        self, mock_bedrock_client, sample_session_notes
    ):
        """Test extract returns valid FrameworkExtractionOutput."""
        extractor = FrameworkExtractor(bedrock_client=mock_bedrock_client)
        output = extractor.extract(sample_session_notes)

        assert isinstance(output, FrameworkExtractionOutput)
        assert len(output.frameworks_discussed) > 0
        assert len(output.modalities_used) > 0

    def test_extract_frameworks(
        self, mock_bedrock_client, sample_session_notes
    ):
        """Test framework extraction."""
        extractor = FrameworkExtractor(bedrock_client=mock_bedrock_client)
        output = extractor.extract(sample_session_notes)

        assert "Attachment Theory" in output.frameworks_discussed
        assert "Pursuer-Distancer Dynamic" in output.frameworks_discussed

    def test_extract_modalities(
        self, mock_bedrock_client, sample_session_notes
    ):
        """Test modality extraction."""
        extractor = FrameworkExtractor(bedrock_client=mock_bedrock_client)
        output = extractor.extract(sample_session_notes)

        assert "CBT" in output.modalities_used
        assert "Mindfulness" in output.modalities_used

    def test_extract_homework(
        self, mock_bedrock_client, sample_session_notes
    ):
        """Test homework extraction."""
        extractor = FrameworkExtractor(bedrock_client=mock_bedrock_client)
        output = extractor.extract(sample_session_notes)

        assert len(output.homework_assigned) >= 2
        assert all(isinstance(hw, HomeworkAssignment) for hw in output.homework_assigned)

    def test_extract_breakthroughs(
        self, mock_bedrock_client, sample_session_notes
    ):
        """Test breakthrough extraction."""
        extractor = FrameworkExtractor(bedrock_client=mock_bedrock_client)
        output = extractor.extract(sample_session_notes)

        assert len(output.breakthroughs) > 0
        assert any("pursuer-distancer" in b.lower() for b in output.breakthroughs)

    def test_extract_progress_indicators(
        self, mock_bedrock_client, sample_session_notes
    ):
        """Test progress indicator extraction."""
        extractor = FrameworkExtractor(bedrock_client=mock_bedrock_client)
        output = extractor.extract(sample_session_notes)

        assert len(output.progress_indicators) > 0

    def test_extract_next_session_areas(
        self, mock_bedrock_client, sample_session_notes
    ):
        """Test next session areas extraction."""
        extractor = FrameworkExtractor(bedrock_client=mock_bedrock_client)
        output = extractor.extract(sample_session_notes)

        assert len(output.areas_for_next_session) > 0

    def test_extract_empty_notes_raises(self, mock_bedrock_client):
        """Test extraction with empty notes raises error."""
        extractor = FrameworkExtractor(bedrock_client=mock_bedrock_client)

        with pytest.raises(FrameworkExtractorError):
            extractor.extract("")

        with pytest.raises(FrameworkExtractorError):
            extractor.extract("   ")

    def test_extract_frameworks_only(
        self, mock_bedrock_client, sample_session_notes
    ):
        """Test convenience method for frameworks only."""
        extractor = FrameworkExtractor(bedrock_client=mock_bedrock_client)
        frameworks = extractor.extract_frameworks_only(sample_session_notes)

        assert isinstance(frameworks, list)
        assert len(frameworks) > 0

    def test_extract_homework_only(
        self, mock_bedrock_client, sample_session_notes
    ):
        """Test convenience method for homework only."""
        extractor = FrameworkExtractor(bedrock_client=mock_bedrock_client)
        homework = extractor.extract_homework(sample_session_notes)

        assert isinstance(homework, list)
        assert all(isinstance(hw, HomeworkAssignment) for hw in homework)


class TestHomeworkAssignment:
    """Test HomeworkAssignment model."""

    def test_homework_model(self):
        """Test HomeworkAssignment model creation."""
        hw = HomeworkAssignment(
            task="Practice breathing",
            due="daily",
            category="practice"
        )
        assert hw.task == "Practice breathing"
        assert hw.due == "daily"
        assert hw.category == "practice"

    def test_homework_optional_fields(self):
        """Test homework with optional fields."""
        hw = HomeworkAssignment(task="Read article")
        assert hw.task == "Read article"
        assert hw.due is None
        assert hw.category is None


# =============================================================================
# Notes Processor Tests
# =============================================================================

class TestNotesProcessor:
    """Test notes processing functionality."""

    def test_processor_initialization(self, mock_bedrock_client):
        """Test processor initializes correctly."""
        extractor = FrameworkExtractor(bedrock_client=mock_bedrock_client)
        processor = NotesProcessor(framework_extractor=extractor)
        assert processor.extractor == extractor

    def test_process_notes(self, mock_bedrock_client, sample_session_notes):
        """Test complete notes processing."""
        extractor = FrameworkExtractor(bedrock_client=mock_bedrock_client)
        processor = NotesProcessor(framework_extractor=extractor)

        input_data = NotesInput(
            session_id=str(uuid4()),
            notes=sample_session_notes,
            therapist_id=str(uuid4()),
            encrypt=True,
        )

        result = processor.process(input_data)

        assert isinstance(result, NotesProcessingResult)
        assert result.status == "completed"
        assert result.extraction_complete is True
        assert result.extraction is not None

    def test_process_empty_notes_fails(self, mock_bedrock_client):
        """Test processing empty notes fails."""
        extractor = FrameworkExtractor(bedrock_client=mock_bedrock_client)
        processor = NotesProcessor(framework_extractor=extractor)

        input_data = NotesInput(
            session_id=str(uuid4()),
            notes="",
            therapist_id=str(uuid4()),
        )

        with pytest.raises(NotesProcessorError):
            processor.process(input_data)

    def test_process_invalid_uuid_fails(self, mock_bedrock_client):
        """Test processing with invalid UUID fails."""
        extractor = FrameworkExtractor(bedrock_client=mock_bedrock_client)
        processor = NotesProcessor(framework_extractor=extractor)

        input_data = NotesInput(
            session_id="invalid-uuid",
            notes="Some notes here",
            therapist_id=str(uuid4()),
        )

        with pytest.raises(NotesProcessorError):
            processor.process(input_data)

    def test_encrypt_notes(self, mock_bedrock_client):
        """Test notes encryption (placeholder)."""
        extractor = FrameworkExtractor(bedrock_client=mock_bedrock_client)
        processor = NotesProcessor(framework_extractor=extractor)

        encrypted = processor.encrypt_notes("Test notes")
        decrypted = processor.decrypt_notes(encrypted)

        assert decrypted == "Test notes"

    def test_prepare_for_storage(
        self, mock_bedrock_client, sample_session_notes
    ):
        """Test preparing data for storage."""
        extractor = FrameworkExtractor(bedrock_client=mock_bedrock_client)
        processor = NotesProcessor(framework_extractor=extractor)

        input_data = NotesInput(
            session_id=str(uuid4()),
            notes=sample_session_notes,
            therapist_id=str(uuid4()),
        )

        # Process first
        result = processor.process(input_data)

        # Prepare for storage
        storage_data = processor.prepare_for_storage(
            input_data, result.extraction
        )

        assert "session_id" in storage_data
        assert "notes_encrypted" in storage_data
        assert "frameworks_discussed" in storage_data
        assert "homework_assigned" in storage_data

    def test_create_audit_entry(
        self, mock_bedrock_client, sample_session_notes
    ):
        """Test audit entry creation."""
        extractor = FrameworkExtractor(bedrock_client=mock_bedrock_client)
        processor = NotesProcessor(framework_extractor=extractor)

        input_data = NotesInput(
            session_id=str(uuid4()),
            notes=sample_session_notes,
            therapist_id=str(uuid4()),
        )

        result = processor.process(input_data)

        audit = processor.create_audit_entry(
            input_data, result,
            user_id=str(uuid4()),
            ip_address="127.0.0.1"
        )

        assert audit["event_type"] == "notes_processed"
        assert audit["action"] == "create"
        assert "notes_length" in audit["details"]


# =============================================================================
# Schema Tests
# =============================================================================

class TestExtractionOutput:
    """Test FrameworkExtractionOutput schema."""

    def test_extraction_output_model(self):
        """Test FrameworkExtractionOutput model."""
        output = FrameworkExtractionOutput(
            frameworks_discussed=["CBT", "DBT"],
            modalities_used=["Mindfulness"],
            homework_assigned=[HomeworkAssignment(task="Journal")],
            breakthroughs=["Insight achieved"],
            progress_indicators=["Better awareness"],
            areas_for_next_session=["Explore emotions"],
            session_summary="Good session",
            extraction_confidence=0.9,
        )

        assert len(output.frameworks_discussed) == 2
        assert output.extraction_confidence == 0.9

    def test_extraction_output_defaults(self):
        """Test extraction output default values."""
        output = FrameworkExtractionOutput()

        assert output.frameworks_discussed == []
        assert output.modalities_used == []
        assert output.homework_assigned == []
        assert output.session_summary is None


class TestNotesInput:
    """Test NotesInput schema."""

    def test_notes_input_model(self):
        """Test NotesInput model."""
        input_data = NotesInput(
            session_id=str(uuid4()),
            notes="Session notes here",
            therapist_id=str(uuid4()),
            encrypt=True,
        )

        assert input_data.encrypt is True
        assert len(input_data.notes) > 0


class TestNotesProcessingResult:
    """Test NotesProcessingResult schema."""

    def test_processing_result_model(self):
        """Test NotesProcessingResult model."""
        result = NotesProcessingResult(
            session_id=str(uuid4()),
            processing_id=str(uuid4()),
            status="completed",
            encrypted=True,
            extraction_complete=True,
        )

        assert result.status == "completed"
        assert result.extraction_complete is True


# =============================================================================
# File Existence Tests
# =============================================================================

class TestFileStructure:
    """Test that all required files exist."""

    def test_framework_extractor_exists(self):
        """Verify framework_extractor.py exists."""
        assert os.path.exists("src/services/framework_extractor.py")

    def test_notes_processor_exists(self):
        """Verify notes_processor.py exists."""
        assert os.path.exists("src/services/notes_processor.py")

    def test_post_session_api_exists(self):
        """Verify post_session.py exists."""
        assert os.path.exists("src/api/post_session.py")


# =============================================================================
# Integration Tests
# =============================================================================

class TestNotesProcessingIntegration:
    """Integration tests for notes processing."""

    def test_full_processing_workflow(
        self, mock_bedrock_client, sample_session_notes
    ):
        """Test complete processing workflow."""
        # Create processor with mocked extractor
        extractor = FrameworkExtractor(bedrock_client=mock_bedrock_client)
        processor = NotesProcessor(framework_extractor=extractor)

        # Process notes
        input_data = NotesInput(
            session_id=str(uuid4()),
            notes=sample_session_notes,
            therapist_id=str(uuid4()),
            encrypt=True,
        )

        result = processor.process(input_data)

        # Verify complete result
        assert result.status == "completed"
        assert result.extraction is not None
        assert len(result.extraction.frameworks_discussed) > 0
        assert len(result.extraction.homework_assigned) > 0
        assert result.extraction.extraction_confidence is not None

    def test_extraction_to_storage_workflow(
        self, mock_bedrock_client, sample_session_notes
    ):
        """Test extraction through to storage preparation."""
        extractor = FrameworkExtractor(bedrock_client=mock_bedrock_client)
        processor = NotesProcessor(framework_extractor=extractor)

        input_data = NotesInput(
            session_id=str(uuid4()),
            notes=sample_session_notes,
            therapist_id=str(uuid4()),
        )

        result = processor.process(input_data)
        storage_data = processor.prepare_for_storage(input_data, result.extraction)

        # Verify storage data
        assert storage_data["frameworks_discussed"] == result.extraction.frameworks_discussed
        assert len(storage_data["homework_assigned"]) == len(result.extraction.homework_assigned)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
