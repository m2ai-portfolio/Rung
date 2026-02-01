"""
Transcription Service - AWS Transcribe Medical Integration

Handles voice memo transcription with medical vocabulary and speaker diarization.
"""

import json
import os
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

import boto3
from botocore.exceptions import ClientError
from pydantic import BaseModel, Field


class TranscriptionStatus(str, Enum):
    """Status of a transcription job."""
    QUEUED = "QUEUED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TranscriptionJobInfo(BaseModel):
    """Information about a transcription job."""
    job_id: str
    job_name: str
    status: TranscriptionStatus
    session_id: UUID
    input_s3_uri: str
    output_s3_uri: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    language_code: str = "en-US"
    media_format: str = "mp3"


class TranscriptionResult(BaseModel):
    """Result of a completed transcription."""
    job_id: str
    session_id: UUID
    transcript: str
    speaker_labels: Optional[list[dict]] = None
    confidence: Optional[float] = None


class TranscriptionService:
    """Service for managing AWS Transcribe Medical jobs."""

    def __init__(
        self,
        region: str | None = None,
        voice_memos_bucket: str | None = None,
        transcripts_bucket: str | None = None
    ):
        """Initialize the transcription service.

        Args:
            region: AWS region. Defaults to AWS_REGION env var.
            voice_memos_bucket: S3 bucket for voice memos. Defaults to env var.
            transcripts_bucket: S3 bucket for transcripts. Defaults to env var.
        """
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self.voice_memos_bucket = voice_memos_bucket or os.getenv("VOICE_MEMOS_BUCKET")
        self.transcripts_bucket = transcripts_bucket or os.getenv("TRANSCRIPTS_BUCKET")

        self.transcribe_client = boto3.client("transcribe", region_name=self.region)
        self.s3_client = boto3.client("s3", region_name=self.region)

    def start_transcription_job(
        self,
        session_id: UUID,
        s3_key: str,
        media_format: str = "mp3",
        language_code: str = "en-US",
        enable_speaker_diarization: bool = True,
        max_speakers: int = 2
    ) -> TranscriptionJobInfo:
        """Start an AWS Transcribe Medical job.

        Args:
            session_id: ID of the therapy session.
            s3_key: S3 key of the voice memo file.
            media_format: Audio format (mp3, wav, flac, etc.).
            language_code: Language code (default: en-US).
            enable_speaker_diarization: Enable speaker identification.
            max_speakers: Maximum number of speakers to identify.

        Returns:
            TranscriptionJobInfo with job details.

        Raises:
            ClientError: If AWS API call fails.
        """
        job_id = str(uuid4())
        job_name = f"rung-{session_id}-{job_id[:8]}"
        input_s3_uri = f"s3://{self.voice_memos_bucket}/{s3_key}"
        output_s3_uri = f"s3://{self.transcripts_bucket}/{session_id}/"

        # Configure the transcription job
        job_config = {
            "TranscriptionJobName": job_name,
            "LanguageCode": language_code,
            "MediaFormat": media_format,
            "Media": {
                "MediaFileUri": input_s3_uri
            },
            "OutputBucketName": self.transcripts_bucket,
            "OutputKey": f"{session_id}/{job_id}.json",
            "Settings": {
                "ShowSpeakerLabels": enable_speaker_diarization,
                "MaxSpeakerLabels": max_speakers,
                "ChannelIdentification": False,
                "ShowAlternatives": False
            },
            # Use medical specialty for therapy sessions
            "ContentRedaction": {
                "RedactionType": "PII",
                "RedactionOutput": "redacted"
            }
        }

        # Start the job
        try:
            response = self.transcribe_client.start_transcription_job(**job_config)
            job = response["TranscriptionJob"]

            return TranscriptionJobInfo(
                job_id=job_id,
                job_name=job_name,
                status=TranscriptionStatus(job["TranscriptionJobStatus"]),
                session_id=session_id,
                input_s3_uri=input_s3_uri,
                output_s3_uri=f"{output_s3_uri}{job_id}.json",
                created_at=datetime.utcnow(),
                language_code=language_code,
                media_format=media_format
            )
        except ClientError as e:
            raise TranscriptionError(f"Failed to start transcription job: {e}")

    def start_medical_transcription_job(
        self,
        session_id: UUID,
        s3_key: str,
        media_format: str = "mp3",
        language_code: str = "en-US",
        specialty: str = "PRIMARYCARE",
        job_type: str = "CONVERSATION"
    ) -> TranscriptionJobInfo:
        """Start an AWS Transcribe Medical job with medical vocabulary.

        Args:
            session_id: ID of the therapy session.
            s3_key: S3 key of the voice memo file.
            media_format: Audio format.
            language_code: Language code.
            specialty: Medical specialty (PRIMARYCARE or CARDIOLOGY).
            job_type: Type of audio (CONVERSATION or DICTATION).

        Returns:
            TranscriptionJobInfo with job details.
        """
        job_id = str(uuid4())
        job_name = f"rung-medical-{session_id}-{job_id[:8]}"
        input_s3_uri = f"s3://{self.voice_memos_bucket}/{s3_key}"

        job_config = {
            "MedicalTranscriptionJobName": job_name,
            "LanguageCode": language_code,
            "MediaFormat": media_format,
            "Media": {
                "MediaFileUri": input_s3_uri
            },
            "OutputBucketName": self.transcripts_bucket,
            "OutputKey": f"{session_id}/{job_id}.json",
            "Specialty": specialty,
            "Type": job_type,
            "Settings": {
                "ShowSpeakerLabels": True,
                "MaxSpeakerLabels": 2,
                "ChannelIdentification": False
            }
        }

        try:
            response = self.transcribe_client.start_medical_transcription_job(**job_config)
            job = response["MedicalTranscriptionJob"]

            return TranscriptionJobInfo(
                job_id=job_id,
                job_name=job_name,
                status=TranscriptionStatus(job["TranscriptionJobStatus"]),
                session_id=session_id,
                input_s3_uri=input_s3_uri,
                output_s3_uri=f"s3://{self.transcripts_bucket}/{session_id}/{job_id}.json",
                created_at=datetime.utcnow(),
                language_code=language_code,
                media_format=media_format
            )
        except ClientError as e:
            raise TranscriptionError(f"Failed to start medical transcription job: {e}")

    def get_job_status(self, job_name: str, is_medical: bool = False) -> TranscriptionJobInfo:
        """Get the status of a transcription job.

        Args:
            job_name: Name of the transcription job.
            is_medical: Whether this is a medical transcription job.

        Returns:
            TranscriptionJobInfo with current status.
        """
        try:
            if is_medical:
                response = self.transcribe_client.get_medical_transcription_job(
                    MedicalTranscriptionJobName=job_name
                )
                job = response["MedicalTranscriptionJob"]
                status_key = "TranscriptionJobStatus"
            else:
                response = self.transcribe_client.get_transcription_job(
                    TranscriptionJobName=job_name
                )
                job = response["TranscriptionJob"]
                status_key = "TranscriptionJobStatus"

            # Extract session_id from job name (format: rung-{session_id}-{short_id})
            parts = job_name.split("-")
            session_id = "-".join(parts[1:-1]) if len(parts) > 2 else parts[1]

            info = TranscriptionJobInfo(
                job_id=parts[-1] if len(parts) > 2 else job_name,
                job_name=job_name,
                status=TranscriptionStatus(job[status_key]),
                session_id=UUID(session_id) if self._is_valid_uuid(session_id) else UUID(int=0),
                input_s3_uri=job["Media"]["MediaFileUri"],
                output_s3_uri=job.get("Transcript", {}).get("TranscriptFileUri"),
                created_at=job.get("CreationTime", datetime.utcnow()),
                completed_at=job.get("CompletionTime"),
                failure_reason=job.get("FailureReason"),
                language_code=job.get("LanguageCode", "en-US"),
                media_format=job.get("MediaFormat", "mp3")
            )

            return info

        except ClientError as e:
            raise TranscriptionError(f"Failed to get job status: {e}")

    def get_transcript(self, session_id: UUID, job_id: str) -> TranscriptionResult:
        """Get the transcript content from S3.

        Args:
            session_id: ID of the therapy session.
            job_id: ID of the transcription job.

        Returns:
            TranscriptionResult with transcript content.
        """
        s3_key = f"{session_id}/{job_id}.json"

        try:
            response = self.s3_client.get_object(
                Bucket=self.transcripts_bucket,
                Key=s3_key
            )
            content = json.loads(response["Body"].read().decode("utf-8"))

            # Extract transcript from AWS Transcribe format
            results = content.get("results", {})
            transcripts = results.get("transcripts", [])
            transcript_text = transcripts[0].get("transcript", "") if transcripts else ""

            # Extract speaker labels if available
            speaker_labels = None
            if "speaker_labels" in results:
                speaker_labels = results["speaker_labels"].get("segments", [])

            # Calculate average confidence
            items = results.get("items", [])
            confidences = [
                float(item.get("alternatives", [{}])[0].get("confidence", 0))
                for item in items
                if item.get("type") == "pronunciation"
            ]
            avg_confidence = sum(confidences) / len(confidences) if confidences else None

            return TranscriptionResult(
                job_id=job_id,
                session_id=session_id,
                transcript=transcript_text,
                speaker_labels=speaker_labels,
                confidence=avg_confidence
            )

        except ClientError as e:
            raise TranscriptionError(f"Failed to get transcript: {e}")

    def delete_job(self, job_name: str, is_medical: bool = False) -> bool:
        """Delete a transcription job.

        Args:
            job_name: Name of the job to delete.
            is_medical: Whether this is a medical transcription job.

        Returns:
            True if deletion was successful.
        """
        try:
            if is_medical:
                self.transcribe_client.delete_medical_transcription_job(
                    MedicalTranscriptionJobName=job_name
                )
            else:
                self.transcribe_client.delete_transcription_job(
                    TranscriptionJobName=job_name
                )
            return True
        except ClientError as e:
            raise TranscriptionError(f"Failed to delete job: {e}")

    @staticmethod
    def _is_valid_uuid(val: str) -> bool:
        """Check if a string is a valid UUID."""
        try:
            UUID(val)
            return True
        except (ValueError, AttributeError):
            return False


class TranscriptionError(Exception):
    """Custom exception for transcription errors."""
    pass
