"""
Query Anonymization Layer

Strips all PHI (Protected Health Information) from queries before
sending to external APIs like Perplexity.

CRITICAL: This is a security-critical component. All queries to
external research APIs MUST pass through this anonymizer.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class AnonymizationResult:
    """Result of anonymization process."""
    original_query: str
    anonymized_query: str
    phi_detected: bool
    phi_types_found: list[str]
    is_safe: bool
    rejection_reason: Optional[str] = None


class AnonymizationError(Exception):
    """Exception raised when anonymization fails or query is rejected."""
    pass


class QueryAnonymizer:
    """
    Anonymizes queries by removing PHI before external API calls.

    Implements multiple layers of PHI detection and removal:
    1. Named entity patterns (names, dates, locations)
    2. Medical identifiers (MRN, SSN, etc.)
    3. Contact information (phone, email, address)
    4. Specific incident details
    5. Quoted speech/content

    HIPAA Safe Harbor method is used as the baseline.
    """

    # Common clinical/therapy terms that should NOT trigger name detection
    CLINICAL_TERMS = {
        "avoidant", "attachment", "anxious", "secure", "disorganized",
        "cognitive", "behavioral", "therapy", "intervention", "technique",
        "stonewalling", "criticism", "contempt", "defensiveness",
        "gottman", "four", "horsemen", "patterns", "skills", "emotion",
        "regulation", "dbt", "cbt", "eft", "emdr", "mindfulness",
        "intellectualization", "projection", "denial", "rationalization",
        "depression", "anxiety", "ptsd", "trauma", "disorder",
        "research", "evidence", "based", "clinical", "therapeutic",
        "couples", "relationship", "dynamic", "pursuer", "distancer",
        "parent", "child", "enmeshment", "codependency", "boundary",
    }

    # Patterns for PHI detection
    PATTERNS = {
        # Names - patterns for detecting personal names
        "name": [
            r"\b(?:Mr\.|Mrs\.|Ms\.|Dr\.)\s+[A-Z][a-z]+\b",  # Title + Name
            r"\bmy (?:husband|wife|partner|mother|father|son|daughter|brother|sister)\s+[A-Z][a-z]+\b",
            r"\b(?:patient|client)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b",  # patient John or patient John Smith
            r"\bnamed?\s+[A-Z][a-z]+\b",  # named John
            r"\b[A-Z][a-z]+\s+and\s+[A-Z][a-z]+'s\b",  # John and Jane's
            r"\b[A-Z][a-z]+'s\s+(?:attachment|anxiety|depression|issues?|therapy)\b",  # John's attachment
        ],
        # Dates
        "date": [
            r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",  # MM/DD/YYYY
            r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4}\b",
            r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b",
            r"\blast\s+(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b",
            r"\bon\s+(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b",
        ],
        # Locations
        "location": [
            r"\b\d+\s+[A-Z][a-z]+\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct)\b",
            r"\b[A-Z][a-z]+\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct)\b",  # Street name without number
            r"\b[A-Z][a-z]+,\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?\b",  # City, ST ZIP
            r"\bat\s+[A-Z][a-z]+\s+(?:Hospital|Medical Center|Clinic)\b",
        ],
        # Phone numbers
        "phone": [
            r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
            r"\(\d{3}\)\s*\d{3}[-.\s]?\d{4}\b",
        ],
        # Email addresses
        "email": [
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        ],
        # Social Security Numbers
        "ssn": [
            r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b",
        ],
        # Medical Record Numbers (various formats)
        "mrn": [
            r"\b(?:MRN|Medical Record|Patient ID)[:\s#]*[A-Z0-9-]+\b",
        ],
        # Ages with context
        "age": [
            r"\b(?:I am|I'm|he is|she is|they are)\s+\d{1,3}\s+years?\s+old\b",
            r"\bmy\s+\d{1,2}[-\s]?year[-\s]?old\b",
        ],
        # Direct quotes (may contain identifying info)
        "quote": [
            r'"[^"]{20,}"',  # Long quotes
            r"'[^']{20,}'",  # Long single quotes
            r"(?:he|she|they)\s+said[,:]?\s+[\"'][^\"']+[\"']",
        ],
        # Specific incident markers
        "incident": [
            r"\b(?:on|last|this past)\s+(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(?:morning|afternoon|evening|night)\b",
            r"\bat\s+(?:work|school|home|the office|the hospital)\s+(?:yesterday|today|last week)\b",
        ],
    }

    # Generic replacements for detected PHI
    REPLACEMENTS = {
        "name": "[PERSON]",
        "date": "[DATE]",
        "location": "[LOCATION]",
        "phone": "[PHONE]",
        "email": "[EMAIL]",
        "ssn": "[ID]",
        "mrn": "[MEDICAL_ID]",
        "age": "[AGE]",
        "quote": "[QUOTE]",
        "incident": "[TIME_REFERENCE]",
    }

    # Words that indicate high-risk content that should block the query
    BLOCKING_PATTERNS = [
        r"\bmy\s+(?:full\s+)?name\s+is\b",
        r"\bI\s+live\s+(?:at|in)\b",
        r"\bmy\s+(?:social\s+security|SSN)\b",
        r"\bmy\s+(?:phone|cell|mobile)\s+(?:number|#)\b",
        r"\bmy\s+email\s+(?:is|address)\b",
        r"\bborn\s+on\b",
        r"\bmy\s+birthday\b",
    ]

    def __init__(self, strict_mode: bool = True):
        """
        Initialize anonymizer.

        Args:
            strict_mode: If True, reject queries with any detected PHI.
                        If False, attempt to anonymize and proceed.
        """
        self.strict_mode = strict_mode

    def _is_likely_name(self, text: str) -> bool:
        """
        Check if a capitalized word sequence is likely a personal name.

        Returns True if it looks like a name (not a clinical term).
        """
        words = text.lower().split()
        # If all words are clinical terms, not a name
        if all(w in self.CLINICAL_TERMS for w in words):
            return False
        # Check for common name patterns
        # Two capitalized words not in clinical terms = likely name
        if len(words) >= 2:
            non_clinical = [w for w in words if w not in self.CLINICAL_TERMS]
            if len(non_clinical) >= 2:
                return True
        return False

    # Street suffixes to skip in name detection
    STREET_SUFFIXES = {
        "street", "st", "avenue", "ave", "road", "rd", "boulevard", "blvd",
        "drive", "dr", "lane", "ln", "court", "ct", "way", "place", "pl",
    }

    def _detect_names(self, text: str) -> list[str]:
        """Detect potential personal names in text."""
        names_found = []
        # Pattern: Two consecutive capitalized words
        pattern = r"\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b"
        for match in re.finditer(pattern, text):
            full_match = match.group(0)
            first, second = match.group(1).lower(), match.group(2).lower()
            # Skip if both are clinical terms
            if first in self.CLINICAL_TERMS and second in self.CLINICAL_TERMS:
                continue
            # Skip street addresses (e.g., "Main Street")
            if second in self.STREET_SUFFIXES:
                continue
            # Skip common non-name patterns
            skip_patterns = ["New York", "Los Angeles", "San Francisco"]
            if full_match in skip_patterns:
                continue
            names_found.append(full_match)
        return names_found

    def anonymize(self, query: str) -> AnonymizationResult:
        """
        Anonymize a query by removing PHI.

        Args:
            query: The original query text

        Returns:
            AnonymizationResult with anonymized query and metadata

        Raises:
            AnonymizationError: If query cannot be safely anonymized
        """
        phi_types_found = []
        anonymized = query

        # Check for blocking patterns first
        for pattern in self.BLOCKING_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return AnonymizationResult(
                    original_query=query,
                    anonymized_query="",
                    phi_detected=True,
                    phi_types_found=["blocking_pattern"],
                    is_safe=False,
                    rejection_reason="Query contains explicit PHI disclosure patterns"
                )

        # Special handling for name detection
        detected_names = self._detect_names(query)
        if detected_names:
            phi_types_found.append("name")
            for name in detected_names:
                anonymized = anonymized.replace(name, "[PERSON]")

        # Apply other anonymization patterns
        for phi_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, anonymized, re.IGNORECASE)
                if matches:
                    # Filter out clinical terms (false positives)
                    real_matches = []
                    for match in matches:
                        if isinstance(match, tuple):
                            match = " ".join(match)
                        match_words = match.lower().split()
                        if not all(w in self.CLINICAL_TERMS for w in match_words):
                            real_matches.append(match)

                    if real_matches:
                        if phi_type not in phi_types_found:
                            phi_types_found.append(phi_type)
                        replacement = self.REPLACEMENTS.get(phi_type, "[REDACTED]")
                        anonymized = re.sub(pattern, replacement, anonymized, flags=re.IGNORECASE)

        # Remove duplicate PHI types
        phi_types_found = list(set(phi_types_found))

        # Determine if safe
        phi_detected = len(phi_types_found) > 0

        if self.strict_mode and phi_detected:
            return AnonymizationResult(
                original_query=query,
                anonymized_query=anonymized,
                phi_detected=True,
                phi_types_found=phi_types_found,
                is_safe=False,
                rejection_reason=f"PHI detected: {', '.join(phi_types_found)}"
            )

        return AnonymizationResult(
            original_query=query,
            anonymized_query=anonymized,
            phi_detected=phi_detected,
            phi_types_found=phi_types_found,
            is_safe=True
        )

    def is_safe(self, query: str) -> bool:
        """
        Quick check if a query is safe to send externally.

        Args:
            query: The query to check

        Returns:
            True if safe, False if PHI detected
        """
        result = self.anonymize(query)
        return result.is_safe

    def validate_and_anonymize(self, query: str) -> str:
        """
        Validate and return anonymized query, or raise if unsafe.

        Args:
            query: The query to anonymize

        Returns:
            Anonymized query string

        Raises:
            AnonymizationError: If query cannot be safely anonymized
        """
        result = self.anonymize(query)

        if not result.is_safe:
            raise AnonymizationError(
                f"Query rejected: {result.rejection_reason}"
            )

        return result.anonymized_query


class FrameworkQueryBuilder:
    """
    Builds anonymized research queries from Rung analysis output.

    Converts clinical frameworks and patterns into safe research queries.
    """

    # Query templates for different research types
    TEMPLATES = {
        "intervention": "evidence-based interventions for {framework} in therapy",
        "technique": "therapeutic techniques for addressing {pattern}",
        "research": "clinical research on {mechanism} in {context}",
        "couples": "couples therapy approaches for {dynamic} patterns",
        "attachment": "treatment approaches for {style} attachment in adults",
    }

    def __init__(self, anonymizer: Optional[QueryAnonymizer] = None):
        """Initialize with optional custom anonymizer."""
        self.anonymizer = anonymizer or QueryAnonymizer(strict_mode=True)

    def build_intervention_query(self, framework: str) -> str:
        """Build a query for evidence-based interventions."""
        # Framework names should be clinical terms, not PHI
        query = self.TEMPLATES["intervention"].format(framework=framework)
        return self.anonymizer.validate_and_anonymize(query)

    def build_technique_query(self, pattern: str) -> str:
        """Build a query for therapeutic techniques."""
        query = self.TEMPLATES["technique"].format(pattern=pattern)
        return self.anonymizer.validate_and_anonymize(query)

    def build_research_query(self, mechanism: str, context: str = "therapy") -> str:
        """Build a query for clinical research."""
        query = self.TEMPLATES["research"].format(
            mechanism=mechanism,
            context=context
        )
        return self.anonymizer.validate_and_anonymize(query)

    def build_couples_query(self, dynamic: str) -> str:
        """Build a query for couples therapy approaches."""
        query = self.TEMPLATES["couples"].format(dynamic=dynamic)
        return self.anonymizer.validate_and_anonymize(query)

    def build_attachment_query(self, style: str) -> str:
        """Build a query for attachment treatment."""
        query = self.TEMPLATES["attachment"].format(style=style)
        return self.anonymizer.validate_and_anonymize(query)

    def build_from_rung_output(self, rung_output: dict) -> list[str]:
        """
        Build multiple research queries from Rung analysis output.

        Args:
            rung_output: Dictionary from RungAnalysisOutput

        Returns:
            List of safe, anonymized research queries
        """
        queries = []

        # Build queries from frameworks
        for framework in rung_output.get("frameworks_identified", []):
            name = framework.get("name", "")
            if name:
                try:
                    query = self.build_intervention_query(name)
                    queries.append(query)
                except AnonymizationError:
                    continue  # Skip unsafe queries

        # Build queries from defense mechanisms
        for defense in rung_output.get("defense_mechanisms", []):
            mechanism = defense.get("type", "")
            if mechanism:
                try:
                    query = self.build_research_query(mechanism, "psychotherapy")
                    queries.append(query)
                except AnonymizationError:
                    continue

        return queries
