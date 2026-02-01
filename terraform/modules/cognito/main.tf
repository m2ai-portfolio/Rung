# Rung Cognito Module - HIPAA Compliant User Authentication
# Creates Cognito User Pool with MFA for therapist authentication

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

#------------------------------------------------------------------------------
# Cognito User Pool
#------------------------------------------------------------------------------
resource "aws_cognito_user_pool" "therapists" {
  name = "${local.name_prefix}-therapists"

  # Username configuration
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  # Password policy - HIPAA compliant
  password_policy {
    minimum_length                   = var.password_minimum_length
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = true
    temporary_password_validity_days = var.temporary_password_validity_days
  }

  # MFA configuration - Required for HIPAA
  mfa_configuration = "ON"

  software_token_mfa_configuration {
    enabled = true
  }

  # Account recovery
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # Email configuration
  email_configuration {
    email_sending_account = var.ses_email_identity != null ? "DEVELOPER" : "COGNITO_DEFAULT"
    source_arn            = var.ses_email_identity
    from_email_address    = var.from_email_address
  }

  # User attribute verification
  user_attribute_update_settings {
    attributes_require_verification_before_update = ["email"]
  }

  # Advanced security features (for HIPAA)
  user_pool_add_ons {
    advanced_security_mode = "ENFORCED"
  }

  # Device tracking
  device_configuration {
    challenge_required_on_new_device      = true
    device_only_remembered_on_user_prompt = true
  }

  # Verification message
  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
    email_subject        = "Rung - Verify your email"
    email_message        = "Your verification code is {####}"
  }

  # Admin create user config
  admin_create_user_config {
    allow_admin_create_user_only = var.admin_create_user_only

    invite_message_template {
      email_subject = "Rung - Your temporary password"
      email_message = "Your username is {username} and temporary password is {####}. Please login and change your password."
      sms_message   = "Your username is {username} and temporary password is {####}"
    }
  }

  # Custom attributes
  schema {
    name                     = "practice_id"
    attribute_data_type      = "String"
    developer_only_attribute = false
    mutable                  = true
    required                 = false

    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  schema {
    name                     = "role"
    attribute_data_type      = "String"
    developer_only_attribute = false
    mutable                  = true
    required                 = false

    string_attribute_constraints {
      min_length = 1
      max_length = 50
    }
  }

  # User pool deletion protection
  deletion_protection = var.deletion_protection ? "ACTIVE" : "INACTIVE"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-therapists"
  })
}

#------------------------------------------------------------------------------
# User Pool Domain
#------------------------------------------------------------------------------
resource "aws_cognito_user_pool_domain" "therapists" {
  domain       = var.custom_domain != null ? var.custom_domain : "${local.name_prefix}-therapists"
  user_pool_id = aws_cognito_user_pool.therapists.id

  # For custom domain, certificate ARN is required
  certificate_arn = var.custom_domain != null ? var.custom_domain_certificate_arn : null
}

#------------------------------------------------------------------------------
# Resource Server (API Scopes)
#------------------------------------------------------------------------------
resource "aws_cognito_resource_server" "api" {
  identifier   = "rung-api"
  name         = "Rung API"
  user_pool_id = aws_cognito_user_pool.therapists.id

  scope {
    scope_name        = "read:sessions"
    scope_description = "Read session data"
  }

  scope {
    scope_name        = "write:sessions"
    scope_description = "Create and update session data"
  }

  scope {
    scope_name        = "read:clients"
    scope_description = "Read client data"
  }

  scope {
    scope_name        = "write:clients"
    scope_description = "Create and update client data"
  }

  scope {
    scope_name        = "admin"
    scope_description = "Full administrative access"
  }
}

#------------------------------------------------------------------------------
# App Client
#------------------------------------------------------------------------------
resource "aws_cognito_user_pool_client" "web_app" {
  name         = "${local.name_prefix}-web-client"
  user_pool_id = aws_cognito_user_pool.therapists.id

  # Client secret - required for authorization_code flow
  generate_secret = true

  # Token validity
  access_token_validity  = var.access_token_validity_hours
  id_token_validity      = var.id_token_validity_hours
  refresh_token_validity = var.refresh_token_validity_days

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }

  # OAuth configuration
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes = [
    "email",
    "openid",
    "profile",
    "rung-api/read:sessions",
    "rung-api/write:sessions",
    "rung-api/read:clients",
    "rung-api/write:clients"
  ]

  # Callback URLs
  callback_urls = var.callback_urls
  logout_urls   = var.logout_urls

  # Supported identity providers
  supported_identity_providers = ["COGNITO"]

  # Prevent user existence errors (security)
  prevent_user_existence_errors = "ENABLED"

  # Auth flows
  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH"
  ]

  # Read/Write attributes
  read_attributes = [
    "email",
    "email_verified",
    "name",
    "custom:practice_id",
    "custom:role"
  ]

  write_attributes = [
    "email",
    "name",
    "custom:practice_id",
    "custom:role"
  ]

  depends_on = [aws_cognito_resource_server.api]
}

#------------------------------------------------------------------------------
# Admin App Client (for backend services)
#------------------------------------------------------------------------------
resource "aws_cognito_user_pool_client" "admin" {
  name         = "${local.name_prefix}-admin-client"
  user_pool_id = aws_cognito_user_pool.therapists.id

  generate_secret = true

  access_token_validity  = 1
  id_token_validity      = 1
  refresh_token_validity = 1

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }

  allowed_oauth_flows                  = ["client_credentials"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes = [
    "rung-api/admin",
    "rung-api/read:sessions",
    "rung-api/write:sessions",
    "rung-api/read:clients",
    "rung-api/write:clients"
  ]

  supported_identity_providers = ["COGNITO"]

  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]

  depends_on = [aws_cognito_resource_server.api]
}

#------------------------------------------------------------------------------
# User Groups
#------------------------------------------------------------------------------
resource "aws_cognito_user_group" "therapists" {
  name         = "therapists"
  user_pool_id = aws_cognito_user_pool.therapists.id
  description  = "Licensed therapists with full client access"
  precedence   = 1
}

resource "aws_cognito_user_group" "practice_admins" {
  name         = "practice-admins"
  user_pool_id = aws_cognito_user_pool.therapists.id
  description  = "Practice administrators with management access"
  precedence   = 2
}

resource "aws_cognito_user_group" "supervisors" {
  name         = "supervisors"
  user_pool_id = aws_cognito_user_pool.therapists.id
  description  = "Clinical supervisors with oversight access"
  precedence   = 3
}

#------------------------------------------------------------------------------
# Lambda Triggers (optional)
#------------------------------------------------------------------------------
resource "aws_cognito_user_pool" "therapists_triggers" {
  count = var.enable_lambda_triggers ? 1 : 0

  # This is a workaround - normally you'd use a lifecycle block
  # to add triggers after initial creation
  name = "${local.name_prefix}-therapists"

  lambda_config {
    pre_sign_up                    = var.pre_signup_lambda_arn
    post_confirmation              = var.post_confirmation_lambda_arn
    pre_token_generation           = var.pre_token_generation_lambda_arn
    custom_message                 = var.custom_message_lambda_arn
    define_auth_challenge          = var.define_auth_challenge_lambda_arn
    create_auth_challenge          = var.create_auth_challenge_lambda_arn
    verify_auth_challenge_response = var.verify_auth_challenge_lambda_arn
  }
}
