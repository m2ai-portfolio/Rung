"""
Notes Processor Service

Handles processing of therapist session notes:
1. Encryption before storage
2. Framework extraction
3. Workflow triggering
4. Audit logging
"""

import os
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.services.framework_extractor import (
    FrameworkExtractor,
    FrameworkExtractionOutput,
    FrameworkExtractorError,
)


class NotesInput(BaseModel):
    """Input for notes processing."""
    session_id: str = Field(..., description="UUID of the session")
    notes: str = Field(..., description="Session notes text")
    therapist_id: str = Field(..., description="UUID of the therapist")
    encrypt: bool = Field(default=True, description="Whether to encrypt before storage")


class NotesProcessingResult(BaseModel):
    """Result of notes processing."""
    session_id: str
    processing_id: str
    status: str = Field(..., description="pending|processing|completed|failed")
    encrypted: bool = False
    extraction_complete: bool = False
    extraction: Optional[FrameworkExtractionOutput] = None
    error_message: Optional[str] = None
    processed_at: Optional[str] = None


class NotesProcessorError(Exception):
    """Exception for notes processing errors."""
    pass


class NotesProcessor:
    """
    Processes therapist session notes.

    Handles:
    1. Input validation
    2. Encryption (using KMS)
    3. Framework extraction
    4. Storage preparation
    5. Audit logging
    """

    def __init__(
        self,
        framework_extractor: Optional[FrameworkExtractor] = None,
        kms_key_id: Optional[str] = None,
    ):
        """
        Initialize notes processor.

        Args:
            framework_extractor: Optional pre-configured extractor
            kms_key_id: KMS key ID for encryption
        """
        self.extractor = framework_extractor or FrameworkExtractor()
        self.kms_key_id = kms_key_id or os.environ.get("FIELD_ENCRYPTION_KEY_ID")

    def process(self, input_data: NotesInput) -> NotesProcessingResult:
        """
        Process session notes.

        Args:
            input_data: Notes input with session info

        Returns:
            NotesProcessingResult with extraction and status

        Raises:
            NotesProcessorError: If processing fails
        """
        processing_id = str(uuid4())

        try:
            # Validate input
            self._validate_input(input_data)

            # Extract frameworks
            extraction = self.extractor.extract(input_data.notes)

            # Prepare result
            result = NotesProcessingResult(
                session_id=input_data.session_id,
                processing_id=processing_id,
                status="completed",
                encrypted=input_data.encrypt,
                extraction_complete=True,
                extraction=extraction,
                processed_at=datetime.utcnow().isoformat(),
            )

            return result

        except FrameworkExtractorError as e:
            return NotesProcessingResult(
                session_id=input_data.session_id,
                processing_id=processing_id,
                status="failed",
                encrypted=False,
                extraction_complete=False,
                error_message=str(e),
            )

        except Exception as e:
            raise NotesProcessorError(f"Processing failed: {str(e)}") from e

    def _validate_input(self, input_data: NotesInput) -> None:
        """Validate input data."""
        if not input_data.notes or not input_data.notes.strip():
            raise NotesProcessorError("Notes cannot be empty")

        if len(input_data.notes) > 100000:  # 100KB limit
            raise NotesProcessorError("Notes exceed maximum length")

        # Validate UUIDs
        try:
            UUID(input_data.session_id)
            UUID(input_data.therapist_id)
        except ValueError as e:
            raise NotesProcessorError(f"Invalid UUID: {str(e)}")

    def encrypt_notes(self, notes: str) -> bytes:
        """
        Encrypt notes using KMS.

        Args:
            notes: Plain text notes

        Returns:
            Encrypted bytes

        Note: This is a placeholder. Real implementation would use
        AWS KMS or field-level encryption.
        """
        # Placeholder for encryption
        # In production: Use KMS client to encrypt
        return notes.encode("utf-8")

    def decrypt_notes(self, encrypted: bytes) -> str:
        """
        Decrypt notes using KMS.

        Args:
            encrypted: Encrypted bytes

        Returns:
            Plain text notes

        Note: This is a placeholder. Real implementation would use
        AWS KMS or field-level encryption.
        """
        # Placeholder for decryption
        return encrypted.decode("utf-8")

    def prepare_for_storage(
        self,
        input_data: NotesInput,
        extraction: FrameworkExtractionOutput,
    ) -> dict:
        """
        Prepare data for database storage.

        Args:
            input_data: Original input
            extraction: Extraction results

        Returns:
            Dictionary ready for database insertion
        """
        encrypted_notes = self.encrypt_notes(input_data.notes) if input_data.encrypt else input_data.notes.encode()

        return {
            "session_id": input_data.session_id,
            "notes_encrypted": encrypted_notes,
            "frameworks_discussed": extraction.frameworks_discussed,
            "modalities_used": extraction.modalities_used,
            "homework_assigned": [hw.model_dump() for hw in extraction.homework_assigned],
            "breakthroughs": extraction.breakthroughs,
            "progress_indicators": extraction.progress_indicators,
            "areas_for_next_session": extraction.areas_for_next_session,
            "created_at": datetime.utcnow().isoformat(),
        }

    def create_audit_entry(
        self,
        input_data: NotesInput,
        result: NotesProcessingResult,
        user_id: str,
        ip_address: str = "unknown",
    ) -> dict:
        """
        Create audit log entry for notes processing.

        Args:
            input_data: Original input
            result: Processing result
            user_id: ID of user who submitted notes
            ip_address: IP address of request

        Returns:
            Audit entry dictionary
        """
        return {
            "id": str(uuid4()),
            "event_type": "notes_processed",
            "user_id": user_id,
            "resource_type": "session_notes",
            "resource_id": input_data.session_id,
            "action": "create",
            "ip_address": ip_address,
            "details": {
                "processing_id": result.processing_id,
                "status": result.status,
                "encrypted": result.encrypted,
                "notes_length": len(input_data.notes),
                "frameworks_count": len(result.extraction.frameworks_discussed) if result.extraction else 0,
            },
            "created_at": datetime.utcnow().isoformat(),
        }
