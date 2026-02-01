# Cognito Module Outputs

#------------------------------------------------------------------------------
# User Pool
#------------------------------------------------------------------------------
output "user_pool_id" {
  description = "ID of the Cognito user pool"
  value       = aws_cognito_user_pool.therapists.id
}

output "user_pool_arn" {
  description = "ARN of the Cognito user pool"
  value       = aws_cognito_user_pool.therapists.arn
}

output "user_pool_endpoint" {
  description = "Endpoint of the Cognito user pool"
  value       = aws_cognito_user_pool.therapists.endpoint
}

output "user_pool_name" {
  description = "Name of the Cognito user pool"
  value       = aws_cognito_user_pool.therapists.name
}

#------------------------------------------------------------------------------
# Domain
#------------------------------------------------------------------------------
output "user_pool_domain" {
  description = "Domain of the Cognito user pool"
  value       = aws_cognito_user_pool_domain.therapists.domain
}

output "cognito_domain_url" {
  description = "Full URL of the Cognito hosted UI domain"
  value       = "https://${aws_cognito_user_pool_domain.therapists.domain}.auth.${data.aws_region.current.id}.amazoncognito.com"
}

# Get current region for domain URL
data "aws_region" "current" {}

#------------------------------------------------------------------------------
# Web App Client
#------------------------------------------------------------------------------
output "web_client_id" {
  description = "ID of the web app client"
  value       = aws_cognito_user_pool_client.web_app.id
}

output "web_client_secret" {
  description = "Secret of the web app client"
  value       = aws_cognito_user_pool_client.web_app.client_secret
  sensitive   = true
}

output "web_client_name" {
  description = "Name of the web app client"
  value       = aws_cognito_user_pool_client.web_app.name
}

#------------------------------------------------------------------------------
# Admin Client
#------------------------------------------------------------------------------
output "admin_client_id" {
  description = "ID of the admin client"
  value       = aws_cognito_user_pool_client.admin.id
}

output "admin_client_secret" {
  description = "Secret of the admin client"
  value       = aws_cognito_user_pool_client.admin.client_secret
  sensitive   = true
}

#------------------------------------------------------------------------------
# Resource Server
#------------------------------------------------------------------------------
output "resource_server_identifier" {
  description = "Identifier of the API resource server"
  value       = aws_cognito_resource_server.api.identifier
}

output "resource_server_scopes" {
  description = "List of scopes defined on the resource server"
  value       = aws_cognito_resource_server.api.scope[*].scope_name
}

#------------------------------------------------------------------------------
# User Groups
#------------------------------------------------------------------------------
output "user_groups" {
  description = "Map of user group names"
  value = {
    therapists     = aws_cognito_user_group.therapists.name
    practice_admins = aws_cognito_user_group.practice_admins.name
    supervisors    = aws_cognito_user_group.supervisors.name
  }
}

#------------------------------------------------------------------------------
# MFA Status
#------------------------------------------------------------------------------
output "mfa_configuration" {
  description = "MFA configuration status"
  value       = aws_cognito_user_pool.therapists.mfa_configuration
}

output "mfa_enforced" {
  description = "Whether MFA is enforced (ON = required)"
  value       = aws_cognito_user_pool.therapists.mfa_configuration == "ON"
}

#------------------------------------------------------------------------------
# Password Policy
#------------------------------------------------------------------------------
output "password_policy" {
  description = "Password policy configuration"
  value = {
    minimum_length    = aws_cognito_user_pool.therapists.password_policy[0].minimum_length
    require_lowercase = aws_cognito_user_pool.therapists.password_policy[0].require_lowercase
    require_uppercase = aws_cognito_user_pool.therapists.password_policy[0].require_uppercase
    require_numbers   = aws_cognito_user_pool.therapists.password_policy[0].require_numbers
    require_symbols   = aws_cognito_user_pool.therapists.password_policy[0].require_symbols
  }
}

#------------------------------------------------------------------------------
# OAuth Endpoints
#------------------------------------------------------------------------------
output "oauth_endpoints" {
  description = "OAuth 2.0 endpoints for the user pool"
  value = {
    authorization = "https://${aws_cognito_user_pool_domain.therapists.domain}.auth.${data.aws_region.current.id}.amazoncognito.com/oauth2/authorize"
    token         = "https://${aws_cognito_user_pool_domain.therapists.domain}.auth.${data.aws_region.current.id}.amazoncognito.com/oauth2/token"
    userinfo      = "https://${aws_cognito_user_pool_domain.therapists.domain}.auth.${data.aws_region.current.id}.amazoncognito.com/oauth2/userInfo"
    logout        = "https://${aws_cognito_user_pool_domain.therapists.domain}.auth.${data.aws_region.current.id}.amazoncognito.com/logout"
  }
}

#------------------------------------------------------------------------------
# JWKS URI (for token verification)
#------------------------------------------------------------------------------
output "jwks_uri" {
  description = "JWKS URI for token verification"
  value       = "https://cognito-idp.${data.aws_region.current.id}.amazonaws.com/${aws_cognito_user_pool.therapists.id}/.well-known/jwks.json"
}

#------------------------------------------------------------------------------
# Custom Attributes
#------------------------------------------------------------------------------
output "custom_attributes" {
  description = "List of custom attributes defined on the user pool"
  value       = ["practice_id", "role"]
}
