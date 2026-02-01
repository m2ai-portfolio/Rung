"""
Transcript Retrieval Lambda Handler

Retrieves completed transcript from S3 with audit logging.
"""

import json
import os
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import boto3
from botocore.exceptions import ClientError


# Lazy-loaded client
_s3_client = None


def get_s3_client():
    """Get or create S3 client."""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    return _s3_client


# Environment variables (loaded at runtime)
TRANSCRIPTS_BUCKET = os.environ.get("TRANSCRIPTS_BUCKET", "")

# For testing - allow injection
s3_client = None


def _get_s3():
    """Get S3 client - uses injected mock or creates real client."""
    return s3_client if s3_client is not None else get_s3_client()


def handler(event: dict, context: Any) -> dict:
    """Lambda handler for transcript retrieval.

    Expects API Gateway v2 (HTTP API) event format.

    Args:
        event: API Gateway event with:
            - pathParameters.session_id: UUID of the session
            - queryStringParameters.job_id: ID of the transcription job
            - headers.X-User-ID: ID of requesting user
        context: Lambda context object.

    Returns:
        API Gateway response with transcript content.
    """
    try:
        # Parse path parameters
        path_params = event.get("pathParameters", {})
        session_id = path_params.get("session_id")

        if not session_id:
            return error_response(400, "Missing session_id in path")

        try:
            UUID(session_id)
        except ValueError:
            return error_response(400, "Invalid session_id format")

        # Parse query parameters
        query_params = event.get("queryStringParameters", {}) or {}
        job_id = query_params.get("job_id")

        if not job_id:
            return error_response(400, "Missing job_id in query parameters")

        # Parse headers for audit
        headers = event.get("headers", {})
        user_id = headers.get("x-user-id", "unknown")
        user_agent = headers.get("user-agent", "unknown")

        # Get client IP from request context
        request_context = event.get("requestContext", {})
        http_context = request_context.get("http", {})
        ip_address = http_context.get("sourceIp", "unknown")

        # Retrieve transcript from S3
        s3_key = f"{session_id}/{job_id}.json"

        try:
            response = _get_s3().get_object(
                Bucket=TRANSCRIPTS_BUCKET,
                Key=s3_key
            )
            content = json.loads(response["Body"].read().decode("utf-8"))

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey":
                return error_response(404, f"Transcript not found for job_id: {job_id}")
            return error_response(500, f"Failed to retrieve transcript: {str(e)}")

        # Parse AWS Transcribe output format
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

        # Create audit log entry (would be stored in database)
        audit_entry = {
            "id": str(uuid4()),
            "event_type": "phi_access",
            "user_id": user_id,
            "resource_type": "transcript",
            "resource_id": session_id,
            "action": "read",
            "ip_address": ip_address,
            "user_agent": user_agent,
            "details": {
                "job_id": job_id,
                "transcript_length": len(transcript_text)
            },
            "created_at": datetime.utcnow().isoformat()
        }

        # TODO: Store audit entry in database
        # For now, log it
        print(f"AUDIT: {json.dumps(audit_entry)}")

        return success_response(200, {
            "session_id": session_id,
            "job_id": job_id,
            "transcript": transcript_text,
            "speaker_labels": speaker_labels,
            "confidence": avg_confidence
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
