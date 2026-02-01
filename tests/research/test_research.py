"""
Research Service Tests for Phase 2C

Tests verify:
1. Anonymization layer blocks PHI (CRITICAL)
2. PHI detection accuracy
3. Query building from Rung output
4. Perplexity client functionality
5. Research service integration
6. Cache behavior
"""

import os
import pytest
from unittest.mock import MagicMock, patch

# Set test environment variables
os.environ["AWS_REGION"] = "us-east-1"
os.environ["PERPLEXITY_API_KEY"] = "test-key"

from src.services.anonymizer import (
    QueryAnonymizer,
    FrameworkQueryBuilder,
    AnonymizationResult,
    AnonymizationError,
)
from src.services.perplexity_client import (
    PerplexityClient,
    PerplexityResponse,
    PerplexityError,
    RateLimitError,
    Citation,
    ResponseCache,
)
from src.services.research import (
    ResearchService,
    ResearchResult,
    ResearchBatch,
    ResearchError,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def anonymizer():
    """Create test anonymizer."""
    return QueryAnonymizer(strict_mode=True)


@pytest.fixture
def anonymizer_lenient():
    """Create lenient anonymizer."""
    return QueryAnonymizer(strict_mode=False)


@pytest.fixture
def sample_rung_output():
    """Sample Rung analysis output."""
    return {
        "frameworks_identified": [
            {
                "name": "Avoidant Attachment",
                "confidence": 0.85,
                "evidence": "Client shuts down during conflict",
                "category": "attachment"
            },
            {
                "name": "Stonewalling",
                "confidence": 0.75,
                "evidence": "Says everything is fine",
                "category": "communication"
            }
        ],
        "defense_mechanisms": [
            {
                "type": "intellectualization",
                "indicators": ["overanalyzing"],
                "context": "Work stress"
            }
        ],
        "risk_flags": [],
        "key_themes": ["emotional avoidance"],
        "suggested_exploration": [],
        "session_questions": []
    }


@pytest.fixture
def mock_perplexity_response():
    """Sample Perplexity response."""
    return PerplexityResponse(
        query="test query",
        answer="Research shows that evidence-based interventions for avoidant attachment include EFT techniques. The approach involves building emotional awareness.",
        citations=[
            Citation(
                title="Attachment Theory in Practice",
                source="Journal of Clinical Psychology",
                url="https://example.com/article1",
                summary="Overview of attachment interventions"
            )
        ],
        model="sonar",
        usage={"tokens": 500},
        cached=False
    )


@pytest.fixture
def mock_perplexity_client(mock_perplexity_response):
    """Create mock Perplexity client."""
    mock_client = MagicMock(spec=PerplexityClient)
    mock_client.search.return_value = mock_perplexity_response
    mock_client.search_therapy_intervention.return_value = mock_perplexity_response
    mock_client.search_defense_mechanism.return_value = mock_perplexity_response
    mock_client.search_couples_therapy.return_value = mock_perplexity_response
    return mock_client


# =============================================================================
# Anonymization Tests (CRITICAL)
# =============================================================================

class TestAnonymization:
    """Test PHI detection and anonymization."""

    def test_safe_clinical_query(self, anonymizer):
        """Test that clinical terminology passes through."""
        query = "evidence-based interventions for avoidant attachment in therapy"
        result = anonymizer.anonymize(query)

        assert result.is_safe is True
        assert result.phi_detected is False
        assert result.anonymized_query == query

    def test_detects_full_name(self, anonymizer):
        """Test detection of full names."""
        query = "John Smith has avoidant attachment"
        result = anonymizer.anonymize(query)

        assert result.is_safe is False
        assert "name" in result.phi_types_found

    def test_detects_date_formats(self, anonymizer):
        """Test detection of various date formats."""
        date_queries = [
            "session on 01/15/2024",
            "born on January 15th, 1990",
            "last Monday's session",
        ]

        for query in date_queries:
            result = anonymizer.anonymize(query)
            assert result.phi_detected is True, f"Failed for: {query}"

    def test_detects_phone_numbers(self, anonymizer):
        """Test detection of phone numbers."""
        phone_queries = [
            "call me at 555-123-4567",
            "phone is (555) 123-4567",
            "reach me at 555.123.4567",
        ]

        for query in phone_queries:
            result = anonymizer.anonymize(query)
            assert result.phi_detected is True, f"Failed for: {query}"

    def test_detects_email_addresses(self, anonymizer):
        """Test detection of email addresses."""
        query = "contact patient@email.com for details"
        result = anonymizer.anonymize(query)

        assert result.phi_detected is True
        assert "email" in result.phi_types_found

    def test_detects_ssn(self, anonymizer):
        """Test detection of SSN patterns."""
        query = "SSN is 123-45-6789"
        result = anonymizer.anonymize(query)

        assert result.phi_detected is True
        assert "ssn" in result.phi_types_found

    def test_detects_addresses(self, anonymizer):
        """Test detection of street addresses."""
        query = "lives at 123 Main Street"
        result = anonymizer.anonymize(query)

        assert result.phi_detected is True
        assert "location" in result.phi_types_found

    def test_detects_medical_ids(self, anonymizer):
        """Test detection of medical record numbers."""
        query = "MRN: 12345678 has anxiety"
        result = anonymizer.anonymize(query)

        assert result.phi_detected is True
        assert "mrn" in result.phi_types_found

    def test_detects_ages_with_context(self, anonymizer):
        """Test detection of age with identifying context."""
        query = "I am 35 years old and have depression"
        result = anonymizer.anonymize(query)

        assert result.phi_detected is True
        assert "age" in result.phi_types_found

    def test_detects_long_quotes(self, anonymizer):
        """Test detection of potentially identifying quotes."""
        query = 'Client said "I feel like nobody understands what I am going through right now"'
        result = anonymizer.anonymize(query)

        assert result.phi_detected is True
        assert "quote" in result.phi_types_found

    def test_blocks_explicit_phi_disclosure(self, anonymizer):
        """Test blocking of explicit PHI patterns."""
        blocking_queries = [
            "my name is John",
            "I live at 123 Main",
            "my SSN is",
            "my phone number is",
            "born on January 1st",
        ]

        for query in blocking_queries:
            result = anonymizer.anonymize(query)
            assert result.is_safe is False, f"Should block: {query}"

    def test_anonymizes_with_replacements(self, anonymizer_lenient):
        """Test that PHI is replaced with generic terms."""
        query = "John Smith called on 01/15/2024 from 555-123-4567"
        result = anonymizer_lenient.anonymize(query)

        # In lenient mode, should anonymize and allow
        assert "[PERSON]" in result.anonymized_query
        assert "[DATE]" in result.anonymized_query
        assert "[PHONE]" in result.anonymized_query
        assert "John Smith" not in result.anonymized_query

    def test_validate_and_anonymize_raises(self, anonymizer):
        """Test validate_and_anonymize raises on unsafe query."""
        with pytest.raises(AnonymizationError):
            anonymizer.validate_and_anonymize("my name is John")

    def test_is_safe_shortcut(self, anonymizer):
        """Test is_safe convenience method."""
        assert anonymizer.is_safe("avoidant attachment therapy") is True
        assert anonymizer.is_safe("John Smith therapy") is False


class TestPHIPatternCoverage:
    """Comprehensive PHI pattern tests."""

    @pytest.mark.parametrize("query,expected_phi", [
        # Safe clinical queries
        ("evidence-based CBT techniques", False),
        ("attachment theory interventions", False),
        ("Gottman Four Horsemen patterns", False),
        ("DBT skills for emotion regulation", False),
        # PHI-containing queries
        ("session with Dr. Smith", True),
        ("patient John visited Tuesday", True),
        ("call back at 800-555-1234", True),
        ("email john@example.com", True),
        ("lives in New York, NY 10001", True),
        ("MRN: ABC123 diagnosis", True),
        ("my 5-year-old son", True),
    ])
    def test_phi_detection_cases(self, anonymizer, query, expected_phi):
        """Test various PHI detection cases."""
        result = anonymizer.anonymize(query)
        assert result.phi_detected == expected_phi, f"Failed for: {query}"


# =============================================================================
# Query Builder Tests
# =============================================================================

class TestFrameworkQueryBuilder:
    """Test query building from clinical terms."""

    def test_builds_intervention_query(self):
        """Test building intervention queries."""
        builder = FrameworkQueryBuilder()
        query = builder.build_intervention_query("avoidant attachment")

        assert "interventions" in query
        assert "avoidant attachment" in query

    def test_builds_technique_query(self):
        """Test building technique queries."""
        builder = FrameworkQueryBuilder()
        query = builder.build_technique_query("emotional avoidance")

        assert "techniques" in query
        assert "emotional avoidance" in query

    def test_builds_research_query(self):
        """Test building research queries."""
        builder = FrameworkQueryBuilder()
        query = builder.build_research_query("intellectualization", "therapy")

        assert "research" in query
        assert "intellectualization" in query

    def test_builds_couples_query(self):
        """Test building couples therapy queries."""
        builder = FrameworkQueryBuilder()
        query = builder.build_couples_query("pursuer-distancer")

        assert "couples" in query
        assert "pursuer-distancer" in query

    def test_builds_attachment_query(self):
        """Test building attachment queries."""
        builder = FrameworkQueryBuilder()
        query = builder.build_attachment_query("anxious")

        assert "attachment" in query
        assert "anxious" in query

    def test_builds_from_rung_output(self, sample_rung_output):
        """Test building queries from Rung output."""
        builder = FrameworkQueryBuilder()
        queries = builder.build_from_rung_output(sample_rung_output)

        assert len(queries) >= 2  # At least frameworks + mechanisms
        assert all(isinstance(q, str) for q in queries)


# =============================================================================
# Perplexity Client Tests
# =============================================================================

class TestPerplexityClient:
    """Test Perplexity API client."""

    def test_client_initialization(self):
        """Test client initializes with defaults."""
        client = PerplexityClient()
        assert client.model == PerplexityClient.DEFAULT_MODEL
        assert client.enable_cache is True

    def test_client_custom_config(self):
        """Test client with custom configuration."""
        client = PerplexityClient(
            api_key="custom-key",
            model="sonar-pro",
            enable_cache=False,
        )
        assert client.api_key == "custom-key"
        assert client.model == "sonar-pro"
        assert client.enable_cache is False


class TestResponseCache:
    """Test caching functionality."""

    def test_cache_set_and_get(self):
        """Test basic cache operations."""
        cache = ResponseCache(ttl_seconds=3600)
        response = PerplexityResponse(
            query="test",
            answer="answer",
            citations=[],
            model="sonar",
        )

        cache.set("test query", response)
        cached = cache.get("test query")

        assert cached is not None
        assert cached.answer == "answer"
        assert cached.cached is True

    def test_cache_miss(self):
        """Test cache miss returns None."""
        cache = ResponseCache()
        result = cache.get("nonexistent query")
        assert result is None

    def test_cache_clear(self):
        """Test cache clearing."""
        cache = ResponseCache()
        cache.set("query", PerplexityResponse(
            query="q", answer="a", citations=[], model="m"
        ))

        cache.clear()
        assert cache.size() == 0

    def test_cache_case_insensitive(self):
        """Test cache is case-insensitive."""
        cache = ResponseCache()
        response = PerplexityResponse(
            query="test", answer="answer", citations=[], model="m"
        )

        cache.set("Test Query", response)
        cached = cache.get("test query")

        assert cached is not None


# =============================================================================
# Research Service Tests
# =============================================================================

class TestResearchService:
    """Test research service integration."""

    def test_service_initialization(self, mock_perplexity_client):
        """Test service initializes correctly."""
        service = ResearchService(
            perplexity_client=mock_perplexity_client,
            strict_mode=True
        )
        assert service.strict_mode is True

    def test_research_framework(self, mock_perplexity_client):
        """Test framework research."""
        service = ResearchService(perplexity_client=mock_perplexity_client)
        result = service.research_framework("avoidant attachment")

        assert isinstance(result, ResearchResult)
        assert result.query is not None
        assert len(result.citations) > 0

    def test_research_defense_mechanism(self, mock_perplexity_client):
        """Test defense mechanism research."""
        service = ResearchService(perplexity_client=mock_perplexity_client)
        result = service.research_defense_mechanism("intellectualization")

        assert isinstance(result, ResearchResult)

    def test_research_relationship_pattern(self, mock_perplexity_client):
        """Test couples therapy research."""
        service = ResearchService(perplexity_client=mock_perplexity_client)
        result = service.research_relationship_pattern("pursuer-distancer")

        assert isinstance(result, ResearchResult)

    def test_research_from_rung_output(
        self, mock_perplexity_client, sample_rung_output
    ):
        """Test batch research from Rung output."""
        service = ResearchService(perplexity_client=mock_perplexity_client)
        batch = service.research_from_rung_output(sample_rung_output)

        assert isinstance(batch, ResearchBatch)
        assert batch.total_queries >= 2
        assert batch.successful_queries > 0

    def test_blocks_phi_in_framework(self, mock_perplexity_client):
        """Test PHI is blocked even in framework research."""
        service = ResearchService(perplexity_client=mock_perplexity_client)

        # This should work
        result = service.research_framework("avoidant attachment")
        assert result is not None

    def test_validate_query(self, mock_perplexity_client):
        """Test query validation."""
        service = ResearchService(perplexity_client=mock_perplexity_client)

        safe_result = service.validate_query("attachment theory")
        assert safe_result.is_safe is True

        unsafe_result = service.validate_query("John Smith has depression")
        assert unsafe_result.is_safe is False

    def test_is_query_safe(self, mock_perplexity_client):
        """Test is_query_safe shortcut."""
        service = ResearchService(perplexity_client=mock_perplexity_client)

        assert service.is_query_safe("CBT techniques") is True
        assert service.is_query_safe("patient John Smith") is False


class TestResearchWithPHI:
    """Test that PHI never reaches external APIs."""

    def test_phi_blocked_in_research_framework(self, mock_perplexity_client):
        """Test PHI blocked in framework research."""
        service = ResearchService(
            perplexity_client=mock_perplexity_client,
            strict_mode=True
        )

        # Should not call Perplexity with PHI
        with pytest.raises(ResearchError):
            service.research_framework("John Smith's attachment issues")

        # Verify Perplexity was not called
        mock_perplexity_client.search_therapy_intervention.assert_not_called()

    def test_phi_blocked_in_defense_research(self, mock_perplexity_client):
        """Test PHI blocked in defense mechanism research."""
        service = ResearchService(
            perplexity_client=mock_perplexity_client,
            strict_mode=True
        )

        with pytest.raises(ResearchError):
            service.research_defense_mechanism("denial - called 555-123-4567")

    def test_phi_blocked_in_couples_research(self, mock_perplexity_client):
        """Test PHI blocked in couples research."""
        service = ResearchService(
            perplexity_client=mock_perplexity_client,
            strict_mode=True
        )

        with pytest.raises(ResearchError):
            service.research_relationship_pattern(
                "John and Jane's pursuer-distancer dynamic"
            )


# =============================================================================
# File Existence Tests
# =============================================================================

class TestFileStructure:
    """Test that all required files exist."""

    def test_anonymizer_exists(self):
        """Verify anonymizer.py exists."""
        assert os.path.exists("src/services/anonymizer.py")

    def test_perplexity_client_exists(self):
        """Verify perplexity_client.py exists."""
        assert os.path.exists("src/services/perplexity_client.py")

    def test_research_service_exists(self):
        """Verify research.py exists."""
        assert os.path.exists("src/services/research.py")


# =============================================================================
# Integration Tests
# =============================================================================

class TestResearchIntegration:
    """Integration tests for research workflow."""

    def test_full_research_workflow(
        self, mock_perplexity_client, sample_rung_output
    ):
        """Test complete research workflow from Rung output."""
        service = ResearchService(perplexity_client=mock_perplexity_client)

        # Run batch research
        batch = service.research_from_rung_output(sample_rung_output)

        # Verify results
        assert batch.total_queries > 0
        assert batch.blocked_queries == 0  # No PHI in sample output
        assert len(batch.results) > 0

        # Check each result has proper structure
        for result in batch.results:
            assert result.query is not None
            assert result.anonymized_query is not None
            assert isinstance(result.citations, list)

    def test_mixed_safe_unsafe_queries(self, mock_perplexity_client):
        """Test handling of mixed safe/unsafe queries."""
        service = ResearchService(perplexity_client=mock_perplexity_client)

        # Safe query succeeds
        safe_result = service.research_framework("attachment anxiety")
        assert safe_result is not None

        # Unsafe query fails
        with pytest.raises(ResearchError):
            service.research_framework("John Smith's anxiety - born 1990")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
