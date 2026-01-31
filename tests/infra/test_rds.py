"""
RDS Infrastructure Tests for Phase 1B

Tests verify:
1. RDS instance is configured for encryption
2. Multi-AZ is enabled
3. Security group allows only Lambda access
4. KMS keys created with correct policies
5. Secrets Manager integration

Note: These tests verify Terraform configuration files.
For real infrastructure validation, use terraform plan/apply.
"""

import json
import os
import pytest


class TestKMSConfiguration:
    """Test KMS module configuration files."""

    def test_kms_module_main_exists(self):
        """Verify kms/main.tf exists."""
        path = "terraform/modules/kms/main.tf"
        assert os.path.exists(path), f"Missing {path}"

    def test_kms_module_variables_exists(self):
        """Verify kms/variables.tf exists."""
        path = "terraform/modules/kms/variables.tf"
        assert os.path.exists(path), f"Missing {path}"

    def test_kms_module_outputs_exists(self):
        """Verify kms/outputs.tf exists."""
        path = "terraform/modules/kms/outputs.tf"
        assert os.path.exists(path), f"Missing {path}"


class TestKMSKeyHierarchy:
    """Test KMS key hierarchy configuration."""

    def test_master_key_defined(self):
        """Verify master CMK is defined."""
        with open("terraform/modules/kms/main.tf", "r") as f:
            content = f.read()
        assert 'aws_kms_key" "master"' in content, "Master key should be defined"

    def test_rds_key_defined(self):
        """Verify RDS key is defined."""
        with open("terraform/modules/kms/main.tf", "r") as f:
            content = f.read()
        assert 'aws_kms_key" "rds"' in content, "RDS key should be defined"

    def test_s3_key_defined(self):
        """Verify S3 key is defined."""
        with open("terraform/modules/kms/main.tf", "r") as f:
            content = f.read()
        assert 'aws_kms_key" "s3"' in content, "S3 key should be defined"

    def test_field_key_defined(self):
        """Verify field-level encryption key is defined."""
        with open("terraform/modules/kms/main.tf", "r") as f:
            content = f.read()
        assert 'aws_kms_key" "field"' in content, "Field key should be defined"

    def test_key_rotation_enabled(self):
        """Verify key rotation is enabled."""
        with open("terraform/modules/kms/main.tf", "r") as f:
            content = f.read()
        assert "enable_key_rotation" in content, "Key rotation should be configured"

    def test_kms_aliases_defined(self):
        """Verify KMS aliases are defined for all keys."""
        with open("terraform/modules/kms/main.tf", "r") as f:
            content = f.read()
        assert "aws_kms_alias" in content, "KMS aliases should be defined"
        assert "rung-dev-master-key" in content or "master-key" in content
        assert "rung-dev-rds-key" in content or "rds-key" in content
        assert "rung-dev-s3-key" in content or "s3-key" in content

    def test_kms_key_outputs(self):
        """Verify KMS key outputs are defined."""
        with open("terraform/modules/kms/outputs.tf", "r") as f:
            content = f.read()
        assert "master_key_arn" in content
        assert "rds_key_arn" in content
        assert "s3_key_arn" in content
        assert "field_key_arn" in content


class TestRDSConfiguration:
    """Test RDS module configuration files."""

    def test_rds_module_main_exists(self):
        """Verify rds/main.tf exists."""
        path = "terraform/modules/rds/main.tf"
        assert os.path.exists(path), f"Missing {path}"

    def test_rds_module_variables_exists(self):
        """Verify rds/variables.tf exists."""
        path = "terraform/modules/rds/variables.tf"
        assert os.path.exists(path), f"Missing {path}"

    def test_rds_module_outputs_exists(self):
        """Verify rds/outputs.tf exists."""
        path = "terraform/modules/rds/outputs.tf"
        assert os.path.exists(path), f"Missing {path}"

    def test_dev_environment_rds_exists(self):
        """Verify dev environment rds.tf exists."""
        path = "terraform/environments/dev/rds.tf"
        assert os.path.exists(path), f"Missing {path}"


class TestRDSInstanceConfiguration:
    """Test RDS instance configuration."""

    def test_postgresql_15_configured(self):
        """Verify PostgreSQL 15 is configured."""
        with open("terraform/modules/rds/variables.tf", "r") as f:
            content = f.read()
        assert '"15"' in content, "PostgreSQL 15 should be default"

    def test_instance_class_configured(self):
        """Verify instance class is db.r6g.large."""
        with open("terraform/modules/rds/variables.tf", "r") as f:
            content = f.read()
        assert "db.r6g.large" in content, "Instance class should be db.r6g.large"

    def test_database_name_rung(self):
        """Verify database name is rung."""
        with open("terraform/modules/rds/variables.tf", "r") as f:
            content = f.read()
        assert '"rung"' in content, "Database name should be rung"

    def test_dev_environment_uses_correct_config(self):
        """Verify dev environment uses correct database name."""
        with open("terraform/environments/dev/rds.tf", "r") as f:
            content = f.read()
        assert 'database_name' in content and 'rung' in content


class TestRDSEncryption:
    """Test RDS encryption configuration."""

    def test_storage_encrypted(self):
        """Verify storage encryption is enabled."""
        with open("terraform/modules/rds/main.tf", "r") as f:
            content = f.read()
        assert "storage_encrypted = true" in content, "Storage encryption must be enabled"

    def test_kms_key_reference(self):
        """Verify KMS key is referenced for encryption."""
        with open("terraform/modules/rds/main.tf", "r") as f:
            content = f.read()
        assert "kms_key_id" in content, "KMS key should be referenced"

    def test_encryption_output(self):
        """Verify encryption status is output."""
        with open("terraform/modules/rds/outputs.tf", "r") as f:
            content = f.read()
        assert "db_instance_encrypted" in content or "storage_encrypted" in content


class TestRDSMultiAZ:
    """Test Multi-AZ configuration."""

    def test_multi_az_variable(self):
        """Verify Multi-AZ variable exists."""
        with open("terraform/modules/rds/variables.tf", "r") as f:
            content = f.read()
        assert "multi_az" in content, "Multi-AZ variable should exist"

    def test_multi_az_default_true(self):
        """Verify Multi-AZ defaults to true."""
        with open("terraform/modules/rds/variables.tf", "r") as f:
            content = f.read()
        # Check that multi_az default is true
        assert "default     = true" in content, "Multi-AZ should default to true"

    def test_multi_az_in_instance(self):
        """Verify Multi-AZ is set on instance."""
        with open("terraform/modules/rds/main.tf", "r") as f:
            content = f.read()
        assert "multi_az = var.multi_az" in content, "Multi-AZ should be set on instance"

    def test_multi_az_output(self):
        """Verify Multi-AZ status is output."""
        with open("terraform/modules/rds/outputs.tf", "r") as f:
            content = f.read()
        assert "multi_az" in content, "Multi-AZ status should be output"


class TestRDSSecretsManager:
    """Test Secrets Manager integration."""

    def test_secrets_manager_secret(self):
        """Verify Secrets Manager secret is created."""
        with open("terraform/modules/rds/main.tf", "r") as f:
            content = f.read()
        assert "aws_secretsmanager_secret" in content, "Secrets Manager secret should be created"

    def test_secrets_manager_credentials(self):
        """Verify credentials are stored in Secrets Manager."""
        with open("terraform/modules/rds/main.tf", "r") as f:
            content = f.read()
        assert "aws_secretsmanager_secret_version" in content
        assert "username" in content
        assert "password" in content

    def test_random_password(self):
        """Verify random password is generated."""
        with open("terraform/modules/rds/main.tf", "r") as f:
            content = f.read()
        assert "random_password" in content, "Random password should be generated"

    def test_secrets_kms_encrypted(self):
        """Verify secrets are encrypted with KMS."""
        with open("terraform/modules/rds/main.tf", "r") as f:
            content = f.read()
        assert "kms_key_id" in content, "Secrets should use KMS encryption"


class TestRDSNetworking:
    """Test RDS networking configuration."""

    def test_subnet_group(self):
        """Verify DB subnet group is created."""
        with open("terraform/modules/rds/main.tf", "r") as f:
            content = f.read()
        assert "aws_db_subnet_group" in content, "DB subnet group should be created"

    def test_not_publicly_accessible(self):
        """Verify RDS is not publicly accessible."""
        with open("terraform/modules/rds/main.tf", "r") as f:
            content = f.read()
        assert "publicly_accessible    = false" in content, "RDS must not be publicly accessible"

    def test_security_group_variable(self):
        """Verify security group variable exists."""
        with open("terraform/modules/rds/variables.tf", "r") as f:
            content = f.read()
        assert "security_group_ids" in content, "Security group variable should exist"


class TestRDSHIPAACompliance:
    """Test HIPAA compliance configurations."""

    def test_backup_retention(self):
        """Verify backup retention meets HIPAA requirements."""
        with open("terraform/modules/rds/variables.tf", "r") as f:
            content = f.read()
        # HIPAA requires minimum 30 days
        assert "backup_retention_period" in content
        assert "35" in content or "30" in content, "Backup retention should be at least 30 days"

    def test_ssl_enforcement(self):
        """Verify SSL is enforced."""
        with open("terraform/modules/rds/main.tf", "r") as f:
            content = f.read()
        assert "rds.force_ssl" in content, "SSL should be enforced"

    def test_logging_enabled(self):
        """Verify database logging is enabled."""
        with open("terraform/modules/rds/main.tf", "r") as f:
            content = f.read()
        assert "log_connections" in content
        assert "log_disconnections" in content

    def test_hipaa_tag(self):
        """Verify HIPAA tag is present."""
        with open("terraform/modules/rds/main.tf", "r") as f:
            content = f.read()
        assert "HIPAA" in content and "true" in content

    def test_deletion_protection(self):
        """Verify deletion protection variable exists."""
        with open("terraform/modules/rds/variables.tf", "r") as f:
            content = f.read()
        assert "deletion_protection" in content


class TestRDSMonitoring:
    """Test RDS monitoring configuration."""

    def test_performance_insights(self):
        """Verify Performance Insights is configured."""
        with open("terraform/modules/rds/main.tf", "r") as f:
            content = f.read()
        assert "performance_insights_enabled" in content

    def test_enhanced_monitoring(self):
        """Verify enhanced monitoring is configured."""
        with open("terraform/modules/rds/main.tf", "r") as f:
            content = f.read()
        assert "monitoring_interval" in content
        assert "monitoring_role_arn" in content

    def test_cloudwatch_alarms(self):
        """Verify CloudWatch alarms are defined."""
        with open("terraform/modules/rds/main.tf", "r") as f:
            content = f.read()
        assert "aws_cloudwatch_metric_alarm" in content


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


class TestKMSPlanResources:
    """Test KMS resources in Terraform plan."""

    def test_kms_keys_in_plan(self):
        """Verify all KMS keys are in the plan."""
        import subprocess
        result = subprocess.run(
            ["terraform", "plan", "-input=false"],
            cwd="terraform/environments/dev",
            capture_output=True,
            text=True
        )
        plan_output = result.stdout

        assert "module.kms.aws_kms_key.master" in plan_output, "Master key should be in plan"
        assert "module.kms.aws_kms_key.rds" in plan_output, "RDS key should be in plan"
        assert "module.kms.aws_kms_key.s3" in plan_output, "S3 key should be in plan"
        assert "module.kms.aws_kms_key.field" in plan_output, "Field key should be in plan"


class TestRDSPlanResources:
    """Test RDS resources in Terraform plan."""

    def test_rds_instance_in_plan(self):
        """Verify RDS instance is in the plan."""
        import subprocess
        result = subprocess.run(
            ["terraform", "plan", "-input=false"],
            cwd="terraform/environments/dev",
            capture_output=True,
            text=True
        )
        plan_output = result.stdout

        assert "module.rds.aws_db_instance.main" in plan_output, "RDS instance should be in plan"

    def test_secrets_manager_in_plan(self):
        """Verify Secrets Manager resources are in the plan."""
        import subprocess
        result = subprocess.run(
            ["terraform", "plan", "-input=false"],
            cwd="terraform/environments/dev",
            capture_output=True,
            text=True
        )
        plan_output = result.stdout

        assert "aws_secretsmanager_secret" in plan_output, "Secrets Manager should be in plan"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
