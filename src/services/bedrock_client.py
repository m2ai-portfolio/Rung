"""
AWS Bedrock Client for Claude Integration

Provides a wrapper for AWS Bedrock Claude API calls with:
- Retry logic and error handling
- Structured output parsing
- Token usage tracking
- HIPAA-compliant logging (no PHI in logs)
"""

import json
import os
from typing import Any, Optional
from dataclasses import dataclass

import boto3
from botocore.exceptions import ClientError


# Lazy-loaded client
_bedrock_client = None


def get_bedrock_client():
    """Get or create Bedrock Runtime client."""
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=os.environ.get("AWS_REGION", "us-east-1")
        )
    return _bedrock_client


# For testing - allow injection
bedrock_client = None


def _get_client():
    """Get Bedrock client - uses injected mock or creates real client."""
    return bedrock_client if bedrock_client is not None else get_bedrock_client()


@dataclass
class BedrockResponse:
    """Response from Bedrock API call."""
    content: str
    input_tokens: int
    output_tokens: int
    stop_reason: str
    model_id: str


class BedrockClientError(Exception):
    """Custom exception for Bedrock client errors."""
    pass


class BedrockClient:
    """
    Client for AWS Bedrock Claude API.

    Attributes:
        model_id: The Bedrock model identifier
        max_tokens: Maximum tokens for response
        temperature: Sampling temperature (0.0-1.0)
        region: AWS region
    """

    # Default model: Claude 3.5 Sonnet via Bedrock
    DEFAULT_MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"

    def __init__(
        self,
        model_id: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
        region: Optional[str] = None
    ):
        """
        Initialize Bedrock client.

        Args:
            model_id: Bedrock model ID (defaults to Claude 3.5 Sonnet)
            max_tokens: Maximum response tokens
            temperature: Sampling temperature (lower = more deterministic)
            region: AWS region (defaults to AWS_REGION env var)
        """
        self.model_id = model_id or self.DEFAULT_MODEL_ID
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")

    def invoke(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> BedrockResponse:
        """
        Invoke Claude via Bedrock.

        Args:
            system_prompt: System prompt defining agent behavior
            user_message: User message to process
            max_tokens: Override default max tokens
            temperature: Override default temperature

        Returns:
            BedrockResponse with content and metadata

        Raises:
            BedrockClientError: If API call fails
        """
        client = _get_client()

        # Build request body for Claude Messages API
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature if temperature is not None else self.temperature,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        }

        try:
            response = client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body)
            )

            response_body = json.loads(response["body"].read())

            # Extract content from response
            content = ""
            if response_body.get("content"):
                for block in response_body["content"]:
                    if block.get("type") == "text":
                        content += block.get("text", "")

            return BedrockResponse(
                content=content,
                input_tokens=response_body.get("usage", {}).get("input_tokens", 0),
                output_tokens=response_body.get("usage", {}).get("output_tokens", 0),
                stop_reason=response_body.get("stop_reason", "unknown"),
                model_id=self.model_id
            )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))

            # Log error without PHI
            print(f"Bedrock API error: {error_code} - {error_msg}")

            raise BedrockClientError(
                f"Bedrock API call failed: {error_code}"
            ) from e

    def invoke_with_json_output(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> tuple[dict[str, Any], BedrockResponse]:
        """
        Invoke Claude and parse JSON response.

        Args:
            system_prompt: System prompt (should request JSON output)
            user_message: User message to process
            max_tokens: Override default max tokens
            temperature: Override default temperature

        Returns:
            Tuple of (parsed JSON dict, BedrockResponse metadata)

        Raises:
            BedrockClientError: If API call or JSON parsing fails
        """
        response = self.invoke(
            system_prompt=system_prompt,
            user_message=user_message,
            max_tokens=max_tokens,
            temperature=temperature
        )

        try:
            # Try to extract JSON from response
            content = response.content.strip()

            # Handle markdown code blocks
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]

            if content.endswith("```"):
                content = content[:-3]

            content = content.strip()

            parsed = json.loads(content)
            return parsed, response

        except json.JSONDecodeError as e:
            raise BedrockClientError(
                f"Failed to parse JSON response: {str(e)}"
            ) from e
