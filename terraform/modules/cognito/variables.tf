# Cognito Module Variables

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

variable "callback_urls" {
  description = "List of allowed callback URLs after authentication"
  type        = list(string)
}

variable "logout_urls" {
  description = "List of allowed logout URLs"
  type        = list(string)
}

#------------------------------------------------------------------------------
# Password Policy
#------------------------------------------------------------------------------
variable "password_minimum_length" {
  description = "Minimum password length (HIPAA recommends 12+)"
  type        = number
  default     = 12
}

variable "temporary_password_validity_days" {
  description = "Days before temporary password expires"
  type        = number
  default     = 7
}

#------------------------------------------------------------------------------
# Token Validity
#------------------------------------------------------------------------------
variable "access_token_validity_hours" {
  description = "Access token validity in hours"
  type        = number
  default     = 1
}

variable "id_token_validity_hours" {
  description = "ID token validity in hours"
  type        = number
  default     = 1
}

variable "refresh_token_validity_days" {
  description = "Refresh token validity in days"
  type        = number
  default     = 30
}

#------------------------------------------------------------------------------
# Email Configuration
#------------------------------------------------------------------------------
variable "ses_email_identity" {
  description = "SES email identity ARN for custom email sending (optional)"
  type        = string
  default     = null
}

variable "from_email_address" {
  description = "From email address for Cognito emails"
  type        = string
  default     = null
}

#------------------------------------------------------------------------------
# Domain Configuration
#------------------------------------------------------------------------------
variable "custom_domain" {
  description = "Custom domain for Cognito hosted UI (optional)"
  type        = string
  default     = null
}

variable "custom_domain_certificate_arn" {
  description = "ACM certificate ARN for custom domain"
  type        = string
  default     = null
}

#------------------------------------------------------------------------------
# Security Settings
#------------------------------------------------------------------------------
variable "admin_create_user_only" {
  description = "Only allow admins to create users (recommended for healthcare)"
  type        = bool
  default     = true
}

variable "deletion_protection" {
  description = "Enable deletion protection on user pool"
  type        = bool
  default     = false
}

#------------------------------------------------------------------------------
# Lambda Triggers
#------------------------------------------------------------------------------
variable "enable_lambda_triggers" {
  description = "Enable Lambda triggers for user pool events"
  type        = bool
  default     = false
}

variable "pre_signup_lambda_arn" {
  description = "ARN of pre-signup Lambda function"
  type        = string
  default     = null
}

variable "post_confirmation_lambda_arn" {
  description = "ARN of post-confirmation Lambda function"
  type        = string
  default     = null
}

variable "pre_token_generation_lambda_arn" {
  description = "ARN of pre-token generation Lambda function"
  type        = string
  default     = null
}

variable "custom_message_lambda_arn" {
  description = "ARN of custom message Lambda function"
  type        = string
  default     = null
}

variable "define_auth_challenge_lambda_arn" {
  description = "ARN of define auth challenge Lambda function"
  type        = string
  default     = null
}

variable "create_auth_challenge_lambda_arn" {
  description = "ARN of create auth challenge Lambda function"
  type        = string
  default     = null
}

variable "verify_auth_challenge_lambda_arn" {
  description = "ARN of verify auth challenge Lambda function"
  type        = string
  default     = null
}

#------------------------------------------------------------------------------
# Tags
#------------------------------------------------------------------------------
variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}
