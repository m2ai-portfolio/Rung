# Rung Transcribe Module - Voice Processing Infrastructure
# Creates Lambda functions and IAM roles for voice memo processing

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = merge(var.tags, {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    HIPAA       = "true"
  })
}

# Get current AWS account ID and region
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

#------------------------------------------------------------------------------
# IAM Role for Lambda Functions
#------------------------------------------------------------------------------
resource "aws_iam_role" "lambda_voice_processing" {
  name = "${local.name_prefix}-lambda-voice-processing"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

#------------------------------------------------------------------------------
# IAM Policy for Voice Processing
#------------------------------------------------------------------------------
resource "aws_iam_role_policy" "lambda_voice_processing" {
  name = "${local.name_prefix}-lambda-voice-processing-policy"
  role = aws_iam_role.lambda_voice_processing.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # CloudWatch Logs
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:*"
      },
      # S3 Access for voice memos and transcripts
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${var.voice_memos_bucket_arn}/*",
          "${var.transcripts_bucket_arn}/*"
        ]
      },
      # S3 List buckets
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = [
          var.voice_memos_bucket_arn,
          var.transcripts_bucket_arn
        ]
      },
      # AWS Transcribe
      {
        Effect = "Allow"
        Action = [
          "transcribe:StartTranscriptionJob",
          "transcribe:StartMedicalTranscriptionJob",
          "transcribe:GetTranscriptionJob",
          "transcribe:GetMedicalTranscriptionJob",
          "transcribe:DeleteTranscriptionJob",
          "transcribe:DeleteMedicalTranscriptionJob",
          "transcribe:ListTranscriptionJobs",
          "transcribe:ListMedicalTranscriptionJobs"
        ]
        Resource = "*"
      },
      # KMS for encryption/decryption
      {
        Effect = "Allow"
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = var.kms_key_arn
      },
      # VPC networking (if Lambda is in VPC)
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface",
          "ec2:AssignPrivateIpAddresses",
          "ec2:UnassignPrivateIpAddresses"
        ]
        Resource = "*"
      }
    ]
  })
}

#------------------------------------------------------------------------------
# Lambda Function: Voice Upload
#------------------------------------------------------------------------------
resource "aws_lambda_function" "voice_upload" {
  function_name = "${local.name_prefix}-voice-upload"
  description   = "Handles voice memo uploads and triggers transcription"

  filename         = var.lambda_zip_path != null ? var.lambda_zip_path : null
  source_code_hash = var.lambda_zip_path != null ? filebase64sha256(var.lambda_zip_path) : null

  # Use placeholder if no zip provided
  package_type = var.lambda_zip_path != null ? "Zip" : null

  runtime = "python3.12"
  handler = "src.lambdas.voice_upload.handler"
  timeout = 30
  memory_size = 256

  role = aws_iam_role.lambda_voice_processing.arn

  environment {
    variables = {
      VOICE_MEMOS_BUCKET = var.voice_memos_bucket_name
      TRANSCRIPTS_BUCKET = var.transcripts_bucket_name
      AWS_REGION_NAME    = data.aws_region.current.id
    }
  }

  # VPC configuration for HIPAA compliance
  dynamic "vpc_config" {
    for_each = var.vpc_config != null ? [var.vpc_config] : []
    content {
      subnet_ids         = vpc_config.value.subnet_ids
      security_group_ids = vpc_config.value.security_group_ids
    }
  }

  tags = merge(local.common_tags, {
    Name     = "${local.name_prefix}-voice-upload"
    Function = "voice-upload"
  })

  # Ignore changes to code when deploying infrastructure only
  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }
}

#------------------------------------------------------------------------------
# Lambda Function: Transcription Status
#------------------------------------------------------------------------------
resource "aws_lambda_function" "transcription_status" {
  function_name = "${local.name_prefix}-transcription-status"
  description   = "Checks transcription job status"

  filename         = var.lambda_zip_path != null ? var.lambda_zip_path : null
  source_code_hash = var.lambda_zip_path != null ? filebase64sha256(var.lambda_zip_path) : null

  runtime = "python3.12"
  handler = "src.lambdas.transcription_status.handler"
  timeout = 10
  memory_size = 128

  role = aws_iam_role.lambda_voice_processing.arn

  environment {
    variables = {
      AWS_REGION_NAME = data.aws_region.current.id
    }
  }

  dynamic "vpc_config" {
    for_each = var.vpc_config != null ? [var.vpc_config] : []
    content {
      subnet_ids         = vpc_config.value.subnet_ids
      security_group_ids = vpc_config.value.security_group_ids
    }
  }

  tags = merge(local.common_tags, {
    Name     = "${local.name_prefix}-transcription-status"
    Function = "transcription-status"
  })

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }
}

#------------------------------------------------------------------------------
# Lambda Function: Transcript Retrieval
#------------------------------------------------------------------------------
resource "aws_lambda_function" "transcript_retrieval" {
  function_name = "${local.name_prefix}-transcript-retrieval"
  description   = "Retrieves completed transcripts with audit logging"

  filename         = var.lambda_zip_path != null ? var.lambda_zip_path : null
  source_code_hash = var.lambda_zip_path != null ? filebase64sha256(var.lambda_zip_path) : null

  runtime = "python3.12"
  handler = "src.lambdas.transcript_retrieval.handler"
  timeout = 15
  memory_size = 256

  role = aws_iam_role.lambda_voice_processing.arn

  environment {
    variables = {
      TRANSCRIPTS_BUCKET = var.transcripts_bucket_name
      AWS_REGION_NAME    = data.aws_region.current.id
    }
  }

  dynamic "vpc_config" {
    for_each = var.vpc_config != null ? [var.vpc_config] : []
    content {
      subnet_ids         = vpc_config.value.subnet_ids
      security_group_ids = vpc_config.value.security_group_ids
    }
  }

  tags = merge(local.common_tags, {
    Name     = "${local.name_prefix}-transcript-retrieval"
    Function = "transcript-retrieval"
  })

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }
}

#------------------------------------------------------------------------------
# CloudWatch Log Groups
#------------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "voice_upload" {
  name              = "/aws/lambda/${aws_lambda_function.voice_upload.function_name}"
  retention_in_days = var.log_retention_days

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "transcription_status" {
  name              = "/aws/lambda/${aws_lambda_function.transcription_status.function_name}"
  retention_in_days = var.log_retention_days

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "transcript_retrieval" {
  name              = "/aws/lambda/${aws_lambda_function.transcript_retrieval.function_name}"
  retention_in_days = var.log_retention_days

  tags = local.common_tags
}

#------------------------------------------------------------------------------
# API Gateway Integration (HTTP API)
#------------------------------------------------------------------------------
resource "aws_apigatewayv2_api" "voice_api" {
  count = var.create_api_gateway ? 1 : 0

  name          = "${local.name_prefix}-voice-api"
  protocol_type = "HTTP"
  description   = "Voice memo processing API"

  cors_configuration {
    allow_origins = var.cors_allowed_origins
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["Content-Type", "X-User-ID", "Authorization"]
    max_age       = 300
  }

  tags = local.common_tags
}

resource "aws_apigatewayv2_stage" "voice_api" {
  count = var.create_api_gateway ? 1 : 0

  api_id      = aws_apigatewayv2_api.voice_api[0].id
  name        = var.environment
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway[0].arn
    format = jsonencode({
      requestId        = "$context.requestId"
      ip               = "$context.identity.sourceIp"
      requestTime      = "$context.requestTime"
      httpMethod       = "$context.httpMethod"
      routeKey         = "$context.routeKey"
      status           = "$context.status"
      responseLength   = "$context.responseLength"
      integrationError = "$context.integrationErrorMessage"
    })
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "api_gateway" {
  count = var.create_api_gateway ? 1 : 0

  name              = "/aws/apigateway/${local.name_prefix}-voice-api"
  retention_in_days = var.log_retention_days

  tags = local.common_tags
}

#------------------------------------------------------------------------------
# API Gateway Routes and Integrations
#------------------------------------------------------------------------------

# Voice Upload Route
resource "aws_apigatewayv2_integration" "voice_upload" {
  count = var.create_api_gateway ? 1 : 0

  api_id                 = aws_apigatewayv2_api.voice_api[0].id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.voice_upload.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "voice_upload" {
  count = var.create_api_gateway ? 1 : 0

  api_id    = aws_apigatewayv2_api.voice_api[0].id
  route_key = "POST /sessions/{session_id}/voice-memo"
  target    = "integrations/${aws_apigatewayv2_integration.voice_upload[0].id}"
}

resource "aws_lambda_permission" "voice_upload_api" {
  count = var.create_api_gateway ? 1 : 0

  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.voice_upload.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.voice_api[0].execution_arn}/*/*"
}

# Transcription Status Route
resource "aws_apigatewayv2_integration" "transcription_status" {
  count = var.create_api_gateway ? 1 : 0

  api_id                 = aws_apigatewayv2_api.voice_api[0].id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.transcription_status.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "transcription_status" {
  count = var.create_api_gateway ? 1 : 0

  api_id    = aws_apigatewayv2_api.voice_api[0].id
  route_key = "GET /sessions/{session_id}/transcription/status"
  target    = "integrations/${aws_apigatewayv2_integration.transcription_status[0].id}"
}

resource "aws_lambda_permission" "transcription_status_api" {
  count = var.create_api_gateway ? 1 : 0

  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.transcription_status.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.voice_api[0].execution_arn}/*/*"
}

# Transcript Retrieval Route
resource "aws_apigatewayv2_integration" "transcript_retrieval" {
  count = var.create_api_gateway ? 1 : 0

  api_id                 = aws_apigatewayv2_api.voice_api[0].id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.transcript_retrieval.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "transcript_retrieval" {
  count = var.create_api_gateway ? 1 : 0

  api_id    = aws_apigatewayv2_api.voice_api[0].id
  route_key = "GET /sessions/{session_id}/transcript"
  target    = "integrations/${aws_apigatewayv2_integration.transcript_retrieval[0].id}"
}

resource "aws_lambda_permission" "transcript_retrieval_api" {
  count = var.create_api_gateway ? 1 : 0

  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.transcript_retrieval.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.voice_api[0].execution_arn}/*/*"
}
