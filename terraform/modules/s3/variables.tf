# S3 Module Variables

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

variable "s3_kms_key_arn" {
  description = "ARN of the KMS key for S3 encryption"
  type        = string
}

variable "vpc_endpoint_id" {
  description = "ID of the S3 VPC endpoint for access restriction"
  type        = string
}

#------------------------------------------------------------------------------
# Optional Variables
#------------------------------------------------------------------------------
variable "glacier_transition_days" {
  description = "Number of days before transitioning objects to Glacier"
  type        = number
  default     = 90
}

variable "exports_expiration_days" {
  description = "Number of days before export objects are expired"
  type        = number
  default     = 365
}

variable "logging_bucket_id" {
  description = "ID of the bucket for S3 access logging (optional)"
  type        = string
  default     = null
}

variable "cors_allowed_origins" {
  description = "List of allowed origins for CORS configuration"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}
