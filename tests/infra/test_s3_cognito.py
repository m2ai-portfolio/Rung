"""
S3 and Cognito Infrastructure Tests for Phase 1C

Tests verify:
1. S3 buckets are configured for encryption (KMS)
2. Versioning is enabled on all buckets
3. Public access is blocked
4. Lifecycle rules are configured
5. Cognito user pool has MFA enforced
6. Password policy meets HIPAA requirements
7. Custom attributes are defined
8. OAuth flows are properly configured

Note: These tests verify Terraform configuration files.
For real infrastructure validation, use terraform plan/apply.
"""

import json
import os
import pytest


class TestS3ModuleConfiguration:
    """Test S3 module configuration files."""

    def test_s3_module_main_exists(self):
        """Verify s3/main.tf exists."""
        path = "terraform/modules/s3/main.tf"
        assert os.path.exists(path), f"Missing {path}"

    def test_s3_module_variables_exists(self):
        """Verify s3/variables.tf exists."""
        path = "terraform/modules/s3/variables.tf"
        assert os.path.exists(path), f"Missing {path}"

    def test_s3_module_outputs_exists(self):
        """Verify s3/outputs.tf exists."""
        path = "terraform/modules/s3/outputs.tf"
        assert os.path.exists(path), f"Missing {path}"


class TestS3BucketConfiguration:
    """Test S3 bucket definitions."""

    def test_voice_memos_bucket_defined(self):
        """Verify voice memos bucket is defined."""
        with open("terraform/modules/s3/main.tf", "r") as f:
            content = f.read()
        assert 'aws_s3_bucket" "voice_memos"' in content, "Voice memos bucket should be defined"

    def test_transcripts_bucket_defined(self):
        """Verify transcripts bucket is defined."""
        with open("terraform/modules/s3/main.tf", "r") as f:
            content = f.read()
        assert 'aws_s3_bucket" "transcripts"' in content, "Transcripts bucket should be defined"

    def test_exports_bucket_defined(self):
        """Verify exports bucket is defined."""
        with open("terraform/modules/s3/main.tf", "r") as f:
            content = f.read()
        assert 'aws_s3_bucket" "exports"' in content, "Exports bucket should be defined"


class TestS3Encryption:
    """Test S3 encryption configuration."""

    def test_voice_memos_encryption(self):
        """Verify voice memos bucket has KMS encryption."""
        with open("terraform/modules/s3/main.tf", "r") as f:
            content = f.read()
        assert 'aws_s3_bucket_server_side_encryption_configuration" "voice_memos"' in content
        assert "aws:kms" in content, "KMS encryption should be used"

    def test_transcripts_encryption(self):
        """Verify transcripts bucket has KMS encryption."""
        with open("terraform/modules/s3/main.tf", "r") as f:
            content = f.read()
        assert 'aws_s3_bucket_server_side_encryption_configuration" "transcripts"' in content

    def test_exports_encryption(self):
        """Verify exports bucket has KMS encryption."""
        with open("terraform/modules/s3/main.tf", "r") as f:
            content = f.read()
        assert 'aws_s3_bucket_server_side_encryption_configuration" "exports"' in content

    def test_kms_key_reference(self):
        """Verify KMS key is referenced for encryption."""
        with open("terraform/modules/s3/main.tf", "r") as f:
            content = f.read()
        assert "kms_master_key_id" in content, "KMS key should be referenced"
        assert "var.s3_kms_key_arn" in content, "S3 KMS key variable should be used"


class TestS3Versioning:
    """Test S3 versioning configuration."""

    def test_voice_memos_versioning(self):
        """Verify voice memos bucket has versioning enabled."""
        with open("terraform/modules/s3/main.tf", "r") as f:
            content = f.read()
        assert 'aws_s3_bucket_versioning" "voice_memos"' in content
        assert '"Enabled"' in content or 'status = "Enabled"' in content

    def test_transcripts_versioning(self):
        """Verify transcripts bucket has versioning enabled."""
        with open("terraform/modules/s3/main.tf", "r") as f:
            content = f.read()
        assert 'aws_s3_bucket_versioning" "transcripts"' in content

    def test_exports_versioning(self):
        """Verify exports bucket has versioning enabled."""
        with open("terraform/modules/s3/main.tf", "r") as f:
            content = f.read()
        assert 'aws_s3_bucket_versioning" "exports"' in content

    def test_versioning_output(self):
        """Verify versioning status is output."""
        with open("terraform/modules/s3/outputs.tf", "r") as f:
            content = f.read()
        assert "versioning" in content.lower(), "Versioning status should be output"


class TestS3PublicAccessBlock:
    """Test S3 public access block configuration."""

    def test_voice_memos_public_block(self):
        """Verify voice memos bucket blocks public access."""
        with open("terraform/modules/s3/main.tf", "r") as f:
            content = f.read()
        assert 'aws_s3_bucket_public_access_block" "voice_memos"' in content

    def test_transcripts_public_block(self):
        """Verify transcripts bucket blocks public access."""
        with open("terraform/modules/s3/main.tf", "r") as f:
            content = f.read()
        assert 'aws_s3_bucket_public_access_block" "transcripts"' in content

    def test_exports_public_block(self):
        """Verify exports bucket blocks public access."""
        with open("terraform/modules/s3/main.tf", "r") as f:
            content = f.read()
        assert 'aws_s3_bucket_public_access_block" "exports"' in content

    def test_all_public_access_blocked(self):
        """Verify all public access settings are blocked."""
        with open("terraform/modules/s3/main.tf", "r") as f:
            content = f.read()
        assert "block_public_acls       = true" in content
        assert "block_public_policy     = true" in content
        assert "ignore_public_acls      = true" in content
        assert "restrict_public_buckets = true" in content


class TestS3LifecycleRules:
    """Test S3 lifecycle configuration."""

    def test_voice_memos_lifecycle(self):
        """Verify voice memos bucket has lifecycle rules."""
        with open("terraform/modules/s3/main.tf", "r") as f:
            content = f.read()
        assert 'aws_s3_bucket_lifecycle_configuration" "voice_memos"' in content

    def test_transcripts_lifecycle(self):
        """Verify transcripts bucket has lifecycle rules."""
        with open("terraform/modules/s3/main.tf", "r") as f:
            content = f.read()
        assert 'aws_s3_bucket_lifecycle_configuration" "transcripts"' in content

    def test_exports_lifecycle(self):
        """Verify exports bucket has lifecycle rules."""
        with open("terraform/modules/s3/main.tf", "r") as f:
            content = f.read()
        assert 'aws_s3_bucket_lifecycle_configuration" "exports"' in content

    def test_glacier_transition(self):
        """Verify Glacier transition is configured."""
        with open("terraform/modules/s3/main.tf", "r") as f:
            content = f.read()
        assert "GLACIER" in content, "Glacier transition should be configured"

    def test_glacier_transition_days_variable(self):
        """Verify glacier transition days is configurable."""
        with open("terraform/modules/s3/variables.tf", "r") as f:
            content = f.read()
        assert "glacier_transition_days" in content
        assert "90" in content, "Default should be 90 days"


class TestS3BucketPolicies:
    """Test S3 bucket policy configuration."""

    def test_voice_memos_policy(self):
        """Verify voice memos bucket has policy."""
        with open("terraform/modules/s3/main.tf", "r") as f:
            content = f.read()
        assert 'aws_s3_bucket_policy" "voice_memos"' in content

    def test_transcripts_policy(self):
        """Verify transcripts bucket has policy."""
        with open("terraform/modules/s3/main.tf", "r") as f:
            content = f.read()
        assert 'aws_s3_bucket_policy" "transcripts"' in content

    def test_https_enforcement(self):
        """Verify HTTPS is enforced."""
        with open("terraform/modules/s3/main.tf", "r") as f:
            content = f.read()
        assert "SecureTransport" in content, "HTTPS should be enforced"

    def test_vpc_endpoint_restriction(self):
        """Verify VPC endpoint restriction."""
        with open("terraform/modules/s3/main.tf", "r") as f:
            content = f.read()
        assert "aws:SourceVpce" in content, "VPC endpoint restriction should be configured"


class TestCognitoModuleConfiguration:
    """Test Cognito module configuration files."""

    def test_cognito_module_main_exists(self):
        """Verify cognito/main.tf exists."""
        path = "terraform/modules/cognito/main.tf"
        assert os.path.exists(path), f"Missing {path}"

    def test_cognito_module_variables_exists(self):
        """Verify cognito/variables.tf exists."""
        path = "terraform/modules/cognito/variables.tf"
        assert os.path.exists(path), f"Missing {path}"

    def test_cognito_module_outputs_exists(self):
        """Verify cognito/outputs.tf exists."""
        path = "terraform/modules/cognito/outputs.tf"
        assert os.path.exists(path), f"Missing {path}"


class TestCognitoUserPool:
    """Test Cognito user pool configuration."""

    def test_user_pool_defined(self):
        """Verify user pool is defined."""
        with open("terraform/modules/cognito/main.tf", "r") as f:
            content = f.read()
        assert 'aws_cognito_user_pool" "therapists"' in content, "User pool should be defined"

    def test_user_pool_name(self):
        """Verify user pool naming convention."""
        with open("terraform/modules/cognito/main.tf", "r") as f:
            content = f.read()
        assert "therapists" in content, "User pool should be named for therapists"


class TestCognitoMFA:
    """Test Cognito MFA configuration."""

    def test_mfa_required(self):
        """Verify MFA is required (ON)."""
        with open("terraform/modules/cognito/main.tf", "r") as f:
            content = f.read()
        assert 'mfa_configuration = "ON"' in content, "MFA should be required"

    def test_totp_enabled(self):
        """Verify TOTP is enabled."""
        with open("terraform/modules/cognito/main.tf", "r") as f:
            content = f.read()
        assert "software_token_mfa_configuration" in content
        assert "enabled = true" in content, "Software token MFA should be enabled"

    def test_mfa_output(self):
        """Verify MFA status is output."""
        with open("terraform/modules/cognito/outputs.tf", "r") as f:
            content = f.read()
        assert "mfa_enforced" in content, "MFA enforcement status should be output"


class TestCognitoPasswordPolicy:
    """Test Cognito password policy configuration."""

    def test_minimum_length_12(self):
        """Verify minimum password length is 12+."""
        with open("terraform/modules/cognito/variables.tf", "r") as f:
            content = f.read()
        assert "password_minimum_length" in content
        assert "12" in content, "Minimum password length should be 12"

    def test_require_lowercase(self):
        """Verify lowercase is required."""
        with open("terraform/modules/cognito/main.tf", "r") as f:
            content = f.read()
        assert "require_lowercase" in content
        assert "true" in content

    def test_require_uppercase(self):
        """Verify uppercase is required."""
        with open("terraform/modules/cognito/main.tf", "r") as f:
            content = f.read()
        assert "require_uppercase" in content

    def test_require_numbers(self):
        """Verify numbers are required."""
        with open("terraform/modules/cognito/main.tf", "r") as f:
            content = f.read()
        assert "require_numbers" in content

    def test_require_symbols(self):
        """Verify symbols are required."""
        with open("terraform/modules/cognito/main.tf", "r") as f:
            content = f.read()
        assert "require_symbols" in content

    def test_password_policy_output(self):
        """Verify password policy is output."""
        with open("terraform/modules/cognito/outputs.tf", "r") as f:
            content = f.read()
        assert "password_policy" in content


class TestCognitoEmailVerification:
    """Test Cognito email verification configuration."""

    def test_email_verification_required(self):
        """Verify email verification is required."""
        with open("terraform/modules/cognito/main.tf", "r") as f:
            content = f.read()
        assert "auto_verified_attributes" in content
        assert '"email"' in content, "Email should be auto-verified"

    def test_verification_message(self):
        """Verify verification message is configured."""
        with open("terraform/modules/cognito/main.tf", "r") as f:
            content = f.read()
        assert "verification_message_template" in content


class TestCognitoCustomAttributes:
    """Test Cognito custom attributes configuration."""

    def test_practice_id_attribute(self):
        """Verify practice_id custom attribute is defined."""
        with open("terraform/modules/cognito/main.tf", "r") as f:
            content = f.read()
        assert 'name                     = "practice_id"' in content, "practice_id attribute should be defined"

    def test_role_attribute(self):
        """Verify role custom attribute is defined."""
        with open("terraform/modules/cognito/main.tf", "r") as f:
            content = f.read()
        assert 'name                     = "role"' in content, "role attribute should be defined"

    def test_custom_attributes_output(self):
        """Verify custom attributes are output."""
        with open("terraform/modules/cognito/outputs.tf", "r") as f:
            content = f.read()
        assert "custom_attributes" in content


class TestCognitoAppClient:
    """Test Cognito app client configuration."""

    def test_web_client_defined(self):
        """Verify web app client is defined."""
        with open("terraform/modules/cognito/main.tf", "r") as f:
            content = f.read()
        assert 'aws_cognito_user_pool_client" "web_app"' in content

    def test_client_secret_generated(self):
        """Verify client secret is generated."""
        with open("terraform/modules/cognito/main.tf", "r") as f:
            content = f.read()
        assert "generate_secret = true" in content

    def test_authorization_code_flow(self):
        """Verify authorization_code flow is configured."""
        with open("terraform/modules/cognito/main.tf", "r") as f:
            content = f.read()
        assert '"code"' in content, "Authorization code flow should be enabled"

    def test_refresh_token_flow(self):
        """Verify refresh token flow is configured."""
        with open("terraform/modules/cognito/main.tf", "r") as f:
            content = f.read()
        assert "ALLOW_REFRESH_TOKEN_AUTH" in content

    def test_callback_urls_variable(self):
        """Verify callback URLs are configurable."""
        with open("terraform/modules/cognito/variables.tf", "r") as f:
            content = f.read()
        assert "callback_urls" in content

    def test_logout_urls_variable(self):
        """Verify logout URLs are configurable."""
        with open("terraform/modules/cognito/variables.tf", "r") as f:
            content = f.read()
        assert "logout_urls" in content


class TestCognitoOAuthEndpoints:
    """Test Cognito OAuth endpoints configuration."""

    def test_oauth_endpoints_output(self):
        """Verify OAuth endpoints are output."""
        with open("terraform/modules/cognito/outputs.tf", "r") as f:
            content = f.read()
        assert "oauth_endpoints" in content
        assert "authorization" in content
        assert "token" in content

    def test_jwks_uri_output(self):
        """Verify JWKS URI is output."""
        with open("terraform/modules/cognito/outputs.tf", "r") as f:
            content = f.read()
        assert "jwks_uri" in content


class TestCognitoResourceServer:
    """Test Cognito resource server configuration."""

    def test_resource_server_defined(self):
        """Verify API resource server is defined."""
        with open("terraform/modules/cognito/main.tf", "r") as f:
            content = f.read()
        assert 'aws_cognito_resource_server" "api"' in content

    def test_api_scopes_defined(self):
        """Verify API scopes are defined."""
        with open("terraform/modules/cognito/main.tf", "r") as f:
            content = f.read()
        assert "read:sessions" in content
        assert "write:sessions" in content
        assert "read:clients" in content
        assert "write:clients" in content


class TestCognitoUserGroups:
    """Test Cognito user groups configuration."""

    def test_therapists_group_defined(self):
        """Verify therapists group is defined."""
        with open("terraform/modules/cognito/main.tf", "r") as f:
            content = f.read()
        assert 'aws_cognito_user_group" "therapists"' in content

    def test_user_groups_output(self):
        """Verify user groups are output."""
        with open("terraform/modules/cognito/outputs.tf", "r") as f:
            content = f.read()
        assert "user_groups" in content


class TestCognitoSecurity:
    """Test Cognito security configuration."""

    def test_advanced_security_enabled(self):
        """Verify advanced security is enabled."""
        with open("terraform/modules/cognito/main.tf", "r") as f:
            content = f.read()
        assert "user_pool_add_ons" in content
        assert "ENFORCED" in content, "Advanced security should be enforced"

    def test_prevent_user_existence_errors(self):
        """Verify user existence errors are prevented."""
        with open("terraform/modules/cognito/main.tf", "r") as f:
            content = f.read()
        assert "prevent_user_existence_errors" in content
        assert "ENABLED" in content

    def test_device_tracking(self):
        """Verify device tracking is configured."""
        with open("terraform/modules/cognito/main.tf", "r") as f:
            content = f.read()
        assert "device_configuration" in content
        assert "challenge_required_on_new_device" in content


class TestCognitoHIPAACompliance:
    """Test Cognito HIPAA compliance configurations."""

    def test_admin_create_user_only(self):
        """Verify only admins can create users."""
        with open("terraform/modules/cognito/main.tf", "r") as f:
            content = f.read()
        assert "admin_create_user_config" in content
        assert "allow_admin_create_user_only" in content

    def test_hipaa_tag(self):
        """Verify HIPAA tag is present."""
        with open("terraform/modules/cognito/main.tf", "r") as f:
            content = f.read()
        assert "HIPAA" in content and "true" in content


class TestDevEnvironmentConfiguration:
    """Test dev environment S3 and Cognito configuration."""

    def test_dev_s3_cognito_exists(self):
        """Verify dev environment s3_cognito.tf exists."""
        path = "terraform/environments/dev/s3_cognito.tf"
        assert os.path.exists(path), f"Missing {path}"

    def test_s3_module_imported(self):
        """Verify S3 module is imported in dev environment."""
        with open("terraform/environments/dev/s3_cognito.tf", "r") as f:
            content = f.read()
        assert 'module "s3"' in content

    def test_cognito_module_imported(self):
        """Verify Cognito module is imported in dev environment."""
        with open("terraform/environments/dev/s3_cognito.tf", "r") as f:
            content = f.read()
        assert 'module "cognito"' in content

    def test_kms_key_reference(self):
        """Verify KMS key is referenced from KMS module."""
        with open("terraform/environments/dev/s3_cognito.tf", "r") as f:
            content = f.read()
        assert "module.kms.s3_key_arn" in content

    def test_vpc_endpoint_reference(self):
        """Verify VPC endpoint is referenced from VPC module."""
        with open("terraform/environments/dev/s3_cognito.tf", "r") as f:
            content = f.read()
        assert "module.vpc.s3_vpc_endpoint_id" in content


class TestTerraformValidation:
    """Test Terraform validation and plan."""

    def test_terraform_validate(self):
        """Verify Terraform configuration is valid."""
        import subprocess
        result = subprocess.run(
            ["terraform", "validate"],
            cwd="terraform/environments/dev",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Terraform validate failed: {result.stderr}"

    def test_terraform_plan_succeeds(self):
        """Verify Terraform plan executes without errors."""
        import subprocess
        result = subprocess.run(
            ["terraform", "plan", "-input=false", "-detailed-exitcode"],
            cwd="terraform/environments/dev",
            capture_output=True,
            text=True
        )
        # Exit code 0 = no changes, 2 = changes to apply (both are success)
        assert result.returncode in [0, 2], \
            f"Terraform plan failed: {result.stderr}"


class TestS3PlanResources:
    """Test S3 resources in Terraform plan."""

    def test_s3_buckets_in_plan(self):
        """Verify all S3 buckets are in the plan."""
        import subprocess
        result = subprocess.run(
            ["terraform", "plan", "-input=false"],
            cwd="terraform/environments/dev",
            capture_output=True,
            text=True
        )
        plan_output = result.stdout

        assert "module.s3.aws_s3_bucket.voice_memos" in plan_output, \
            "Voice memos bucket should be in plan"
        assert "module.s3.aws_s3_bucket.transcripts" in plan_output, \
            "Transcripts bucket should be in plan"
        assert "module.s3.aws_s3_bucket.exports" in plan_output, \
            "Exports bucket should be in plan"


class TestCognitoPlanResources:
    """Test Cognito resources in Terraform plan."""

    def test_cognito_user_pool_in_plan(self):
        """Verify Cognito user pool is in the plan."""
        import subprocess
        result = subprocess.run(
            ["terraform", "plan", "-input=false"],
            cwd="terraform/environments/dev",
            capture_output=True,
            text=True
        )
        plan_output = result.stdout

        assert "module.cognito.aws_cognito_user_pool.therapists" in plan_output, \
            "Cognito user pool should be in plan"

    def test_cognito_app_client_in_plan(self):
        """Verify Cognito app client is in the plan."""
        import subprocess
        result = subprocess.run(
            ["terraform", "plan", "-input=false"],
            cwd="terraform/environments/dev",
            capture_output=True,
            text=True
        )
        plan_output = result.stdout

        assert "module.cognito.aws_cognito_user_pool_client.web_app" in plan_output, \
            "Cognito web app client should be in plan"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
