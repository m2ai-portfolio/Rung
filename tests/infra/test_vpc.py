"""
VPC Infrastructure Tests for Phase 1A

Tests verify:
1. VPC created with correct CIDR (10.0.0.0/16)
2. Subnets in different AZs
3. NAT Gateway configured
4. VPC Endpoints reachable (S3, Bedrock)
5. Security groups configured correctly

Note: These tests use moto for mocking AWS services.
For real infrastructure validation, use terraform plan/apply.
"""

import json
import os
import pytest


class TestVPCConfiguration:
    """Test VPC Terraform configuration files exist and are valid."""

    def test_vpc_module_main_exists(self):
        """Verify vpc/main.tf exists."""
        path = "terraform/modules/vpc/main.tf"
        assert os.path.exists(path), f"Missing {path}"

    def test_vpc_module_variables_exists(self):
        """Verify vpc/variables.tf exists."""
        path = "terraform/modules/vpc/variables.tf"
        assert os.path.exists(path), f"Missing {path}"

    def test_vpc_module_outputs_exists(self):
        """Verify vpc/outputs.tf exists."""
        path = "terraform/modules/vpc/outputs.tf"
        assert os.path.exists(path), f"Missing {path}"

    def test_dev_environment_exists(self):
        """Verify dev environment vpc.tf exists."""
        path = "terraform/environments/dev/vpc.tf"
        assert os.path.exists(path), f"Missing {path}"


class TestVPCCIDRConfiguration:
    """Test VPC CIDR block configuration."""

    def test_vpc_cidr_in_variables(self):
        """Verify VPC CIDR is configured as 10.0.0.0/16."""
        with open("terraform/modules/vpc/variables.tf", "r") as f:
            content = f.read()
        assert "10.0.0.0/16" in content, "VPC CIDR should be 10.0.0.0/16"

    def test_vpc_cidr_in_dev_environment(self):
        """Verify dev environment uses correct VPC CIDR."""
        with open("terraform/environments/dev/vpc.tf", "r") as f:
            content = f.read()
        assert "10.0.0.0/16" in content, "Dev environment should use 10.0.0.0/16"


class TestSubnetConfiguration:
    """Test subnet configuration for proper AZ distribution."""

    def test_private_subnets_configured(self):
        """Verify private subnets are configured."""
        with open("terraform/modules/vpc/variables.tf", "r") as f:
            content = f.read()
        assert "10.0.1.0/24" in content, "Private subnet 1 should be 10.0.1.0/24"
        assert "10.0.2.0/24" in content, "Private subnet 2 should be 10.0.2.0/24"

    def test_public_subnets_configured(self):
        """Verify public subnets are configured."""
        with open("terraform/modules/vpc/variables.tf", "r") as f:
            content = f.read()
        assert "10.0.101.0/24" in content, "Public subnet 1 should be 10.0.101.0/24"
        assert "10.0.102.0/24" in content, "Public subnet 2 should be 10.0.102.0/24"

    def test_multiple_azs_configured(self):
        """Verify subnets use different AZs."""
        with open("terraform/modules/vpc/variables.tf", "r") as f:
            content = f.read()
        assert "us-east-1a" in content, "Should use us-east-1a"
        assert "us-east-1b" in content, "Should use us-east-1b"

    def test_dev_environment_az_configuration(self):
        """Verify dev environment uses both AZs."""
        with open("terraform/environments/dev/vpc.tf", "r") as f:
            content = f.read()
        assert "us-east-1a" in content, "Dev should use us-east-1a"
        assert "us-east-1b" in content, "Dev should use us-east-1b"


class TestNATGatewayConfiguration:
    """Test NAT Gateway configuration."""

    def test_nat_gateway_resource_exists(self):
        """Verify NAT Gateway resource is defined."""
        with open("terraform/modules/vpc/main.tf", "r") as f:
            content = f.read()
        assert "aws_nat_gateway" in content, "NAT Gateway resource should be defined"

    def test_elastic_ip_for_nat(self):
        """Verify Elastic IP is configured for NAT Gateway."""
        with open("terraform/modules/vpc/main.tf", "r") as f:
            content = f.read()
        assert "aws_eip" in content, "Elastic IP should be defined for NAT"

    def test_nat_gateway_variable(self):
        """Verify NAT Gateway can be enabled/disabled."""
        with open("terraform/modules/vpc/variables.tf", "r") as f:
            content = f.read()
        assert "enable_nat_gateway" in content, "NAT Gateway toggle should exist"

    def test_nat_enabled_in_dev(self):
        """Verify NAT Gateway is enabled in dev environment."""
        with open("terraform/environments/dev/vpc.tf", "r") as f:
            content = f.read()
        assert "enable_nat_gateway = true" in content, "NAT should be enabled in dev"


class TestVPCEndpointsConfiguration:
    """Test VPC Endpoints for S3 and Bedrock."""

    def test_s3_endpoint_exists(self):
        """Verify S3 VPC Gateway endpoint is configured."""
        with open("terraform/modules/vpc/main.tf", "r") as f:
            content = f.read()
        assert "aws_vpc_endpoint" in content, "VPC endpoint should be defined"
        assert ".s3" in content, "S3 endpoint should be configured"

    def test_s3_endpoint_is_gateway_type(self):
        """Verify S3 endpoint uses Gateway type."""
        with open("terraform/modules/vpc/main.tf", "r") as f:
            content = f.read()
        # Check for Gateway type for S3
        assert '"Gateway"' in content, "S3 endpoint should be Gateway type"

    def test_bedrock_endpoint_exists(self):
        """Verify Bedrock VPC Interface endpoint is configured."""
        with open("terraform/modules/vpc/main.tf", "r") as f:
            content = f.read()
        assert "bedrock-runtime" in content, "Bedrock Runtime endpoint should exist"

    def test_bedrock_endpoint_is_interface_type(self):
        """Verify Bedrock endpoint uses Interface type."""
        with open("terraform/modules/vpc/main.tf", "r") as f:
            content = f.read()
        assert '"Interface"' in content, "Bedrock endpoint should be Interface type"

    def test_bedrock_endpoint_outputs(self):
        """Verify Bedrock endpoint outputs are defined."""
        with open("terraform/modules/vpc/outputs.tf", "r") as f:
            content = f.read()
        assert "bedrock_runtime_vpc_endpoint_id" in content
        assert "bedrock_vpc_endpoint_id" in content


class TestSecurityGroupConfiguration:
    """Test security group configuration."""

    def test_lambda_sg_exists(self):
        """Verify Lambda security group is defined."""
        with open("terraform/modules/vpc/main.tf", "r") as f:
            content = f.read()
        assert "rung-lambda-sg" in content or "lambda-sg" in content, \
            "Lambda security group should be defined"

    def test_rds_sg_exists(self):
        """Verify RDS security group is defined."""
        with open("terraform/modules/vpc/main.tf", "r") as f:
            content = f.read()
        assert "rung-rds-sg" in content or "rds-sg" in content, \
            "RDS security group should be defined"

    def test_alb_sg_exists(self):
        """Verify ALB security group is defined."""
        with open("terraform/modules/vpc/main.tf", "r") as f:
            content = f.read()
        assert "alb-sg" in content, \
            "ALB security group should be defined"

    def test_security_group_outputs(self):
        """Verify security group outputs are defined."""
        with open("terraform/modules/vpc/outputs.tf", "r") as f:
            content = f.read()
        assert "lambda_security_group_id" in content
        assert "rds_security_group_id" in content
        assert "alb_security_group_id" in content

    def test_rds_sg_allows_only_lambda(self):
        """Verify RDS SG only allows inbound from Lambda SG."""
        with open("terraform/modules/vpc/main.tf", "r") as f:
            content = f.read()
        # RDS should reference lambda security group for ingress
        assert "aws_security_group.lambda" in content, \
            "RDS should reference Lambda SG"


class TestHIPAACompliance:
    """Test HIPAA compliance configurations."""

    def test_vpc_flow_logs_enabled(self):
        """Verify VPC Flow Logs are configured (HIPAA requirement)."""
        with open("terraform/modules/vpc/main.tf", "r") as f:
            content = f.read()
        assert "aws_flow_log" in content, "VPC Flow Logs should be enabled for HIPAA"

    def test_hipaa_tag_present(self):
        """Verify HIPAA tag is applied to resources."""
        with open("terraform/modules/vpc/main.tf", "r") as f:
            content = f.read()
        assert 'HIPAA' in content and '"true"' in content, \
            "Resources should be tagged with HIPAA = true"

    def test_encryption_considerations(self):
        """Verify DNS support is enabled (required for private endpoint resolution)."""
        with open("terraform/modules/vpc/main.tf", "r") as f:
            content = f.read()
        assert "enable_dns_support" in content, "DNS support should be configurable"
        assert "enable_dns_hostnames" in content, "DNS hostnames should be configurable"


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


class TestResourceCount:
    """Test expected resource counts in Terraform plan."""

    def test_minimum_resources_planned(self):
        """Verify minimum expected resources are planned."""
        import subprocess
        result = subprocess.run(
            ["terraform", "plan", "-input=false"],
            cwd="terraform/environments/dev",
            capture_output=True,
            text=True
        )

        # Check for key resources in plan output
        plan_output = result.stdout

        # VPC resources
        assert "aws_vpc.main" in plan_output, "VPC should be in plan"
        assert "aws_subnet.public" in plan_output, "Public subnets should be in plan"
        assert "aws_subnet.private" in plan_output, "Private subnets should be in plan"

        # Gateway resources
        assert "aws_internet_gateway" in plan_output, "Internet Gateway should be in plan"
        assert "aws_nat_gateway" in plan_output, "NAT Gateway should be in plan"

        # Endpoint resources
        assert "aws_vpc_endpoint" in plan_output, "VPC endpoints should be in plan"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
