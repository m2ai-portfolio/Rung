"""
Voice Upload Lambda Handler

DEPRECATED: This Lambda handler has been superseded by the FastAPI + ECS stack.
Voice upload functionality is now handled by src/api/voice_memo.py running on ECS.
This file is retained because tests/voice/test_voice_processing.py imports from it.
Remove this file once those tests are migrated to test the FastAPI endpoints instead.
See: src/api/voice_memo.py for the replacement implementation.

Original description:
Handles voice memo uploads via API Gateway/Lambda integration.
Validates input, uploads to S3, and triggers transcription.
"""

import json
import os
import base64
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import boto3
from botocore.exceptions import ClientError


# Lazy-loaded clients (initialized on first use)
_s3_client = None
_transcribe_client = None


def get_s3_client():
    """Get or create S3 client."""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    return _s3_client


def get_transcribe_client():
    """Get or create Transcribe client."""
    global _transcribe_client
    if _transcribe_client is None:
        _transcribe_client = boto3.client("transcribe", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    return _transcribe_client


# Environment variables (loaded at runtime)
VOICE_MEMOS_BUCKET = os.environ.get("VOICE_MEMOS_BUCKET", "")
TRANSCRIPTS_BUCKET = os.environ.get("TRANSCRIPTS_BUCKET", "")

# For testing - allow injection of mock clients
s3_client = None
transcribe_client = None


def _get_s3():
    """Get S3 client - uses injected mock or creates real client."""
    return s3_client if s3_client is not None else get_s3_client()


def _get_transcribe():
    """Get Transcribe client - uses injected mock or creates real client."""
    return transcribe_client if transcribe_client is not None else get_transcribe_client()


def handler(event: dict, context: Any) -> dict:
    """Lambda handler for voice memo upload.

    Expects API Gateway v2 (HTTP API) event format.

    Args:
        event: API Gateway event with:
            - pathParameters.session_id: UUID of the session
            - body: Base64 encoded audio file
            - headers: Content-Type, X-User-ID
        context: Lambda context object.

    Returns:
        API Gateway response with job_id and status.
    """
    try:
        # Parse path parameters
        path_params = event.get("pathParameters", {})
        session_id = path_params.get("session_id")

        if not session_id:
            return error_response(400, "Missing session_id in path")

        try:
            session_uuid = UUID(session_id)
        except ValueError:
            return error_response(400, "Invalid session_id format")

        # Parse headers
        headers = event.get("headers", {})
        content_type = headers.get("content-type", "audio/mpeg")
        user_id = headers.get("x-user-id", "unknown")

        # Determine file format from content type
        format_map = {
            "audio/mpeg": ("mp3", "mp3"),
            "audio/mp3": ("mp3", "mp3"),
            "audio/wav": ("wav", "wav"),
            "audio/x-wav": ("wav", "wav"),
            "audio/mp4": ("m4a", "mp4"),
            "audio/x-m4a": ("m4a", "mp4"),
            "audio/flac": ("flac", "flac"),
            "audio/ogg": ("ogg", "ogg"),
            "audio/webm": ("webm", "webm"),
        }

        file_ext, media_format = format_map.get(content_type.lower(), ("mp3", "mp3"))

        # Get and decode body
        body = event.get("body", "")
        is_base64 = event.get("isBase64Encoded", False)

        if is_base64:
            file_content = base64.b64decode(body)
        else:
            file_content = body.encode() if isinstance(body, str) else body

        if not file_content:
            return error_response(400, "Empty file content")

        # Validate file size (100MB max)
        max_size = 100 * 1024 * 1024
        if len(file_content) > max_size:
            return error_response(400, f"File too large. Maximum size is {max_size // (1024*1024)}MB")

        # Generate S3 key
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        s3_key = f"{session_id}/{timestamp}.{file_ext}"

        # Upload to S3
        try:
            _get_s3().put_object(
                Bucket=VOICE_MEMOS_BUCKET,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                Metadata={
                    "session_id": session_id,
                    "uploaded_by": user_id,
                    "upload_timestamp": timestamp
                }
            )
        except ClientError as e:
            return error_response(500, f"Failed to upload to S3: {str(e)}")

        # Start transcription job
        job_id = str(uuid4())
        job_name = f"rung-medical-{session_id[:8]}-{job_id[:8]}"

        try:
            _get_transcribe().start_medical_transcription_job(
                MedicalTranscriptionJobName=job_name,
                LanguageCode="en-US",
                MediaFormat=media_format,
                Media={
                    "MediaFileUri": f"s3://{VOICE_MEMOS_BUCKET}/{s3_key}"
                },
                OutputBucketName=TRANSCRIPTS_BUCKET,
                OutputKey=f"{session_id}/{job_id}.json",
                Specialty="PRIMARYCARE",
                Type="CONVERSATION",
                Settings={
                    "ShowSpeakerLabels": True,
                    "MaxSpeakerLabels": 2,
                    "ChannelIdentification": False
                }
            )
        except ClientError as e:
            return error_response(500, f"Failed to start transcription: {str(e)}")

        # Return success response
        return success_response(202, {
            "session_id": session_id,
            "job_id": job_id,
            "job_name": job_name,
            "status": "IN_PROGRESS",
            "message": "Voice memo uploaded and transcription started"
        })

    except Exception as e:
        return error_response(500, f"Internal error: {str(e)}")


def success_response(status_code: int, body: dict) -> dict:
    """Create a successful API Gateway response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body)
    }


def error_response(status_code: int, message: str) -> dict:
    """Create an error API Gateway response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps({"detail": message})
    }
