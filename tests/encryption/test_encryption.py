"""
Encryption Service Tests

Tests for both DevEncryptor and FieldEncryptor (KMS mocked),
the get_encryptor factory, and NotesProcessor integration.
"""

import os
import struct
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

os.environ["AWS_REGION"] = "us-east-1"

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from src.services.encryption import (
    DevEncryptor,
    FieldEncryptor,
    get_encryptor,
    _NONCE_LENGTH,
    _KEY_LENGTH_FMT,
    _KEY_LENGTH_SIZE,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def dev_encryptor():
    """DevEncryptor with an explicit key."""
    key = Fernet.generate_key()
    return DevEncryptor(key=key)


@pytest.fixture
def sample_context():
    """Sample encryption context."""
    return {"therapist_id": str(uuid4()), "client_id": str(uuid4())}


@pytest.fixture
def different_context():
    """A second, distinct encryption context."""
    return {"therapist_id": str(uuid4()), "client_id": str(uuid4())}


@pytest.fixture
def mock_kms_client():
    """
    Build a mock boto3 KMS client whose generate_data_key / decrypt
    produce real AES-256 key material so that the AES-GCM round-trip
    works end-to-end.
    """
    # Generate a real 32-byte data key for testing
    real_key = os.urandom(32)
    # Simulate an "encrypted" version (just tag it so we can recognize it)
    encrypted_key = b"KMS_ENCRYPTED:" + real_key

    mock_client = MagicMock()
    mock_client.generate_data_key.return_value = {
        "Plaintext": real_key,
        "CiphertextBlob": encrypted_key,
        "KeyId": "arn:aws:kms:us-east-1:123456789012:key/test-key-id",
    }
    mock_client.decrypt.return_value = {
        "Plaintext": real_key,
        "KeyId": "arn:aws:kms:us-east-1:123456789012:key/test-key-id",
    }
    return mock_client


@pytest.fixture
def field_encryptor(mock_kms_client):
    """FieldEncryptor wired to a mock KMS client."""
    enc = FieldEncryptor(kms_key_id="alias/rung-phi", region="us-east-1")
    enc._kms = mock_kms_client
    return enc


# =============================================================================
# DevEncryptor Tests
# =============================================================================

class TestDevEncryptor:
    """Tests for the local-development encryptor."""

    def test_dev_encrypt_decrypt_roundtrip(self, dev_encryptor, sample_context):
        """Encrypt then decrypt should return the original text."""
        plaintext = "Client expressed anxiety about upcoming event."
        encrypted = dev_encryptor.encrypt(plaintext, sample_context)
        decrypted = dev_encryptor.decrypt(encrypted, sample_context)
        assert decrypted == plaintext

    def test_dev_encrypt_produces_bytes(self, dev_encryptor, sample_context):
        """Encrypted output must be bytes, not str."""
        encrypted = dev_encryptor.encrypt("hello", sample_context)
        assert isinstance(encrypted, bytes)

    def test_dev_different_contexts_produce_different_ciphertext(
        self, dev_encryptor, sample_context, different_context
    ):
        """Same plaintext with different contexts yields different ciphertext."""
        plaintext = "Identical session notes for both clients."
        ct_a = dev_encryptor.encrypt(plaintext, sample_context)
        ct_b = dev_encryptor.encrypt(plaintext, different_context)
        assert ct_a != ct_b

    def test_dev_context_mismatch_raises(self, dev_encryptor, sample_context, different_context):
        """Decrypting with a wrong context raises ValueError."""
        encrypted = dev_encryptor.encrypt("secret", sample_context)
        with pytest.raises(ValueError, match="context mismatch"):
            dev_encryptor.decrypt(encrypted, different_context)

    def test_dev_empty_context(self, dev_encryptor):
        """Empty context dict should work for both encrypt and decrypt."""
        ct = dev_encryptor.encrypt("test", {})
        assert dev_encryptor.decrypt(ct, {}) == "test"

    def test_dev_unicode_roundtrip(self, dev_encryptor, sample_context):
        """Non-ASCII characters survive the round-trip."""
        plaintext = "Patient noted feeling 'overwhelmed' and used emoji."
        ct = dev_encryptor.encrypt(plaintext, sample_context)
        assert dev_encryptor.decrypt(ct, sample_context) == plaintext

    def test_dev_env_key(self):
        """DevEncryptor picks up RUNG_DEV_ENCRYPTION_KEY from env."""
        key = Fernet.generate_key()
        with patch.dict(os.environ, {"RUNG_DEV_ENCRYPTION_KEY": key.decode()}):
            enc = DevEncryptor()
            ct = enc.encrypt("env-key-test", {})
            assert enc.decrypt(ct, {}) == "env-key-test"


# =============================================================================
# FieldEncryptor Tests
# =============================================================================

class TestFieldEncryptor:
    """Tests for the KMS-backed encryptor (KMS calls mocked)."""

    def test_field_encryptor_encrypt_calls_kms(
        self, field_encryptor, mock_kms_client, sample_context
    ):
        """encrypt() must call KMS GenerateDataKey."""
        field_encryptor.encrypt("notes text", sample_context)

        mock_kms_client.generate_data_key.assert_called_once_with(
            KeyId="alias/rung-phi",
            KeySpec="AES_256",
            EncryptionContext=sample_context,
        )

    def test_field_encryptor_decrypt_calls_kms(
        self, field_encryptor, mock_kms_client, sample_context
    ):
        """decrypt() must call KMS Decrypt to unwrap the data key."""
        ct = field_encryptor.encrypt("notes text", sample_context)

        # Reset call tracking so we only see decrypt calls
        mock_kms_client.decrypt.reset_mock()

        field_encryptor.decrypt(ct, sample_context)

        assert mock_kms_client.decrypt.call_count == 1
        call_kwargs = mock_kms_client.decrypt.call_args[1]
        assert call_kwargs["EncryptionContext"] == sample_context

    def test_field_encryptor_roundtrip_with_mock_kms(
        self, field_encryptor, sample_context
    ):
        """Full encrypt-then-decrypt round-trip with mocked KMS."""
        plaintext = "Client showed progress with CBT reframing techniques."
        ct = field_encryptor.encrypt(plaintext, sample_context)
        result = field_encryptor.decrypt(ct, sample_context)
        assert result == plaintext

    def test_field_encryptor_wire_format_structure(
        self, field_encryptor, sample_context
    ):
        """Verify wire format: [key_len][encrypted_key][nonce][ct+tag]."""
        ct = field_encryptor.encrypt("test", sample_context)

        # Parse key length
        (key_len,) = struct.unpack_from(_KEY_LENGTH_FMT, ct, 0)
        assert key_len > 0

        # Total must be: 2 + key_len + 12 + (>= 16 bytes for tag + at least 1 byte ct)
        min_length = _KEY_LENGTH_SIZE + key_len + _NONCE_LENGTH + 16 + len("test".encode())
        assert len(ct) >= min_length

    def test_field_encryptor_produces_bytes(self, field_encryptor, sample_context):
        """Encrypted output must be bytes."""
        ct = field_encryptor.encrypt("data", sample_context)
        assert isinstance(ct, bytes)

    def test_field_encryptor_decrypt_short_ciphertext_raises(self, field_encryptor):
        """Decrypting truncated data should raise ValueError."""
        with pytest.raises(ValueError, match="too short"):
            field_encryptor.decrypt(b"\x00", {})

    def test_field_encryptor_decrypt_bad_key_length_raises(self, field_encryptor):
        """Ciphertext claiming a huge key length should raise ValueError."""
        # Claim key_len = 60000 but only provide a few bytes
        bad = struct.pack(_KEY_LENGTH_FMT, 60000) + b"\x00" * 20
        with pytest.raises(ValueError, match="too short"):
            field_encryptor.decrypt(bad, {})


# =============================================================================
# Factory Tests
# =============================================================================

class TestGetEncryptor:
    """Tests for the get_encryptor() factory function."""

    def test_get_encryptor_returns_dev_by_default(self):
        """Without production env vars, factory returns DevEncryptor."""
        env_overrides = {
            "RUNG_ENV": "development",
        }
        with patch.dict(os.environ, env_overrides, clear=False):
            # Remove FIELD_ENCRYPTION_KEY_ID if set
            os.environ.pop("FIELD_ENCRYPTION_KEY_ID", None)
            enc = get_encryptor()
            assert isinstance(enc, DevEncryptor)

    def test_get_encryptor_returns_field_when_production(self):
        """In production with a KMS key ID, factory returns FieldEncryptor."""
        env_overrides = {
            "RUNG_ENV": "production",
            "FIELD_ENCRYPTION_KEY_ID": "arn:aws:kms:us-east-1:123456789012:key/test",
            "AWS_REGION": "us-east-1",
        }
        with patch.dict(os.environ, env_overrides, clear=False):
            with patch("src.services.encryption.boto3") as mock_boto3:
                mock_boto3.client.return_value = MagicMock()
                enc = get_encryptor()
                assert isinstance(enc, FieldEncryptor)

    def test_get_encryptor_returns_dev_when_production_but_no_key(self):
        """Production env without a KMS key ID falls back to DevEncryptor."""
        env_overrides = {"RUNG_ENV": "production"}
        with patch.dict(os.environ, env_overrides, clear=False):
            os.environ.pop("FIELD_ENCRYPTION_KEY_ID", None)
            enc = get_encryptor()
            assert isinstance(enc, DevEncryptor)


# =============================================================================
# NotesProcessor Integration Tests
# =============================================================================

class TestNotesProcessorEncryption:
    """Verify NotesProcessor delegates to the injected encryptor."""

    def test_notes_processor_uses_encryptor(self, dev_encryptor):
        """NotesProcessor.encrypt_notes / decrypt_notes use the injected encryptor."""
        from src.services.notes_processor import NotesProcessor

        # Provide a mock extractor to avoid Bedrock dependency
        mock_extractor = MagicMock()
        processor = NotesProcessor(
            framework_extractor=mock_extractor,
            encryptor=dev_encryptor,
        )

        assert processor.encryptor is dev_encryptor

        plaintext = "Session notes with PHI details."
        encrypted = processor.encrypt_notes(plaintext)
        decrypted = processor.decrypt_notes(encrypted)
        assert decrypted == plaintext

    def test_notes_processor_encrypt_is_not_plaintext(self, dev_encryptor):
        """Encrypted bytes must not contain the original plaintext."""
        from src.services.notes_processor import NotesProcessor

        mock_extractor = MagicMock()
        processor = NotesProcessor(
            framework_extractor=mock_extractor,
            encryptor=dev_encryptor,
        )

        plaintext = "Client name is Jane Doe"
        encrypted = processor.encrypt_notes(plaintext)
        # The plaintext should NOT appear in the encrypted bytes
        assert plaintext.encode("utf-8") not in encrypted

    def test_notes_processor_prepare_for_storage_encrypts(self, dev_encryptor):
        """prepare_for_storage produces encrypted bytes, not plaintext."""
        from src.services.notes_processor import NotesProcessor, NotesInput
        from src.services.framework_extractor import FrameworkExtractionOutput

        mock_extractor = MagicMock()
        processor = NotesProcessor(
            framework_extractor=mock_extractor,
            encryptor=dev_encryptor,
        )

        input_data = NotesInput(
            session_id=str(uuid4()),
            notes="Sensitive session content",
            therapist_id=str(uuid4()),
            encrypt=True,
        )
        extraction = FrameworkExtractionOutput()

        storage = processor.prepare_for_storage(input_data, extraction)
        encrypted_notes = storage["notes_encrypted"]

        assert isinstance(encrypted_notes, bytes)
        assert b"Sensitive session content" not in encrypted_notes

    def test_notes_processor_defaults_to_get_encryptor(self):
        """Without explicit encryptor, NotesProcessor uses get_encryptor()."""
        from src.services.notes_processor import NotesProcessor

        mock_extractor = MagicMock()
        with patch("src.services.notes_processor.get_encryptor") as mock_factory:
            mock_factory.return_value = MagicMock()
            processor = NotesProcessor(framework_extractor=mock_extractor)
            mock_factory.assert_called_once()
            assert processor.encryptor is mock_factory.return_value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
