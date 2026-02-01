"""
Transcription Status Lambda Handler

Checks the status of an AWS Transcribe Medical job.
"""

import json
import os
from typing import Any
from uuid import UUID

import boto3
from botocore.exceptions import ClientError


# Lazy-loaded client
_transcribe_client = None


def get_transcribe_client():
    """Get or create Transcribe client."""
    global _transcribe_client
    if _transcribe_client is None:
        _transcribe_client = boto3.client("transcribe", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    return _transcribe_client


# For testing - allow injection
transcribe_client = None


def _get_transcribe():
    """Get Transcribe client - uses injected mock or creates real client."""
    return transcribe_client if transcribe_client is not None else get_transcribe_client()


def handler(event: dict, context: Any) -> dict:
    """Lambda handler for transcription status check.

    Expects API Gateway v2 (HTTP API) event format.

    Args:
        event: API Gateway event with:
            - pathParameters.session_id: UUID of the session
            - queryStringParameters.job_name: Name of the transcription job
        context: Lambda context object.

    Returns:
        API Gateway response with job status.
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
        job_name = query_params.get("job_name")

        if not job_name:
            return error_response(400, "Missing job_name in query parameters")

        # Get job status from AWS Transcribe
        try:
            response = _get_transcribe().get_medical_transcription_job(
                MedicalTranscriptionJobName=job_name
            )
            job = response["MedicalTranscriptionJob"]

            # Extract job info
            status = job["TranscriptionJobStatus"]
            completed_at = None
            failure_reason = None

            if status == "COMPLETED":
                completed_at = job.get("CompletionTime")
                if completed_at:
                    completed_at = completed_at.isoformat()
            elif status == "FAILED":
                failure_reason = job.get("FailureReason")

            # Extract job_id from output key
            output_key = job.get("Transcript", {}).get("TranscriptFileUri", "")
            job_id = output_key.split("/")[-1].replace(".json", "") if output_key else ""

            return success_response(200, {
                "session_id": session_id,
                "job_id": job_id,
                "job_name": job_name,
                "status": status,
                "completed_at": completed_at,
                "failure_reason": failure_reason
            })

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "BadRequestException":
                return error_response(404, f"Transcription job not found: {job_name}")
            return error_response(500, f"Failed to get job status: {str(e)}")

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
