# Transcribe Module Outputs

#------------------------------------------------------------------------------
# Lambda Functions
#------------------------------------------------------------------------------
output "voice_upload_function_arn" {
  description = "ARN of the voice upload Lambda function"
  value       = aws_lambda_function.voice_upload.arn
}

output "voice_upload_function_name" {
  description = "Name of the voice upload Lambda function"
  value       = aws_lambda_function.voice_upload.function_name
}

output "transcription_status_function_arn" {
  description = "ARN of the transcription status Lambda function"
  value       = aws_lambda_function.transcription_status.arn
}

output "transcription_status_function_name" {
  description = "Name of the transcription status Lambda function"
  value       = aws_lambda_function.transcription_status.function_name
}

output "transcript_retrieval_function_arn" {
  description = "ARN of the transcript retrieval Lambda function"
  value       = aws_lambda_function.transcript_retrieval.arn
}

output "transcript_retrieval_function_name" {
  description = "Name of the transcript retrieval Lambda function"
  value       = aws_lambda_function.transcript_retrieval.function_name
}

#------------------------------------------------------------------------------
# IAM Role
#------------------------------------------------------------------------------
output "lambda_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_voice_processing.arn
}

output "lambda_role_name" {
  description = "Name of the Lambda execution role"
  value       = aws_iam_role.lambda_voice_processing.name
}

#------------------------------------------------------------------------------
# API Gateway
#------------------------------------------------------------------------------
output "api_gateway_id" {
  description = "ID of the API Gateway"
  value       = var.create_api_gateway ? aws_apigatewayv2_api.voice_api[0].id : null
}

output "api_gateway_endpoint" {
  description = "Endpoint URL of the API Gateway"
  value       = var.create_api_gateway ? aws_apigatewayv2_api.voice_api[0].api_endpoint : null
}

output "api_gateway_stage_url" {
  description = "Full URL of the API Gateway stage"
  value       = var.create_api_gateway ? "${aws_apigatewayv2_api.voice_api[0].api_endpoint}/${var.environment}" : null
}

#------------------------------------------------------------------------------
# CloudWatch Log Groups
#------------------------------------------------------------------------------
output "log_groups" {
  description = "CloudWatch log group names"
  value = {
    voice_upload         = aws_cloudwatch_log_group.voice_upload.name
    transcription_status = aws_cloudwatch_log_group.transcription_status.name
    transcript_retrieval = aws_cloudwatch_log_group.transcript_retrieval.name
  }
}

#------------------------------------------------------------------------------
# API Endpoints
#------------------------------------------------------------------------------
output "api_endpoints" {
  description = "API endpoint paths"
  value = var.create_api_gateway ? {
    voice_upload         = "POST /sessions/{session_id}/voice-memo"
    transcription_status = "GET /sessions/{session_id}/transcription/status"
    transcript_retrieval = "GET /sessions/{session_id}/transcript"
  } : null
}
