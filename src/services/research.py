"""
Research Service

Integrates Perplexity research with anonymization layer.
Provides safe, HIPAA-compliant research capabilities for Rung.

CRITICAL: All queries pass through anonymization before external API calls.
"""

import os
from dataclasses import dataclass, field
from typing import Optional

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
    Citation,
)


@dataclass
class ResearchResult:
    """Result from research query."""
    query: str
    anonymized_query: str
    citations: list[Citation] = field(default_factory=list)
    key_findings: list[str] = field(default_factory=list)
    recommended_techniques: list[str] = field(default_factory=list)
    raw_response: Optional[str] = None
    cached: bool = False


@dataclass
class ResearchBatch:
    """Batch of research results from multiple queries."""
    results: list[ResearchResult] = field(default_factory=list)
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    blocked_queries: int = 0


class ResearchError(Exception):
    """Exception for research service errors."""
    pass


class ResearchService:
    """
    HIPAA-compliant research service.

    Provides research capabilities with mandatory anonymization.
    All queries are validated and anonymized before external API calls.

    Workflow:
    1. Receive query or Rung analysis output
    2. Anonymize query (block if PHI detected)
    3. Send anonymized query to Perplexity
    4. Parse and return structured results
    """

    def __init__(
        self,
        perplexity_client: Optional[PerplexityClient] = None,
        anonymizer: Optional[QueryAnonymizer] = None,
        strict_mode: bool = True,
    ):
        """
        Initialize research service.

        Args:
            perplexity_client: Optional pre-configured Perplexity client
            anonymizer: Optional pre-configured anonymizer
            strict_mode: If True, reject any query with detected PHI
        """
        self.perplexity = perplexity_client or PerplexityClient()
        self.anonymizer = anonymizer or QueryAnonymizer(strict_mode=strict_mode)
        self.query_builder = FrameworkQueryBuilder(self.anonymizer)
        self.strict_mode = strict_mode

    def research_framework(self, framework_name: str) -> ResearchResult:
        """
        Research evidence-based interventions for a framework.

        Args:
            framework_name: Name of the psychological framework

        Returns:
            ResearchResult with citations and techniques

        Raises:
            ResearchError: If anonymization fails or API error
        """
        try:
            # Build and anonymize query
            query = f"evidence-based interventions for {framework_name} in therapy"
            anon_result = self.anonymizer.anonymize(query)

            if not anon_result.is_safe:
                raise ResearchError(
                    f"Query blocked: {anon_result.rejection_reason}"
                )

            # Call Perplexity
            response = self.perplexity.search_therapy_intervention(framework_name)

            # Parse findings
            findings, techniques = self._extract_findings(response.answer)

            return ResearchResult(
                query=query,
                anonymized_query=anon_result.anonymized_query,
                citations=response.citations,
                key_findings=findings,
                recommended_techniques=techniques,
                raw_response=response.answer,
                cached=response.cached,
            )

        except AnonymizationError as e:
            raise ResearchError(f"Anonymization failed: {str(e)}") from e
        except PerplexityError as e:
            raise ResearchError(f"Research API error: {str(e)}") from e

    def research_defense_mechanism(self, mechanism: str) -> ResearchResult:
        """
        Research a defense mechanism.

        Args:
            mechanism: Name of the defense mechanism

        Returns:
            ResearchResult with research findings
        """
        try:
            query = f"clinical research on {mechanism} defense mechanism"
            anon_result = self.anonymizer.anonymize(query)

            if not anon_result.is_safe:
                raise ResearchError(
                    f"Query blocked: {anon_result.rejection_reason}"
                )

            response = self.perplexity.search_defense_mechanism(mechanism)
            findings, techniques = self._extract_findings(response.answer)

            return ResearchResult(
                query=query,
                anonymized_query=anon_result.anonymized_query,
                citations=response.citations,
                key_findings=findings,
                recommended_techniques=techniques,
                raw_response=response.answer,
                cached=response.cached,
            )

        except (AnonymizationError, PerplexityError) as e:
            raise ResearchError(str(e)) from e

    def research_relationship_pattern(self, pattern: str) -> ResearchResult:
        """
        Research a relationship/couples pattern.

        Args:
            pattern: Relationship pattern name

        Returns:
            ResearchResult with couples therapy approaches
        """
        try:
            query = f"couples therapy approaches for {pattern}"
            anon_result = self.anonymizer.anonymize(query)

            if not anon_result.is_safe:
                raise ResearchError(
                    f"Query blocked: {anon_result.rejection_reason}"
                )

            response = self.perplexity.search_couples_therapy(pattern)
            findings, techniques = self._extract_findings(response.answer)

            return ResearchResult(
                query=query,
                anonymized_query=anon_result.anonymized_query,
                citations=response.citations,
                key_findings=findings,
                recommended_techniques=techniques,
                raw_response=response.answer,
                cached=response.cached,
            )

        except (AnonymizationError, PerplexityError) as e:
            raise ResearchError(str(e)) from e

    def research_from_rung_output(self, rung_output: dict) -> ResearchBatch:
        """
        Generate research for all frameworks in Rung output.

        Args:
            rung_output: Dictionary from RungAnalysisOutput

        Returns:
            ResearchBatch with all research results
        """
        batch = ResearchBatch()
        results = []

        # Research frameworks
        for framework in rung_output.get("frameworks_identified", []):
            name = framework.get("name", "")
            if not name:
                continue

            batch.total_queries += 1
            try:
                result = self.research_framework(name)
                results.append(result)
                batch.successful_queries += 1
            except ResearchError as e:
                if "blocked" in str(e).lower():
                    batch.blocked_queries += 1
                else:
                    batch.failed_queries += 1

        # Research defense mechanisms
        for defense in rung_output.get("defense_mechanisms", []):
            mechanism = defense.get("type", "")
            if not mechanism:
                continue

            batch.total_queries += 1
            try:
                result = self.research_defense_mechanism(mechanism)
                results.append(result)
                batch.successful_queries += 1
            except ResearchError as e:
                if "blocked" in str(e).lower():
                    batch.blocked_queries += 1
                else:
                    batch.failed_queries += 1

        batch.results = results
        return batch

    def validate_query(self, query: str) -> AnonymizationResult:
        """
        Validate a query without executing it.

        Args:
            query: Query to validate

        Returns:
            AnonymizationResult with safety status
        """
        return self.anonymizer.anonymize(query)

    def is_query_safe(self, query: str) -> bool:
        """
        Quick check if a query is safe for research.

        Args:
            query: Query to check

        Returns:
            True if safe, False if PHI detected
        """
        return self.anonymizer.is_safe(query)

    def _extract_findings(self, text: str) -> tuple[list[str], list[str]]:
        """
        Extract key findings and techniques from response text.

        Args:
            text: Response text from Perplexity

        Returns:
            Tuple of (key_findings, recommended_techniques)
        """
        findings = []
        techniques = []

        if not text:
            return findings, techniques

        # Split into sentences
        sentences = text.replace("\n", " ").split(". ")

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Classify sentence
            lower = sentence.lower()

            # Technique indicators
            technique_words = [
                "technique", "approach", "intervention", "strategy",
                "method", "practice", "exercise", "skill", "tool"
            ]
            if any(word in lower for word in technique_words):
                techniques.append(sentence + ".")
            # Finding indicators
            elif any(word in lower for word in ["research", "study", "found", "shows", "evidence"]):
                findings.append(sentence + ".")

        # Limit to top results
        return findings[:5], techniques[:5]
