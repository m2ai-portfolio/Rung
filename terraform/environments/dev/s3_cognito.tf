# Rung Dev Environment - S3 and Cognito Configuration
# This file creates S3 buckets and Cognito user pool for therapist authentication

#------------------------------------------------------------------------------
# S3 Module - Storage Buckets
#------------------------------------------------------------------------------
module "s3" {
  source = "../../modules/s3"

  project_name = "rung"
  environment  = var.environment

  # Encryption (from KMS module)
  s3_kms_key_arn = module.kms.s3_key_arn

  # VPC access restriction
  vpc_endpoint_id = module.vpc.s3_vpc_endpoint_id

  # Lifecycle settings
  glacier_transition_days = 90
  exports_expiration_days = 365

  # CORS for voice memo uploads (configure for your frontend domain)
  cors_allowed_origins = var.cors_allowed_origins

  tags = {
    CostCenter = "rung-dev"
  }

  depends_on = [module.vpc, module.kms]
}

#------------------------------------------------------------------------------
# Cognito Module - User Authentication
#------------------------------------------------------------------------------
module "cognito" {
  source = "../../modules/cognito"

  project_name = "rung"
  environment  = var.environment

  # OAuth callback URLs (configure for your frontend)
  callback_urls = var.cognito_callback_urls
  logout_urls   = var.cognito_logout_urls

  # Password policy (HIPAA compliant)
  password_minimum_length          = 12
  temporary_password_validity_days = 7

  # Token validity
  access_token_validity_hours  = 1
  id_token_validity_hours      = 1
  refresh_token_validity_days  = 30

  # Admin settings
  admin_create_user_only = true  # Only admins can create therapist accounts
  deletion_protection    = false # Set to true in production

  tags = {
    CostCenter = "rung-dev"
  }
}

#------------------------------------------------------------------------------
# S3 Outputs
#------------------------------------------------------------------------------
output "s3_voice_memos_bucket_name" {
  description = "Name of the voice memos bucket"
  value       = module.s3.voice_memos_bucket_name
}

output "s3_voice_memos_bucket_arn" {
  description = "ARN of the voice memos bucket"
  value       = module.s3.voice_memos_bucket_arn
}

output "s3_transcripts_bucket_name" {
  description = "Name of the transcripts bucket"
  value       = module.s3.transcripts_bucket_name
}

output "s3_transcripts_bucket_arn" {
  description = "ARN of the transcripts bucket"
  value       = module.s3.transcripts_bucket_arn
}

output "s3_exports_bucket_name" {
  description = "Name of the exports bucket"
  value       = module.s3.exports_bucket_name
}

output "s3_exports_bucket_arn" {
  description = "ARN of the exports bucket"
  value       = module.s3.exports_bucket_arn
}

output "s3_buckets_encrypted" {
  description = "Confirmation that all buckets are encrypted"
  value       = module.s3.buckets_encrypted
}

output "s3_public_access_blocked" {
  description = "Confirmation that public access is blocked"
  value       = module.s3.public_access_blocked
}

output "s3_versioning_enabled" {
  description = "Versioning status for all buckets"
  value       = module.s3.buckets_versioning_enabled
}

#------------------------------------------------------------------------------
# Cognito Outputs
#------------------------------------------------------------------------------
output "cognito_user_pool_id" {
  description = "ID of the Cognito user pool"
  value       = module.cognito.user_pool_id
}

output "cognito_user_pool_arn" {
  description = "ARN of the Cognito user pool"
  value       = module.cognito.user_pool_arn
}

output "cognito_user_pool_endpoint" {
  description = "Endpoint of the Cognito user pool"
  value       = module.cognito.user_pool_endpoint
}

output "cognito_domain_url" {
  description = "URL of the Cognito hosted UI"
  value       = module.cognito.cognito_domain_url
}

output "cognito_web_client_id" {
  description = "ID of the web app client"
  value       = module.cognito.web_client_id
}

output "cognito_web_client_secret" {
  description = "Secret of the web app client"
  value       = module.cognito.web_client_secret
  sensitive   = true
}

output "cognito_mfa_enforced" {
  description = "Whether MFA is enforced"
  value       = module.cognito.mfa_enforced
}

output "cognito_password_policy" {
  description = "Password policy configuration"
  value       = module.cognito.password_policy
}

output "cognito_oauth_endpoints" {
  description = "OAuth 2.0 endpoints"
  value       = module.cognito.oauth_endpoints
}

output "cognito_jwks_uri" {
  description = "JWKS URI for token verification"
  value       = module.cognito.jwks_uri
}

output "cognito_user_groups" {
  description = "User groups defined in Cognito"
  value       = module.cognito.user_groups
}

output "cognito_custom_attributes" {
  description = "Custom attributes defined in Cognito"
  value       = module.cognito.custom_attributes
}
