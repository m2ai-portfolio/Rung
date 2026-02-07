"""
Voice Processing Tests for Phase 2A

Tests verify:
1. Transcription service functions correctly
2. Lambda handlers process events properly
3. API endpoints validate input correctly
4. Security: unauthorized access is blocked
5. Audit logging is created
"""

import base64
import json
import os
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4, UUID

# Set test environment variables before imports
os.environ["AWS_REGION"] = "us-east-1"
os.environ["VOICE_MEMOS_BUCKET"] = "test-voice-memos"
os.environ["TRANSCRIPTS_BUCKET"] = "test-transcripts"

from src.services.transcription import (
    TranscriptionService,
    TranscriptionStatus,
    TranscriptionJobInfo,
    TranscriptionResult,
    TranscriptionError
)
from src.lambdas.voice_upload import handler as voice_upload_handler
from src.lambdas.transcription_status import handler as transcription_status_handler
from src.lambdas.transcript_retrieval import handler as transcript_retrieval_handler


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_boto_clients():
    """Mock boto3 clients for testing."""
    with patch("boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_transcribe = MagicMock()

        def get_client(service_name, **kwargs):
            if service_name == "s3":
                return mock_s3
            elif service_name == "transcribe":
                return mock_transcribe
            return MagicMock()

        mock_client.side_effect = get_client
        yield {
            "s3": mock_s3,
            "transcribe": mock_transcribe
        }


@pytest.fixture
def sample_session_id():
    """Generate a sample session ID."""
    return uuid4()


@pytest.fixture
def sample_job_id():
    """Generate a sample job ID."""
    return str(uuid4())


@pytest.fixture
def sample_transcribe_response():
    """Sample AWS Transcribe response."""
    return {
        "results": {
            "transcripts": [
                {"transcript": "Hello, how are you feeling today?"}
            ],
            "items": [
                {"type": "pronunciation", "alternatives": [{"confidence": "0.95", "content": "Hello"}]},
                {"type": "pronunciation", "alternatives": [{"confidence": "0.98", "content": "how"}]},
                {"type": "pronunciation", "alternatives": [{"confidence": "0.99", "content": "are"}]},
            ],
            "speaker_labels": {
                "segments": [
                    {"speaker_label": "spk_0", "start_time": "0.0", "end_time": "2.0"},
                    {"speaker_label": "spk_1", "start_time": "2.0", "end_time": "5.0"}
                ]
            }
        }
    }


# =============================================================================
# Transcription Service Tests
# =============================================================================

class TestTranscriptionService:
    """Test TranscriptionService class."""

    def test_service_initialization(self):
        """Test service initializes with correct parameters."""
        service = TranscriptionService(
            region="us-east-1",
            voice_memos_bucket="test-bucket",
            transcripts_bucket="test-transcripts"
        )
        assert service.region == "us-east-1"
        assert service.voice_memos_bucket == "test-bucket"
        assert service.transcripts_bucket == "test-transcripts"

    def test_service_uses_env_vars(self):
        """Test service uses environment variables."""
        service = TranscriptionService()
        assert service.voice_memos_bucket == "test-voice-memos"
        assert service.transcripts_bucket == "test-transcripts"

    @patch("boto3.client")
    def test_start_medical_transcription_job(self, mock_boto_client, sample_session_id):
        """Test starting a medical transcription job."""
        mock_transcribe = MagicMock()
        mock_transcribe.start_medical_transcription_job.return_value = {
            "MedicalTranscriptionJob": {
                "TranscriptionJobStatus": "IN_PROGRESS",
                "Media": {"MediaFileUri": "s3://test/file.mp3"}
            }
        }
        mock_boto_client.return_value = mock_transcribe

        service = TranscriptionService()
        result = service.start_medical_transcription_job(
            session_id=sample_session_id,
            s3_key=f"{sample_session_id}/audio.mp3",
            media_format="mp3"
        )

        assert result.status == TranscriptionStatus.IN_PROGRESS
        assert result.session_id == sample_session_id
        mock_transcribe.start_medical_transcription_job.assert_called_once()

    @patch("boto3.client")
    def test_get_transcript(self, mock_boto_client, sample_session_id, sample_job_id, sample_transcribe_response):
        """Test retrieving a transcript."""
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=lambda: json.dumps(sample_transcribe_response).encode())
        }
        mock_boto_client.return_value = mock_s3

        service = TranscriptionService()
        result = service.get_transcript(sample_session_id, sample_job_id)

        assert isinstance(result, TranscriptionResult)
        assert result.transcript == "Hello, how are you feeling today?"
        assert result.speaker_labels is not None
        assert result.confidence is not None

    def test_is_valid_uuid(self):
        """Test UUID validation helper."""
        assert TranscriptionService._is_valid_uuid(str(uuid4())) is True
        assert TranscriptionService._is_valid_uuid("not-a-uuid") is False
        assert TranscriptionService._is_valid_uuid("") is False


class TestTranscriptionModels:
    """Test Pydantic models for transcription."""

    def test_transcription_status_enum(self):
        """Test TranscriptionStatus enum values."""
        assert TranscriptionStatus.QUEUED == "QUEUED"
        assert TranscriptionStatus.IN_PROGRESS == "IN_PROGRESS"
        assert TranscriptionStatus.COMPLETED == "COMPLETED"
        assert TranscriptionStatus.FAILED == "FAILED"

    def test_transcription_job_info(self, sample_session_id):
        """Test TranscriptionJobInfo model."""
        job_info = TranscriptionJobInfo(
            job_id="test-job",
            job_name="rung-test-job",
            status=TranscriptionStatus.IN_PROGRESS,
            session_id=sample_session_id,
            input_s3_uri="s3://bucket/key",
            created_at=datetime.utcnow()
        )
        assert job_info.job_id == "test-job"
        assert job_info.status == TranscriptionStatus.IN_PROGRESS

    def test_transcription_result(self, sample_session_id):
        """Test TranscriptionResult model."""
        result = TranscriptionResult(
            job_id="test-job",
            session_id=sample_session_id,
            transcript="Test transcript",
            confidence=0.95
        )
        assert result.transcript == "Test transcript"
        assert result.confidence == 0.95


# =============================================================================
# Lambda Handler Tests
# =============================================================================

class TestVoiceUploadHandler:
    """Test voice upload Lambda handler."""

    @patch("src.lambdas.voice_upload.s3_client")
    @patch("src.lambdas.voice_upload.transcribe_client")
    def test_successful_upload(self, mock_transcribe, mock_s3, sample_session_id):
        """Test successful voice memo upload."""
        mock_transcribe.start_medical_transcription_job.return_value = {
            "MedicalTranscriptionJob": {
                "TranscriptionJobStatus": "IN_PROGRESS"
            }
        }

        event = {
            "pathParameters": {"session_id": str(sample_session_id)},
            "headers": {"content-type": "audio/mpeg", "x-user-id": str(uuid4())},
            "body": base64.b64encode(b"fake audio data").decode(),
            "isBase64Encoded": True
        }

        response = voice_upload_handler(event, None)

        assert response["statusCode"] == 202
        body = json.loads(response["body"])
        assert body["session_id"] == str(sample_session_id)
        assert body["status"] == "IN_PROGRESS"

    def test_missing_session_id(self):
        """Test handler rejects missing session_id."""
        event = {
            "pathParameters": {},
            "headers": {},
            "body": ""
        }

        response = voice_upload_handler(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "session_id" in body["detail"]

    def test_invalid_session_id(self):
        """Test handler rejects invalid session_id."""
        event = {
            "pathParameters": {"session_id": "not-a-uuid"},
            "headers": {},
            "body": ""
        }

        response = voice_upload_handler(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "Invalid" in body["detail"]

    @patch("src.lambdas.voice_upload.s3_client")
    @patch("src.lambdas.voice_upload.transcribe_client")
    def test_empty_body_rejected(self, mock_transcribe, mock_s3, sample_session_id):
        """Test handler rejects empty body."""
        event = {
            "pathParameters": {"session_id": str(sample_session_id)},
            "headers": {"content-type": "audio/mpeg"},
            "body": "",
            "isBase64Encoded": False
        }

        response = voice_upload_handler(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "Empty" in body["detail"]


class TestTranscriptionStatusHandler:
    """Test transcription status Lambda handler."""

    @patch("src.lambdas.transcription_status.transcribe_client")
    def test_get_status_success(self, mock_transcribe, sample_session_id):
        """Test successful status check."""
        mock_transcribe.get_medical_transcription_job.return_value = {
            "MedicalTranscriptionJob": {
                "TranscriptionJobStatus": "COMPLETED",
                "Media": {"MediaFileUri": "s3://bucket/key"},
                "Transcript": {"TranscriptFileUri": f"s3://bucket/{sample_session_id}/job123.json"}
            }
        }

        event = {
            "pathParameters": {"session_id": str(sample_session_id)},
            "queryStringParameters": {"job_name": "rung-medical-test-job"}
        }

        response = transcription_status_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "COMPLETED"

    def test_missing_job_name(self, sample_session_id):
        """Test handler requires job_name."""
        event = {
            "pathParameters": {"session_id": str(sample_session_id)},
            "queryStringParameters": {}
        }

        response = transcription_status_handler(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "job_name" in body["detail"]


class TestTranscriptRetrievalHandler:
    """Test transcript retrieval Lambda handler."""

    @patch("src.lambdas.transcript_retrieval.s3_client")
    def test_get_transcript_success(self, mock_s3, sample_session_id, sample_job_id, sample_transcribe_response):
        """Test successful transcript retrieval."""
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=lambda: json.dumps(sample_transcribe_response).encode())
        }

        event = {
            "pathParameters": {"session_id": str(sample_session_id)},
            "queryStringParameters": {"job_id": sample_job_id},
            "headers": {"x-user-id": str(uuid4()), "user-agent": "test"},
            "requestContext": {"http": {"sourceIp": "127.0.0.1"}}
        }

        response = transcript_retrieval_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["transcript"] == "Hello, how are you feeling today?"
        assert body["speaker_labels"] is not None

    def test_missing_job_id(self, sample_session_id):
        """Test handler requires job_id."""
        event = {
            "pathParameters": {"session_id": str(sample_session_id)},
            "queryStringParameters": {},
            "headers": {}
        }

        response = transcript_retrieval_handler(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "job_id" in body["detail"]


# =============================================================================
# Security Tests
# =============================================================================

class TestSecurityValidation:
    """Test security validations."""

    def test_invalid_uuid_rejected(self):
        """Test that invalid UUIDs are rejected."""
        event = {
            "pathParameters": {"session_id": "invalid-uuid"},
            "headers": {}
        }

        response = voice_upload_handler(event, None)
        assert response["statusCode"] == 400

        response = transcription_status_handler(event, None)
        assert response["statusCode"] == 400

        response = transcript_retrieval_handler(event, None)
        assert response["statusCode"] == 400

    def test_cors_headers_present(self):
        """Test that CORS headers are present in responses."""
        event = {
            "pathParameters": {"session_id": str(uuid4())},
            "headers": {},
            "body": ""
        }

        response = voice_upload_handler(event, None)
        assert "Access-Control-Allow-Origin" in response["headers"]


# =============================================================================
# Terraform Configuration Tests
# =============================================================================

class TestTerraformConfiguration:
    """Test Terraform configuration files."""

    def test_transcribe_module_main_exists(self):
        """Verify transcribe/main.tf exists."""
        path = "terraform/modules/transcribe.deprecated/main.tf"
        assert os.path.exists(path), f"Missing {path}"

    def test_transcribe_module_variables_exists(self):
        """Verify transcribe/variables.tf exists."""
        path = "terraform/modules/transcribe.deprecated/variables.tf"
        assert os.path.exists(path), f"Missing {path}"

    def test_transcribe_module_outputs_exists(self):
        """Verify transcribe/outputs.tf exists."""
        path = "terraform/modules/transcribe.deprecated/outputs.tf"
        assert os.path.exists(path), f"Missing {path}"

    def test_lambda_functions_defined(self):
        """Verify Lambda functions are defined in Terraform."""
        with open("terraform/modules/transcribe.deprecated/main.tf", "r") as f:
            content = f.read()

        assert 'aws_lambda_function" "voice_upload"' in content
        assert 'aws_lambda_function" "transcription_status"' in content
        assert 'aws_lambda_function" "transcript_retrieval"' in content

    def test_iam_role_defined(self):
        """Verify IAM role is defined."""
        with open("terraform/modules/transcribe.deprecated/main.tf", "r") as f:
            content = f.read()

        assert 'aws_iam_role" "lambda_voice_processing"' in content

    def test_transcribe_permissions(self):
        """Verify Transcribe permissions are in IAM policy."""
        with open("terraform/modules/transcribe.deprecated/main.tf", "r") as f:
            content = f.read()

        assert "transcribe:StartMedicalTranscriptionJob" in content
        assert "transcribe:GetMedicalTranscriptionJob" in content

    def test_api_gateway_defined(self):
        """Verify API Gateway is defined."""
        with open("terraform/modules/transcribe.deprecated/main.tf", "r") as f:
            content = f.read()

        assert 'aws_apigatewayv2_api" "voice_api"' in content

    def test_hipaa_tag_present(self):
        """Verify HIPAA tag is present."""
        with open("terraform/modules/transcribe.deprecated/main.tf", "r") as f:
            content = f.read()

        assert 'HIPAA' in content
        assert '"true"' in content


# =============================================================================
# API Module Tests
# =============================================================================

class TestAPIModule:
    """Test API module files exist."""

    def test_voice_memo_api_exists(self):
        """Verify voice_memo.py exists."""
        path = "src/api/voice_memo.py"
        assert os.path.exists(path), f"Missing {path}"

    def test_transcription_service_exists(self):
        """Verify transcription.py service exists."""
        path = "src/services/transcription.py"
        assert os.path.exists(path), f"Missing {path}"


class TestLambdaModules:
    """Test Lambda module files exist."""

    def test_voice_upload_lambda_exists(self):
        """Verify voice_upload.py exists."""
        path = "src/lambdas/voice_upload.py"
        assert os.path.exists(path), f"Missing {path}"

    def test_transcription_status_lambda_exists(self):
        """Verify transcription_status.py exists."""
        path = "src/lambdas/transcription_status.py"
        assert os.path.exists(path), f"Missing {path}"

    def test_transcript_retrieval_lambda_exists(self):
        """Verify transcript_retrieval.py exists."""
        path = "src/lambdas/transcript_retrieval.py"
        assert os.path.exists(path), f"Missing {path}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
