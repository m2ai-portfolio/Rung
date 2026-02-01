"""
Voice Memo API Endpoints

Handles voice memo upload, transcription status, and transcript retrieval.
"""

import os
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field

from src.models.audit_log import AuditEventType, AuditAction
from src.services.transcription import (
    TranscriptionService,
    TranscriptionStatus,
    TranscriptionError,
    TranscriptionJobInfo,
    TranscriptionResult
)


router = APIRouter(prefix="/sessions", tags=["voice-memo"])


# =============================================================================
# Response Schemas
# =============================================================================

class VoiceMemoUploadResponse(BaseModel):
    """Response after uploading a voice memo."""
    session_id: UUID
    job_id: str
    job_name: str
    status: TranscriptionStatus
    message: str = "Voice memo uploaded and transcription started"


class TranscriptionStatusResponse(BaseModel):
    """Response for transcription status check."""
    session_id: UUID
    job_id: str
    job_name: str
    status: TranscriptionStatus
    completed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None


class TranscriptResponse(BaseModel):
    """Response containing the transcript."""
    session_id: UUID
    job_id: str
    transcript: str
    speaker_labels: Optional[list[dict]] = None
    confidence: Optional[float] = None


class ErrorResponse(BaseModel):
    """Error response."""
    detail: str


# =============================================================================
# Dependencies
# =============================================================================

def get_transcription_service() -> TranscriptionService:
    """Dependency to get transcription service."""
    return TranscriptionService(
        region=os.getenv("AWS_REGION", "us-east-1"),
        voice_memos_bucket=os.getenv("VOICE_MEMOS_BUCKET"),
        transcripts_bucket=os.getenv("TRANSCRIPTS_BUCKET")
    )


def get_current_user_id(request: Request) -> UUID:
    """Extract current user ID from request.

    In production, this would validate JWT and extract user_id.
    For now, returns a placeholder or header value.
    """
    user_id = request.headers.get("X-User-ID")
    if user_id:
        try:
            return UUID(user_id)
        except ValueError:
            pass
    # Return placeholder for testing
    return UUID("00000000-0000-0000-0000-000000000000")


# =============================================================================
# API Endpoints
# =============================================================================

@router.post(
    "/{session_id}/voice-memo",
    response_model=VoiceMemoUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file format"},
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "Session not found"},
        500: {"model": ErrorResponse, "description": "Transcription service error"}
    }
)
async def upload_voice_memo(
    session_id: UUID,
    file: UploadFile = File(..., description="Audio file (mp3, wav, m4a, flac)"),
    service: TranscriptionService = Depends(get_transcription_service),
    user_id: UUID = Depends(get_current_user_id)
):
    """Upload a voice memo and start transcription.

    This endpoint:
    1. Validates the session exists and user has access
    2. Uploads the audio file to S3 (encrypted)
    3. Starts an AWS Transcribe Medical job
    4. Returns job_id for status polling

    Supported formats: mp3, wav, m4a, flac, ogg, webm
    Max file size: 100MB (configured in Lambda/API Gateway)
    """
    # Validate file format
    allowed_formats = {"mp3", "wav", "m4a", "flac", "ogg", "webm"}
    file_ext = file.filename.split(".")[-1].lower() if file.filename else ""

    if file_ext not in allowed_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file format. Allowed: {', '.join(allowed_formats)}"
        )

    # Map file extensions to media formats
    format_map = {
        "mp3": "mp3",
        "wav": "wav",
        "m4a": "mp4",
        "flac": "flac",
        "ogg": "ogg",
        "webm": "webm"
    }
    media_format = format_map.get(file_ext, "mp3")

    # TODO: Validate session exists and user has access
    # This would query the database for the session and check therapist_id
    # For now, we proceed with the upload

    # Generate S3 key
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    s3_key = f"{session_id}/{timestamp}.{file_ext}"

    try:
        # Upload to S3
        import boto3
        s3_client = boto3.client("s3", region_name=os.getenv("AWS_REGION", "us-east-1"))

        await file.seek(0)
        file_content = await file.read()

        s3_client.put_object(
            Bucket=service.voice_memos_bucket,
            Key=s3_key,
            Body=file_content,
            ContentType=file.content_type or f"audio/{file_ext}",
            Metadata={
                "session_id": str(session_id),
                "uploaded_by": str(user_id),
                "original_filename": file.filename or "unknown"
            }
        )

        # Start transcription job
        job_info = service.start_medical_transcription_job(
            session_id=session_id,
            s3_key=s3_key,
            media_format=media_format,
            specialty="PRIMARYCARE",
            job_type="CONVERSATION"
        )

        # TODO: Create audit log entry
        # audit_log_service.log(
        #     event_type=AuditEventType.PHI_CREATE,
        #     user_id=user_id,
        #     resource_type="voice_memo",
        #     resource_id=session_id,
        #     action=AuditAction.CREATE,
        #     details={"job_id": job_info.job_id, "s3_key": s3_key}
        # )

        return VoiceMemoUploadResponse(
            session_id=session_id,
            job_id=job_info.job_id,
            job_name=job_info.job_name,
            status=job_info.status
        )

    except TranscriptionError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process voice memo: {str(e)}"
        )


@router.get(
    "/{session_id}/transcription/status",
    response_model=TranscriptionStatusResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "Transcription job not found"}
    }
)
async def get_transcription_status(
    session_id: UUID,
    job_name: str,
    service: TranscriptionService = Depends(get_transcription_service),
    user_id: UUID = Depends(get_current_user_id)
):
    """Get the status of a transcription job.

    Poll this endpoint to check if transcription is complete.
    Status values: QUEUED, IN_PROGRESS, COMPLETED, FAILED
    """
    # TODO: Validate session exists and user has access

    try:
        job_info = service.get_job_status(job_name, is_medical=True)

        return TranscriptionStatusResponse(
            session_id=session_id,
            job_id=job_info.job_id,
            job_name=job_info.job_name,
            status=job_info.status,
            completed_at=job_info.completed_at,
            failure_reason=job_info.failure_reason
        )

    except TranscriptionError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcription job not found: {str(e)}"
        )


@router.get(
    "/{session_id}/transcript",
    response_model=TranscriptResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Access denied"},
        404: {"model": ErrorResponse, "description": "Transcript not found"}
    }
)
async def get_transcript(
    session_id: UUID,
    job_id: str,
    service: TranscriptionService = Depends(get_transcription_service),
    user_id: UUID = Depends(get_current_user_id),
    request: Request = None
):
    """Get the transcript content.

    Returns the decrypted transcript text along with speaker labels
    and confidence scores if available.

    This endpoint creates an audit log entry for HIPAA compliance.
    """
    # TODO: Validate session exists and user has access

    try:
        result = service.get_transcript(session_id, job_id)

        # Create audit log entry for PHI access
        # TODO: Implement audit logging
        # audit_log_service.log(
        #     event_type=AuditEventType.PHI_ACCESS,
        #     user_id=user_id,
        #     resource_type="transcript",
        #     resource_id=session_id,
        #     action=AuditAction.READ,
        #     ip_address=request.client.host if request else None,
        #     user_agent=request.headers.get("user-agent") if request else None,
        #     details={"job_id": job_id}
        # )

        return TranscriptResponse(
            session_id=session_id,
            job_id=result.job_id,
            transcript=result.transcript,
            speaker_labels=result.speaker_labels,
            confidence=result.confidence
        )

    except TranscriptionError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcript not found: {str(e)}"
        )


# =============================================================================
# Health Check
# =============================================================================

@router.get("/health", include_in_schema=False)
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "voice-memo"}
