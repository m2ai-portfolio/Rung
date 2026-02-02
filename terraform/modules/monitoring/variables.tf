# =============================================================================
# Rung Monitoring Module - Variables
# =============================================================================

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "kms_key_id" {
  description = "KMS key ID for SNS topic encryption"
  type        = string
}

variable "kms_key_arn" {
  description = "KMS key ARN for CloudWatch Logs encryption"
  type        = string
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "alert_email" {
  description = "Email address for alert notifications"
  type        = string
  default     = ""
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for alert notifications"
  type        = string
  default     = ""
  sensitive   = true
}

variable "pagerduty_integration_key" {
  description = "PagerDuty integration key for critical alerts"
  type        = string
  default     = ""
  sensitive   = true
}

variable "enable_anomaly_detection" {
  description = "Enable CloudWatch anomaly detection alarms"
  type        = bool
  default     = true
}

variable "failed_auth_threshold" {
  description = "Threshold for failed authentication alarm"
  type        = number
  default     = 10
}

variable "api_error_threshold" {
  description = "Threshold for API error alarm"
  type        = number
  default     = 10
}

variable "phi_access_threshold" {
  description = "Threshold for high PHI access alarm"
  type        = number
  default     = 1000
}

variable "log_retention_days" {
  description = "Log retention in days (HIPAA requires 7 years = 2557 days)"
  type        = number
  default     = 2557

  validation {
    condition     = var.log_retention_days >= 2557
    error_message = "Log retention must be at least 2557 days (7 years) for HIPAA compliance."
  }
}
