# RDS Module Variables

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "rung"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

#------------------------------------------------------------------------------
# Database Configuration
#------------------------------------------------------------------------------
variable "database_name" {
  description = "Name of the database to create"
  type        = string
  default     = "rung"
}

variable "engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "15"
}

variable "instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.r6g.large"
}

variable "allocated_storage" {
  description = "Allocated storage in GB"
  type        = number
  default     = 100
}

variable "max_allocated_storage" {
  description = "Maximum allocated storage for autoscaling in GB"
  type        = number
  default     = 500
}

variable "storage_type" {
  description = "Storage type (gp3, io1, etc.)"
  type        = string
  default     = "gp3"
}

variable "storage_iops" {
  description = "Storage IOPS (for gp3 or io1)"
  type        = number
  default     = 3000
}

variable "storage_throughput" {
  description = "Storage throughput in MiBps (for gp3)"
  type        = number
  default     = 125
}

#------------------------------------------------------------------------------
# High Availability
#------------------------------------------------------------------------------
variable "multi_az" {
  description = "Enable Multi-AZ deployment"
  type        = bool
  default     = true
}

#------------------------------------------------------------------------------
# Network Configuration
#------------------------------------------------------------------------------
variable "vpc_id" {
  description = "VPC ID where RDS will be deployed"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for RDS subnet group"
  type        = list(string)
}

variable "security_group_ids" {
  description = "List of security group IDs for RDS"
  type        = list(string)
}

#------------------------------------------------------------------------------
# Encryption
#------------------------------------------------------------------------------
variable "kms_key_arn" {
  description = "ARN of the KMS key for RDS encryption"
  type        = string
}

variable "secrets_kms_key_arn" {
  description = "ARN of the KMS key for Secrets Manager"
  type        = string
}

#------------------------------------------------------------------------------
# Backup Configuration
#------------------------------------------------------------------------------
variable "backup_retention_period" {
  description = "Number of days to retain backups"
  type        = number
  default     = 35  # HIPAA recommends minimum 30 days
}

variable "backup_window" {
  description = "Preferred backup window (UTC)"
  type        = string
  default     = "03:00-04:00"
}

variable "maintenance_window" {
  description = "Preferred maintenance window (UTC)"
  type        = string
  default     = "Mon:04:00-Mon:05:00"
}

#------------------------------------------------------------------------------
# Monitoring
#------------------------------------------------------------------------------
variable "performance_insights_enabled" {
  description = "Enable Performance Insights"
  type        = bool
  default     = true
}

variable "performance_insights_retention_period" {
  description = "Performance Insights retention period in days"
  type        = number
  default     = 7
}

variable "monitoring_interval" {
  description = "Enhanced monitoring interval in seconds (0 to disable)"
  type        = number
  default     = 60
}

variable "enabled_cloudwatch_logs_exports" {
  description = "List of log types to export to CloudWatch"
  type        = list(string)
  default     = ["postgresql", "upgrade"]
}

#------------------------------------------------------------------------------
# Deletion Protection
#------------------------------------------------------------------------------
variable "deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = true
}

variable "skip_final_snapshot" {
  description = "Skip final snapshot on deletion"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}
