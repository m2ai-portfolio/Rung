# Transcribe Module Variables

#------------------------------------------------------------------------------
# Required Variables
#------------------------------------------------------------------------------
variable "project_name" {
  description = "Name of the project (used in resource naming)"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "voice_memos_bucket_name" {
  description = "Name of the S3 bucket for voice memos"
  type        = string
}

variable "voice_memos_bucket_arn" {
  description = "ARN of the S3 bucket for voice memos"
  type        = string
}

variable "transcripts_bucket_name" {
  description = "Name of the S3 bucket for transcripts"
  type        = string
}

variable "transcripts_bucket_arn" {
  description = "ARN of the S3 bucket for transcripts"
  type        = string
}

variable "kms_key_arn" {
  description = "ARN of the KMS key for encryption"
  type        = string
}

#------------------------------------------------------------------------------
# Optional Variables
#------------------------------------------------------------------------------
variable "lambda_zip_path" {
  description = "Path to the Lambda deployment package (null to skip deployment)"
  type        = string
  default     = null
}

variable "vpc_config" {
  description = "VPC configuration for Lambda functions"
  type = object({
    subnet_ids         = list(string)
    security_group_ids = list(string)
  })
  default = null
}

variable "log_retention_days" {
  description = "Number of days to retain CloudWatch logs"
  type        = number
  default     = 30
}

variable "create_api_gateway" {
  description = "Whether to create API Gateway resources"
  type        = bool
  default     = true
}

variable "cors_allowed_origins" {
  description = "List of allowed origins for CORS"
  type        = list(string)
  default     = ["*"]
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}
