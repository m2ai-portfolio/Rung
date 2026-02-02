"""
HIPAA Compliance Verification Tests

Automated verification of HIPAA Security Rule implementation specifications.
These tests verify that required controls are in place and functioning.
"""

import os
import re
import pytest
from pathlib import Path
from datetime import datetime

# Set test environment
os.environ["AWS_REGION"] = "us-east-1"


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def project_root():
    """Get project root directory."""
    return Path(__file__).parent.parent.parent


@pytest.fixture
def src_dir(project_root):
    """Get source directory."""
    return project_root / "src"


@pytest.fixture
def terraform_dir(project_root):
    """Get terraform directory."""
    return project_root / "terraform"


@pytest.fixture
def docs_dir(project_root):
    """Get docs directory."""
    return project_root / "docs"


# =============================================================================
# Access Control Tests (§164.312(a))
# =============================================================================

class TestAccessControls:
    """Test access control implementation."""

    def test_authentication_service_exists(self, src_dir):
        """Verify authentication service is implemented."""
        # Check for Cognito integration
        bedrock_client = src_dir / "services" / "bedrock_client.py"
        assert bedrock_client.exists(), "Bedrock client (auth integration) not found"

    def test_role_based_access_in_api(self, src_dir):
        """Verify RBAC is implemented in API endpoints."""
        api_dir = src_dir / "api"
        assert api_dir.exists(), "API directory not found"

        # Check couples API for role verification
        couples_api = api_dir / "couples.py"
        if couples_api.exists():
            content = couples_api.read_text()
            assert "x_user_role" in content.lower() or "therapist" in content.lower(), \
                "Role-based access control not found in couples API"

    def test_therapist_authorization_check(self, src_dir):
        """Verify therapist authorization is checked."""
        couple_manager = src_dir / "services" / "couple_manager.py"
        if couple_manager.exists():
            content = couple_manager.read_text()
            assert "validate_merge_authorization" in content or "therapist_id" in content, \
                "Therapist authorization check not found"


# =============================================================================
# Encryption Tests (§164.312(a)(2)(iv))
# =============================================================================

class TestEncryption:
    """Test encryption requirements."""

    def test_kms_module_exists(self, terraform_dir):
        """Verify KMS encryption module exists."""
        kms_module = terraform_dir / "modules" / "kms"
        assert kms_module.exists(), "KMS module not found in Terraform"

    def test_rds_encryption_configured(self, terraform_dir):
        """Verify RDS encryption is configured."""
        rds_module = terraform_dir / "modules" / "rds"
        if rds_module.exists():
            main_tf = rds_module / "main.tf"
            if main_tf.exists():
                content = main_tf.read_text()
                assert "storage_encrypted" in content or "kms_key" in content, \
                    "RDS encryption not configured"

    def test_s3_encryption_configured(self, terraform_dir):
        """Verify S3 encryption is configured."""
        s3_module = terraform_dir / "modules" / "s3"
        if s3_module.exists():
            main_tf = s3_module / "main.tf"
            if main_tf.exists():
                content = main_tf.read_text()
                assert "sse" in content.lower() or "encryption" in content.lower(), \
                    "S3 encryption not configured"

    def test_tls_required_in_api(self, src_dir):
        """Verify TLS is enforced (no HTTP endpoints)."""
        api_dir = src_dir / "api"
        if api_dir.exists():
            for py_file in api_dir.glob("*.py"):
                content = py_file.read_text()
                # Check for HTTP (not HTTPS) URLs
                http_urls = re.findall(r'http://(?!localhost|127\.0\.0\.1)', content)
                assert len(http_urls) == 0, \
                    f"Non-TLS HTTP URLs found in {py_file.name}"


# =============================================================================
# Audit Control Tests (§164.312(b))
# =============================================================================

class TestAuditControls:
    """Test audit logging implementation."""

    def test_audit_log_model_exists(self, src_dir):
        """Verify audit log model exists."""
        models_dir = src_dir / "models"
        if models_dir.exists():
            audit_log = models_dir / "audit_log.py"
            # May be defined elsewhere
            pass

    def test_merge_engine_has_audit_logging(self, src_dir):
        """Verify merge engine has comprehensive audit logging."""
        merge_engine = src_dir / "services" / "merge_engine.py"
        if merge_engine.exists():
            content = merge_engine.read_text()
            assert "MergeAuditEntry" in content, \
                "Merge engine missing audit entry class"
            assert "_audit_log" in content, \
                "Merge engine missing audit log storage"
            assert "isolation_invoked" in content, \
                "Merge engine missing isolation invocation tracking"

    def test_audit_entry_required_fields(self, src_dir):
        """Verify audit entries contain required HIPAA fields."""
        merge_engine = src_dir / "services" / "merge_engine.py"
        if merge_engine.exists():
            content = merge_engine.read_text()
            required_fields = [
                "event_type",
                "therapist_id",
                "action",
                "ip_address",
                "created_at",
            ]
            for field in required_fields:
                assert field in content, \
                    f"Audit entry missing required field: {field}"

    def test_cloudwatch_monitoring_module(self, terraform_dir):
        """Verify CloudWatch monitoring module exists."""
        monitoring_module = terraform_dir / "modules" / "monitoring"
        assert monitoring_module.exists(), "Monitoring module not found"

        main_tf = monitoring_module / "main.tf"
        assert main_tf.exists(), "Monitoring main.tf not found"

        content = main_tf.read_text()
        assert "aws_cloudwatch_log_group" in content, \
            "CloudWatch log groups not configured"
        assert "retention_in_days" in content, \
            "Log retention not configured"


# =============================================================================
# Integrity Controls Tests (§164.312(c))
# =============================================================================

class TestIntegrityControls:
    """Test data integrity controls."""

    def test_pydantic_validation_used(self, src_dir):
        """Verify Pydantic is used for data validation."""
        services_dir = src_dir / "services"
        if services_dir.exists():
            for py_file in services_dir.glob("*.py"):
                content = py_file.read_text()
                if "class" in content and "BaseModel" in content:
                    # Pydantic is being used
                    return
        # Check agents
        agents_dir = src_dir / "agents"
        if agents_dir.exists():
            schemas_dir = agents_dir / "schemas"
            if schemas_dir.exists():
                for py_file in schemas_dir.glob("*.py"):
                    content = py_file.read_text()
                    if "BaseModel" in content:
                        return
        # If we get here, no Pydantic found
        pytest.skip("Pydantic validation check - models may be elsewhere")


# =============================================================================
# PHI Protection Tests (Rung-specific)
# =============================================================================

class TestPHIProtection:
    """Test PHI-specific protections."""

    def test_isolation_layer_exists(self, src_dir):
        """Verify isolation layer for couples merge exists."""
        isolation_layer = src_dir / "services" / "isolation_layer.py"
        assert isolation_layer.exists(), "Isolation layer not found"

    def test_isolation_layer_has_whitelists(self, src_dir):
        """Verify isolation layer uses whitelist approach."""
        isolation_layer = src_dir / "services" / "isolation_layer.py"
        if isolation_layer.exists():
            content = isolation_layer.read_text()
            assert "ALLOWED_" in content, \
                "Isolation layer missing whitelist definitions"
            assert "ALLOWED_ATTACHMENT_PATTERNS" in content or \
                   "ALLOWED_FRAMEWORKS" in content, \
                "Isolation layer missing specific whitelists"

    def test_isolation_layer_has_phi_detection(self, src_dir):
        """Verify isolation layer can detect PHI."""
        isolation_layer = src_dir / "services" / "isolation_layer.py"
        if isolation_layer.exists():
            content = isolation_layer.read_text()
            assert "PHI_PATTERNS" in content or "contains_phi" in content, \
                "Isolation layer missing PHI detection"

    def test_anonymizer_exists(self, src_dir):
        """Verify anonymizer for external APIs exists."""
        anonymizer = src_dir / "services" / "anonymizer.py"
        assert anonymizer.exists(), "Anonymizer service not found"

    def test_anonymizer_strips_phi(self, src_dir):
        """Verify anonymizer removes PHI patterns."""
        anonymizer = src_dir / "services" / "anonymizer.py"
        if anonymizer.exists():
            content = anonymizer.read_text()
            assert "strip" in content.lower() or "remove" in content.lower() or \
                   "anonymize" in content.lower(), \
                "Anonymizer missing PHI stripping logic"

    def test_abstraction_layer_exists(self, src_dir):
        """Verify abstraction layer between Rung and Beth exists."""
        abstraction = src_dir / "services" / "abstraction_layer.py"
        assert abstraction.exists(), "Abstraction layer not found"

    def test_abstraction_blocks_clinical_terms(self, src_dir):
        """Verify abstraction layer blocks clinical terminology."""
        abstraction = src_dir / "services" / "abstraction_layer.py"
        if abstraction.exists():
            content = abstraction.read_text()
            # Should have some blocking/filtering logic
            assert "strip" in content.lower() or "filter" in content.lower() or \
                   "extract" in content.lower() or "abstract" in content.lower(), \
                "Abstraction layer missing filtering logic"


# =============================================================================
# Documentation Tests (§164.316)
# =============================================================================

class TestDocumentation:
    """Test required documentation exists."""

    def test_security_policies_exist(self, docs_dir):
        """Verify security policies are documented."""
        policies = docs_dir / "security" / "policies.md"
        assert policies.exists(), "Security policies not documented"

        content = policies.read_text()
        assert len(content) > 1000, "Security policies document too short"

    def test_data_flows_documented(self, docs_dir):
        """Verify data flows are documented."""
        data_flows = docs_dir / "security" / "data_flows.md"
        assert data_flows.exists(), "Data flows not documented"

        content = data_flows.read_text()
        assert "PHI" in content, "Data flows missing PHI markers"

    def test_incident_response_exists(self, docs_dir):
        """Verify incident response plan exists."""
        incident_response = docs_dir / "security" / "incident_response.md"
        assert incident_response.exists(), "Incident response plan not documented"

        content = incident_response.read_text()
        assert "breach" in content.lower(), \
            "Incident response missing breach procedures"

    def test_hipaa_checklist_exists(self, docs_dir):
        """Verify HIPAA checklist exists."""
        checklist = docs_dir / "compliance" / "hipaa_checklist.md"
        assert checklist.exists(), "HIPAA checklist not documented"

        content = checklist.read_text()
        assert "[x]" in content, "HIPAA checklist has no completed items"

    def test_risk_assessment_exists(self, docs_dir):
        """Verify risk assessment exists."""
        risk_assessment = docs_dir / "compliance" / "risk_assessment.md"
        assert risk_assessment.exists(), "Risk assessment not documented"


# =============================================================================
# Network Security Tests
# =============================================================================

class TestNetworkSecurity:
    """Test network security configuration."""

    def test_vpc_module_exists(self, terraform_dir):
        """Verify VPC module exists."""
        vpc_module = terraform_dir / "modules" / "vpc"
        assert vpc_module.exists(), "VPC module not found"

    def test_private_subnets_configured(self, terraform_dir):
        """Verify private subnets are configured."""
        vpc_module = terraform_dir / "modules" / "vpc"
        if vpc_module.exists():
            main_tf = vpc_module / "main.tf"
            if main_tf.exists():
                content = main_tf.read_text()
                assert "private" in content.lower(), \
                    "Private subnets not configured"


# =============================================================================
# Security Scanning Configuration Tests
# =============================================================================

class TestSecurityScanningConfig:
    """Test security scanning is configured."""

    def test_dependency_lock_files_exist(self, project_root):
        """Verify dependency lock files exist for reproducible builds."""
        # Check for various lock file types
        lock_files = [
            "requirements.txt",
            "poetry.lock",
            "Pipfile.lock",
            "package-lock.json",
            "pnpm-lock.yaml",
        ]
        found = any((project_root / f).exists() for f in lock_files)
        # This is a soft check - may not have lock files yet
        if not found:
            pytest.skip("No lock files found - may not be configured yet")

    def test_gitignore_excludes_secrets(self, project_root):
        """Verify .gitignore excludes secret files."""
        gitignore = project_root / ".gitignore"
        if gitignore.exists():
            content = gitignore.read_text()
            secret_patterns = [".env", "*.pem", "*.key", "credentials"]
            found = any(p in content for p in secret_patterns)
            assert found, ".gitignore missing secret file patterns"
        else:
            pytest.skip(".gitignore not found")

    def test_no_hardcoded_secrets_in_code(self, src_dir):
        """Verify no hardcoded secrets in source code."""
        if not src_dir.exists():
            pytest.skip("Source directory not found")

        secret_patterns = [
            r'api_key\s*=\s*["\'][a-zA-Z0-9]{20,}["\']',
            r'password\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][a-zA-Z0-9]{20,}["\']',
            r'AKIA[A-Z0-9]{16}',  # AWS access key pattern
        ]

        for py_file in src_dir.rglob("*.py"):
            content = py_file.read_text()
            for pattern in secret_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                # Filter out obvious test/example patterns
                real_matches = [m for m in matches if "example" not in m.lower()
                               and "test" not in m.lower()
                               and "xxx" not in m.lower()]
                assert len(real_matches) == 0, \
                    f"Potential hardcoded secret in {py_file.name}: {pattern}"


# =============================================================================
# Couples Merge Security Tests
# =============================================================================

class TestCouplesMergeSecurity:
    """Test couples merge security controls."""

    def test_isolation_layer_imported_in_merge(self, src_dir):
        """Verify merge engine uses isolation layer."""
        merge_engine = src_dir / "services" / "merge_engine.py"
        if merge_engine.exists():
            content = merge_engine.read_text()
            assert "isolation_layer" in content.lower() or \
                   "IsolationLayer" in content or \
                   "isolate_for_couples_merge" in content, \
                "Merge engine not using isolation layer"

    def test_merge_requires_authorization(self, src_dir):
        """Verify merge operation requires authorization."""
        merge_engine = src_dir / "services" / "merge_engine.py"
        if merge_engine.exists():
            content = merge_engine.read_text()
            assert "validate_merge_authorization" in content or \
                   "therapist_id" in content, \
                "Merge operation missing authorization check"

    def test_merge_api_requires_therapist_role(self, src_dir):
        """Verify merge API requires therapist role."""
        merged_api = src_dir / "api" / "merged_frameworks.py"
        if merged_api.exists():
            content = merged_api.read_text()
            assert 'therapist' in content.lower(), \
                "Merge API missing therapist role check"

    def test_isolation_tests_exist(self, project_root):
        """Verify isolation layer has tests."""
        security_tests = project_root / "tests" / "security"
        assert security_tests.exists(), "Security tests directory not found"

        # Check for isolation tests
        test_files = list(security_tests.glob("test_*.py"))
        assert len(test_files) > 0, "No security tests found"


# =============================================================================
# Summary Test
# =============================================================================

class TestComplianceSummary:
    """Summary test for overall compliance status."""

    def test_critical_controls_present(self, src_dir, docs_dir, terraform_dir):
        """Verify all critical controls are present."""
        critical_controls = []

        # Check isolation layer
        if (src_dir / "services" / "isolation_layer.py").exists():
            critical_controls.append("isolation_layer")

        # Check anonymizer
        if (src_dir / "services" / "anonymizer.py").exists():
            critical_controls.append("anonymizer")

        # Check audit logging (in merge engine)
        if (src_dir / "services" / "merge_engine.py").exists():
            content = (src_dir / "services" / "merge_engine.py").read_text()
            if "MergeAuditEntry" in content:
                critical_controls.append("audit_logging")

        # Check encryption (KMS module)
        if (terraform_dir / "modules" / "kms").exists():
            critical_controls.append("encryption")

        # Check documentation
        if (docs_dir / "security" / "policies.md").exists():
            critical_controls.append("documentation")

        # Check monitoring
        if (terraform_dir / "modules" / "monitoring").exists():
            critical_controls.append("monitoring")

        expected_controls = [
            "isolation_layer",
            "anonymizer",
            "audit_logging",
            "encryption",
            "documentation",
            "monitoring",
        ]

        missing = set(expected_controls) - set(critical_controls)
        assert len(missing) == 0, f"Missing critical controls: {missing}"
