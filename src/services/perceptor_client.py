"""
Perceptor Client Service

Provides context management for Rung sessions:
- Save session context for longitudinal tracking
- Load historical context for pattern analysis
- Search across sessions
- Tag-based organization

Tag Structure: [agent, stage, session-date, client-id]
Example: rung, post-session, 2024-01-15, client-abc123
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class PerceptorContext(BaseModel):
    """A saved context entry."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = Field(..., description="Context title")
    tags: list[str] = Field(default_factory=list, description="Context tags")
    projects: list[str] = Field(default_factory=list, description="Associated projects")
    summary: str = Field(..., description="Brief summary")
    content: str = Field(..., description="Full context content")
    source: str = Field(default="rung", description="Source identifier")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class PerceptorSearchResult(BaseModel):
    """Search result from Perceptor."""
    id: str
    title: str
    tags: list[str]
    summary: str
    relevance_score: float = Field(default=1.0)
    created_at: str


class PerceptorClientError(Exception):
    """Exception for Perceptor client errors."""
    pass


class PerceptorClient:
    """
    Client for Perceptor context management.

    Handles:
    - Saving session contexts
    - Loading historical contexts
    - Searching across sessions
    - Tag-based organization for longitudinal tracking
    """

    DEFAULT_PROJECT = "Rung"

    def __init__(
        self,
        base_path: Optional[str] = None,
        auto_sync: bool = True,
    ):
        """
        Initialize Perceptor client.

        Args:
            base_path: Base path for context storage (for local mode)
            auto_sync: Whether to auto-sync with remote (placeholder)
        """
        self.base_path = base_path or os.environ.get(
            "PERCEPTOR_BASE_PATH",
            "/tmp/perceptor"
        )
        self.auto_sync = auto_sync
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """Ensure storage directory exists."""
        os.makedirs(self.base_path, exist_ok=True)
        os.makedirs(os.path.join(self.base_path, "contexts"), exist_ok=True)

        # Initialize index if not exists
        index_path = os.path.join(self.base_path, "index.json")
        if not os.path.exists(index_path):
            with open(index_path, "w") as f:
                json.dump({"contexts": []}, f)

    def save_context(
        self,
        title: str,
        content: str,
        summary: str,
        tags: list[str],
        projects: Optional[list[str]] = None,
        client_id: Optional[str] = None,
        session_id: Optional[str] = None,
        agent: str = "rung",
        stage: str = "post-session",
    ) -> PerceptorContext:
        """
        Save a context to Perceptor.

        Args:
            title: Context title
            content: Full context content
            summary: Brief summary
            tags: Base tags for the context
            projects: Associated projects
            client_id: Client ID for tagging
            session_id: Session ID for tagging
            agent: Agent name (rung/beth)
            stage: Stage (pre-session/post-session)

        Returns:
            Saved PerceptorContext

        Raises:
            PerceptorClientError: If save fails
        """
        if not title or not title.strip():
            raise PerceptorClientError("Title cannot be empty")

        if not content or not content.strip():
            raise PerceptorClientError("Content cannot be empty")

        # Build comprehensive tags
        all_tags = list(tags)
        all_tags.append(agent)
        all_tags.append(stage)

        if client_id:
            all_tags.append(f"client:{client_id}")

        if session_id:
            all_tags.append(f"session:{session_id}")

        # Add date tag
        date_tag = datetime.utcnow().strftime("%Y-%m-%d")
        all_tags.append(f"date:{date_tag}")

        # Deduplicate tags
        all_tags = list(set(all_tags))

        # Create context
        context = PerceptorContext(
            title=title,
            tags=all_tags,
            projects=projects or [self.DEFAULT_PROJECT],
            summary=summary,
            content=content,
            source="rung",
        )

        try:
            # Save context file
            context_path = os.path.join(
                self.base_path,
                "contexts",
                f"{context.id}.json"
            )
            with open(context_path, "w") as f:
                json.dump(context.model_dump(), f, indent=2)

            # Update index
            self._update_index(context)

            return context

        except Exception as e:
            raise PerceptorClientError(f"Failed to save context: {str(e)}") from e

    def _update_index(self, context: PerceptorContext) -> None:
        """Update the context index."""
        index_path = os.path.join(self.base_path, "index.json")

        with open(index_path, "r") as f:
            index = json.load(f)

        # Add or update entry
        entry = {
            "id": context.id,
            "title": context.title,
            "tags": context.tags,
            "projects": context.projects,
            "summary": context.summary,
            "created_at": context.created_at,
        }

        # Remove existing entry if present
        index["contexts"] = [
            c for c in index["contexts"]
            if c["id"] != context.id
        ]

        # Add new entry
        index["contexts"].append(entry)

        with open(index_path, "w") as f:
            json.dump(index, f, indent=2)

    def load_context(self, context_id: str) -> PerceptorContext:
        """
        Load a specific context by ID.

        Args:
            context_id: Context ID to load

        Returns:
            PerceptorContext

        Raises:
            PerceptorClientError: If context not found
        """
        context_path = os.path.join(
            self.base_path,
            "contexts",
            f"{context_id}.json"
        )

        if not os.path.exists(context_path):
            raise PerceptorClientError(f"Context not found: {context_id}")

        try:
            with open(context_path, "r") as f:
                data = json.load(f)
            return PerceptorContext(**data)
        except Exception as e:
            raise PerceptorClientError(f"Failed to load context: {str(e)}") from e

    def list_contexts(
        self,
        tags: Optional[list[str]] = None,
        project: Optional[str] = None,
        client_id: Optional[str] = None,
        limit: int = 20,
        since: Optional[str] = None,
    ) -> list[PerceptorSearchResult]:
        """
        List contexts with optional filtering.

        Args:
            tags: Filter by tags (must match ALL)
            project: Filter by project
            client_id: Filter by client ID
            limit: Maximum results
            since: Only contexts from this date forward (YYYY-MM-DD)

        Returns:
            List of matching contexts
        """
        index_path = os.path.join(self.base_path, "index.json")

        with open(index_path, "r") as f:
            index = json.load(f)

        results = []

        for entry in index["contexts"]:
            # Filter by tags
            if tags:
                entry_tags = set(entry.get("tags", []))
                if not all(t in entry_tags for t in tags):
                    continue

            # Filter by project
            if project:
                if project not in entry.get("projects", []):
                    continue

            # Filter by client ID
            if client_id:
                client_tag = f"client:{client_id}"
                if client_tag not in entry.get("tags", []):
                    continue

            # Filter by date
            if since:
                entry_date = entry.get("created_at", "")[:10]
                if entry_date < since:
                    continue

            results.append(PerceptorSearchResult(
                id=entry["id"],
                title=entry["title"],
                tags=entry.get("tags", []),
                summary=entry.get("summary", ""),
                created_at=entry.get("created_at", ""),
            ))

        # Sort by created_at descending
        results.sort(key=lambda x: x.created_at, reverse=True)

        return results[:limit]

    def search_contexts(
        self,
        query: str,
        limit: int = 10,
    ) -> list[PerceptorSearchResult]:
        """
        Search contexts by text query.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching contexts with relevance scores
        """
        if not query or not query.strip():
            raise PerceptorClientError("Search query cannot be empty")

        query_lower = query.lower()
        results = []

        # Load all contexts and search
        contexts_dir = os.path.join(self.base_path, "contexts")

        for filename in os.listdir(contexts_dir):
            if not filename.endswith(".json"):
                continue

            try:
                with open(os.path.join(contexts_dir, filename), "r") as f:
                    context = json.load(f)

                # Calculate relevance score
                score = 0.0

                # Title match (highest weight)
                if query_lower in context.get("title", "").lower():
                    score += 3.0

                # Summary match
                if query_lower in context.get("summary", "").lower():
                    score += 2.0

                # Content match
                content = context.get("content", "").lower()
                if query_lower in content:
                    # Score based on frequency
                    count = content.count(query_lower)
                    score += min(count * 0.5, 2.0)  # Cap at 2.0

                # Tag match
                for tag in context.get("tags", []):
                    if query_lower in tag.lower():
                        score += 1.0

                if score > 0:
                    results.append(PerceptorSearchResult(
                        id=context["id"],
                        title=context["title"],
                        tags=context.get("tags", []),
                        summary=context.get("summary", ""),
                        relevance_score=score,
                        created_at=context.get("created_at", ""),
                    ))

            except Exception:
                continue  # Skip invalid files

        # Sort by relevance score descending
        results.sort(key=lambda x: x.relevance_score, reverse=True)

        return results[:limit]

    def get_client_history(
        self,
        client_id: str,
        agent: Optional[str] = None,
        limit: int = 10,
    ) -> list[PerceptorContext]:
        """
        Get full context history for a client.

        Args:
            client_id: Client ID
            agent: Optional agent filter (rung/beth)
            limit: Maximum contexts to return

        Returns:
            List of contexts with full content
        """
        tags = [f"client:{client_id}"]
        if agent:
            tags.append(agent)

        results = self.list_contexts(tags=tags, limit=limit)

        # Load full contexts
        contexts = []
        for result in results:
            try:
                context = self.load_context(result.id)
                contexts.append(context)
            except PerceptorClientError:
                continue

        return contexts

    def save_session_context(
        self,
        session_id: str,
        client_id: str,
        agent: str,
        stage: str,
        frameworks: list[str],
        insights: list[str],
        summary: str,
        additional_content: Optional[str] = None,
    ) -> PerceptorContext:
        """
        Convenience method to save session context with standard structure.

        Args:
            session_id: Session ID
            client_id: Client ID
            agent: Agent name (rung/beth)
            stage: Stage (pre-session/post-session)
            frameworks: Frameworks identified
            insights: Key insights
            summary: Session summary
            additional_content: Any additional content

        Returns:
            Saved context
        """
        # Build structured content
        content_parts = [
            f"## Session: {session_id}",
            f"## Agent: {agent}",
            f"## Stage: {stage}",
            "",
            "### Frameworks Identified",
            *[f"- {f}" for f in frameworks],
            "",
            "### Key Insights",
            *[f"- {i}" for i in insights],
            "",
            f"### Summary",
            summary,
        ]

        if additional_content:
            content_parts.extend(["", "### Additional Notes", additional_content])

        content = "\n".join(content_parts)

        # Build tags
        tags = ["session-context"]
        tags.extend([f.lower().replace(" ", "-") for f in frameworks[:5]])

        # Build title
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        title = f"{agent.capitalize()} {stage.replace('-', ' ').title()} - {date_str}"

        return self.save_context(
            title=title,
            content=content,
            summary=summary,
            tags=tags,
            client_id=client_id,
            session_id=session_id,
            agent=agent,
            stage=stage,
        )

    def get_longitudinal_patterns(
        self,
        client_id: str,
        framework: Optional[str] = None,
    ) -> dict:
        """
        Analyze longitudinal patterns for a client.

        Args:
            client_id: Client ID
            framework: Optional framework to focus on

        Returns:
            Dictionary with pattern analysis
        """
        contexts = self.get_client_history(client_id, limit=50)

        if not contexts:
            return {
                "client_id": client_id,
                "session_count": 0,
                "frameworks_over_time": [],
                "recurring_themes": [],
                "progress_indicators": [],
            }

        # Extract frameworks from all contexts
        all_frameworks = []
        all_themes = []

        for ctx in contexts:
            # Parse content for frameworks
            content = ctx.content.lower()

            for tag in ctx.tags:
                if tag not in ["rung", "beth", "pre-session", "post-session", "session-context"]:
                    if not tag.startswith("client:") and not tag.startswith("session:") and not tag.startswith("date:"):
                        all_themes.append(tag)

        # Count themes
        theme_counts = {}
        for theme in all_themes:
            theme_counts[theme] = theme_counts.get(theme, 0) + 1

        # Sort by frequency
        recurring = sorted(
            theme_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        return {
            "client_id": client_id,
            "session_count": len(contexts),
            "date_range": {
                "first": contexts[-1].created_at[:10] if contexts else None,
                "last": contexts[0].created_at[:10] if contexts else None,
            },
            "recurring_themes": [
                {"theme": theme, "occurrences": count}
                for theme, count in recurring
            ],
            "total_contexts": len(contexts),
        }
