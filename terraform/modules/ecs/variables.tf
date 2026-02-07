# ECS Module Variables

#------------------------------------------------------------------------------
# Basic Configuration
#------------------------------------------------------------------------------
variable "project_name" {
  description = "Project name"
  type        = string
  default     = "rung"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}

#------------------------------------------------------------------------------
# Container Configuration
#------------------------------------------------------------------------------
variable "cpu" {
  description = "Task CPU units (256, 512, 1024, 2048, 4096)"
  type        = number
  default     = 512
  validation {
    condition     = contains([256, 512, 1024, 2048, 4096], var.cpu)
    error_message = "Valid CPU values: 256, 512, 1024, 2048, 4096."
  }
}

variable "memory" {
  description = "Task memory in MB (512-30720, valid combinations depend on CPU)"
  type        = number
  default     = 1024
}

variable "container_port" {
  description = "Port on which container listens"
  type        = number
  default     = 8000
}

variable "log_level" {
  description = "Application log level (DEBUG, INFO, WARNING, ERROR)"
  type        = string
  default     = "INFO"
}

#------------------------------------------------------------------------------
# Service Configuration
#------------------------------------------------------------------------------
variable "desired_count" {
  description = "Desired number of task instances"
  type        = number
  default     = 1
  validation {
    condition     = var.desired_count >= 1
    error_message = "Desired count must be at least 1."
  }
}

variable "max_capacity" {
  description = "Maximum number of task instances for auto-scaling"
  type        = number
  default     = 4
}

#------------------------------------------------------------------------------
# Network Configuration
#------------------------------------------------------------------------------
variable "vpc_id" {
  description = "VPC ID where ECS tasks will run"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for ECS tasks"
  type        = list(string)
  validation {
    condition     = length(var.private_subnet_ids) >= 1
    error_message = "At least one private subnet is required."
  }
}

variable "alb_arn" {
  description = "ARN of the Application Load Balancer"
  type        = string
}

variable "alb_security_group_id" {
  description = "Security group ID of the ALB"
  type        = string
}

variable "rds_security_group_id" {
  description = "Security group ID of RDS for ECS egress"
  type        = string
}

variable "vpc_endpoints_security_group_id" {
  description = "Security group ID for VPC endpoints"
  type        = string
}

variable "s3_vpc_endpoint_prefix_list_id" {
  description = "Prefix list ID for S3 VPC endpoint"
  type        = string
}

#------------------------------------------------------------------------------
# Database Configuration
#------------------------------------------------------------------------------
variable "database_secret_arn" {
  description = "ARN of the Secrets Manager secret containing database credentials"
  type        = string
  sensitive   = true
}

variable "database_secret_kms_key_arn" {
  description = "ARN of the KMS key used to encrypt database secret"
  type        = string
}

#------------------------------------------------------------------------------
# KMS Keys
#------------------------------------------------------------------------------
variable "ecr_kms_key_arn" {
  description = "ARN of KMS key for ECR encryption"
  type        = string
}

variable "logs_kms_key_id" {
  description = "KMS key ID for CloudWatch logs encryption"
  type        = string
}

variable "s3_kms_key_arn" {
  description = "ARN of KMS key for S3 encryption"
  type        = string
}

variable "field_encryption_key_arn" {
  description = "ARN of KMS key for field-level encryption"
  type        = string
}

#------------------------------------------------------------------------------
# S3 Configuration
#------------------------------------------------------------------------------
variable "s3_bucket_name" {
  description = "Name of the S3 bucket for voice files and documents"
  type        = string
}

#------------------------------------------------------------------------------
# Logging Configuration
#------------------------------------------------------------------------------
variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 365
  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.log_retention_days)
    error_message = "Log retention must be a valid CloudWatch value."
  }
}
