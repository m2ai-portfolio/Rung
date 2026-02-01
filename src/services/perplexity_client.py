"""
Perplexity API Client

Provides research capabilities via Perplexity's Sonar API.
All queries MUST be anonymized before reaching this client.

CRITICAL: This client should NEVER receive PHI directly.
Use the anonymizer layer before calling these methods.
"""

import os
import time
import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from functools import lru_cache

import requests
from requests.exceptions import RequestException


@dataclass
class Citation:
    """A citation from Perplexity research."""
    title: str
    source: str
    url: Optional[str] = None
    summary: Optional[str] = None


@dataclass
class PerplexityResponse:
    """Response from Perplexity API."""
    query: str
    answer: str
    citations: list[Citation] = field(default_factory=list)
    model: str = ""
    usage: dict = field(default_factory=dict)
    cached: bool = False


class PerplexityError(Exception):
    """Exception for Perplexity API errors."""
    pass


class RateLimitError(PerplexityError):
    """Exception when rate limit is exceeded."""
    pass


class ResponseCache:
    """Simple in-memory cache for non-PHI research queries."""

    def __init__(self, ttl_seconds: int = 3600):
        """
        Initialize cache.

        Args:
            ttl_seconds: Time-to-live for cached entries (default 1 hour)
        """
        self._cache: dict[str, tuple[PerplexityResponse, datetime]] = {}
        self.ttl = timedelta(seconds=ttl_seconds)

    def _make_key(self, query: str) -> str:
        """Create cache key from query."""
        return hashlib.sha256(query.lower().strip().encode()).hexdigest()

    def get(self, query: str) -> Optional[PerplexityResponse]:
        """Get cached response if valid."""
        key = self._make_key(query)
        if key in self._cache:
            response, timestamp = self._cache[key]
            if datetime.utcnow() - timestamp < self.ttl:
                # Mark as cached
                response.cached = True
                return response
            else:
                # Expired, remove
                del self._cache[key]
        return None

    def set(self, query: str, response: PerplexityResponse) -> None:
        """Cache a response."""
        key = self._make_key(query)
        self._cache[key] = (response, datetime.utcnow())

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    def size(self) -> int:
        """Return number of cached entries."""
        return len(self._cache)


class PerplexityClient:
    """
    Client for Perplexity Sonar API.

    Features:
    - Rate limiting with backoff
    - Response caching for non-PHI queries
    - Citation parsing
    - Error handling

    IMPORTANT: All queries must be pre-anonymized.
    """

    DEFAULT_MODEL = "sonar"
    API_URL = "https://api.perplexity.ai/chat/completions"

    # Rate limiting settings
    MAX_REQUESTS_PER_MINUTE = 20
    RATE_LIMIT_WINDOW = 60  # seconds

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        enable_cache: bool = True,
        cache_ttl: int = 3600,
    ):
        """
        Initialize Perplexity client.

        Args:
            api_key: Perplexity API key (or from PERPLEXITY_API_KEY env var)
            model: Model to use (default: sonar)
            enable_cache: Whether to cache responses
            cache_ttl: Cache TTL in seconds
        """
        self.api_key = api_key or os.environ.get("PERPLEXITY_API_KEY", "")
        self.model = model
        self.enable_cache = enable_cache
        self.cache = ResponseCache(ttl_seconds=cache_ttl) if enable_cache else None

        # Rate limiting state
        self._request_times: list[float] = []

    def _check_rate_limit(self) -> None:
        """Check and enforce rate limits."""
        now = time.time()
        window_start = now - self.RATE_LIMIT_WINDOW

        # Remove old request times
        self._request_times = [t for t in self._request_times if t > window_start]

        if len(self._request_times) >= self.MAX_REQUESTS_PER_MINUTE:
            wait_time = self._request_times[0] - window_start
            raise RateLimitError(
                f"Rate limit exceeded. Try again in {wait_time:.1f} seconds."
            )

        self._request_times.append(now)

    def search(
        self,
        query: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> PerplexityResponse:
        """
        Search using Perplexity Sonar API.

        Args:
            query: The search query (MUST be anonymized)
            system_prompt: Optional system prompt for context
            max_tokens: Maximum response tokens

        Returns:
            PerplexityResponse with answer and citations

        Raises:
            PerplexityError: If API call fails
            RateLimitError: If rate limit exceeded
        """
        # Check cache first
        if self.enable_cache and self.cache:
            cached = self.cache.get(query)
            if cached:
                return cached

        # Check rate limit
        self._check_rate_limit()

        # Build request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": query})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
        }

        try:
            response = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                timeout=30,
            )

            if response.status_code == 429:
                raise RateLimitError("Perplexity API rate limit exceeded")

            if response.status_code != 200:
                raise PerplexityError(
                    f"Perplexity API error: {response.status_code} - {response.text}"
                )

            data = response.json()
            result = self._parse_response(query, data)

            # Cache the result
            if self.enable_cache and self.cache:
                self.cache.set(query, result)

            return result

        except RequestException as e:
            raise PerplexityError(f"Request failed: {str(e)}") from e

    def _parse_response(self, query: str, data: dict) -> PerplexityResponse:
        """Parse Perplexity API response."""
        # Extract answer
        choices = data.get("choices", [])
        answer = ""
        if choices:
            message = choices[0].get("message", {})
            answer = message.get("content", "")

        # Extract citations if present
        citations = []
        # Perplexity may include citations in different formats
        if "citations" in data:
            for c in data["citations"]:
                citations.append(Citation(
                    title=c.get("title", ""),
                    source=c.get("source", c.get("url", "")),
                    url=c.get("url"),
                    summary=c.get("summary"),
                ))

        return PerplexityResponse(
            query=query,
            answer=answer,
            citations=citations,
            model=data.get("model", self.model),
            usage=data.get("usage", {}),
            cached=False,
        )

    def search_therapy_intervention(self, framework: str) -> PerplexityResponse:
        """
        Search for evidence-based therapy interventions.

        Args:
            framework: Clinical framework name (e.g., "avoidant attachment")

        Returns:
            PerplexityResponse with interventions
        """
        system_prompt = (
            "You are a clinical research assistant. Provide evidence-based "
            "therapeutic interventions with citations to peer-reviewed sources. "
            "Focus on practical techniques therapists can use."
        )
        query = f"evidence-based interventions for {framework} in therapy"
        return self.search(query, system_prompt=system_prompt)

    def search_defense_mechanism(self, mechanism: str) -> PerplexityResponse:
        """
        Search for research on defense mechanisms.

        Args:
            mechanism: Defense mechanism name (e.g., "intellectualization")

        Returns:
            PerplexityResponse with research findings
        """
        system_prompt = (
            "You are a clinical research assistant. Provide research findings "
            "on psychological defense mechanisms and therapeutic approaches. "
            "Include citations to academic sources."
        )
        query = f"clinical research on {mechanism} defense mechanism in psychotherapy"
        return self.search(query, system_prompt=system_prompt)

    def search_couples_therapy(self, pattern: str) -> PerplexityResponse:
        """
        Search for couples therapy approaches.

        Args:
            pattern: Relationship pattern (e.g., "pursuer-distancer")

        Returns:
            PerplexityResponse with couples therapy research
        """
        system_prompt = (
            "You are a clinical research assistant specializing in couples therapy. "
            "Provide evidence-based approaches from EFT, Gottman, and other modalities. "
            "Include practical techniques and research citations."
        )
        query = f"couples therapy approaches for {pattern} relationship dynamic"
        return self.search(query, system_prompt=system_prompt)
