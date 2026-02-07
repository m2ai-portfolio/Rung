"""
KMS Envelope Encryption Service

Implements AWS KMS envelope encryption for field-level PHI encryption.
Uses KMS GenerateDataKey for AES-256-GCM local encryption.

Wire format:
    [2 bytes: key_length (big-endian uint16)]
    [encrypted_data_key (key_length bytes)]
    [12 bytes: nonce]
    [ciphertext + 16-byte GCM auth tag]

Encryption context binds data keys to a specific entity
(e.g., {"therapist_id": "...", "client_id": "..."}).
"""

import os
import struct
from typing import Protocol, Union

import boto3
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# ---------------------------------------------------------------------------
# Protocol for encryptors (structural typing)
# ---------------------------------------------------------------------------

class Encryptor(Protocol):
    """Minimal interface that all encryptors expose."""

    def encrypt(self, plaintext: str, context: dict[str, str]) -> bytes: ...
    def decrypt(self, ciphertext: bytes, context: dict[str, str]) -> str: ...


# ---------------------------------------------------------------------------
# FieldEncryptor -- production KMS envelope encryption
# ---------------------------------------------------------------------------

_NONCE_LENGTH = 12  # 96-bit nonce for AES-GCM
_KEY_LENGTH_FMT = "!H"  # big-endian unsigned short (2 bytes)
_KEY_LENGTH_SIZE = struct.calcsize(_KEY_LENGTH_FMT)


class FieldEncryptor:
    """
    AWS KMS envelope encryption for PHI fields.

    Calls KMS GenerateDataKey to obtain a unique AES-256 data key per
    encrypt() call, encrypts locally with AES-256-GCM, and packs the
    encrypted data key alongside the ciphertext so that KMS is only
    needed for key operations (not bulk data encryption).
    """

    def __init__(self, kms_key_id: str, region: str | None = None):
        """
        Args:
            kms_key_id: ARN or alias of the KMS key used for envelope encryption.
            region: AWS region. Falls back to AWS_REGION / AWS_DEFAULT_REGION.
        """
        self.kms_key_id = kms_key_id
        region = region or os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
        self._kms = boto3.client("kms", region_name=region)

    def encrypt(self, plaintext: str, context: dict[str, str]) -> bytes:
        """
        Encrypt *plaintext* with a fresh KMS data key.

        Args:
            plaintext: UTF-8 string to encrypt.
            context: KMS encryption context (e.g. therapist/client IDs).

        Returns:
            Wire-format bytes containing the encrypted data key, nonce,
            and AES-256-GCM ciphertext+tag.
        """
        # 1. Generate a unique data key via KMS
        dk_response = self._kms.generate_data_key(
            KeyId=self.kms_key_id,
            KeySpec="AES_256",
            EncryptionContext=context,
        )
        plaintext_key: bytes = dk_response["Plaintext"]
        encrypted_key: bytes = dk_response["CiphertextBlob"]

        # 2. Encrypt locally with AES-256-GCM
        nonce = os.urandom(_NONCE_LENGTH)
        aesgcm = AESGCM(plaintext_key)
        ct_with_tag = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)

        # 3. Pack wire format
        key_length = len(encrypted_key)
        wire = (
            struct.pack(_KEY_LENGTH_FMT, key_length)
            + encrypted_key
            + nonce
            + ct_with_tag
        )
        return wire

    def decrypt(self, ciphertext: bytes, context: dict[str, str]) -> str:
        """
        Decrypt wire-format *ciphertext* produced by :meth:`encrypt`.

        Args:
            ciphertext: Wire-format bytes from encrypt().
            context: Must match the encryption context used during encrypt().

        Returns:
            Original plaintext string.

        Raises:
            ValueError: If the wire format is malformed.
        """
        if len(ciphertext) < _KEY_LENGTH_SIZE:
            raise ValueError("Ciphertext too short: missing key length header")

        # 1. Unpack key length
        offset = 0
        (key_length,) = struct.unpack_from(_KEY_LENGTH_FMT, ciphertext, offset)
        offset += _KEY_LENGTH_SIZE

        if len(ciphertext) < offset + key_length + _NONCE_LENGTH + 1:
            raise ValueError("Ciphertext too short for declared key length")

        # 2. Extract encrypted data key
        encrypted_key = ciphertext[offset : offset + key_length]
        offset += key_length

        # 3. Extract nonce
        nonce = ciphertext[offset : offset + _NONCE_LENGTH]
        offset += _NONCE_LENGTH

        # 4. Remaining bytes are ciphertext + GCM tag
        ct_with_tag = ciphertext[offset:]

        # 5. Decrypt data key via KMS
        dk_response = self._kms.decrypt(
            CiphertextBlob=encrypted_key,
            EncryptionContext=context,
        )
        plaintext_key: bytes = dk_response["Plaintext"]

        # 6. Decrypt locally
        aesgcm = AESGCM(plaintext_key)
        plaintext_bytes = aesgcm.decrypt(nonce, ct_with_tag, None)
        return plaintext_bytes.decode("utf-8")


# ---------------------------------------------------------------------------
# DevEncryptor -- local development (no KMS dependency)
# ---------------------------------------------------------------------------

# Default key for local development only.  Not used in production.
_DEV_DEFAULT_KEY = Fernet.generate_key()


class DevEncryptor:
    """
    Fernet-based encryptor for local development and testing.

    Uses the ``RUNG_DEV_ENCRYPTION_KEY`` environment variable when set,
    otherwise falls back to a process-scoped random key.  The encryption
    context is incorporated into the Fernet additional data by prepending
    a deterministic context tag so that different contexts produce
    different ciphertext (Fernet itself does not support AAD, so the
    context is mixed into the plaintext envelope).
    """

    def __init__(self, key: bytes | None = None):
        env_key = os.environ.get("RUNG_DEV_ENCRYPTION_KEY")
        if key is not None:
            self._key = key
        elif env_key is not None:
            self._key = env_key.encode("utf-8") if isinstance(env_key, str) else env_key
        else:
            self._key = _DEV_DEFAULT_KEY
        self._fernet = Fernet(self._key)

    @staticmethod
    def _context_tag(context: dict[str, str]) -> bytes:
        """Build a deterministic tag from the encryption context."""
        # Sort keys for determinism, join as key=value pairs
        pairs = sorted(context.items())
        tag = "&".join(f"{k}={v}" for k, v in pairs)
        return tag.encode("utf-8")

    def encrypt(self, plaintext: str, context: dict[str, str]) -> bytes:
        """
        Encrypt *plaintext* using Fernet.

        The encryption context is prepended (length-prefixed) so that
        different contexts produce different ciphertext and decryption
        validates the context.
        """
        ctx_tag = self._context_tag(context)
        # Envelope: [4-byte context tag length][context tag][plaintext]
        envelope = struct.pack("!I", len(ctx_tag)) + ctx_tag + plaintext.encode("utf-8")
        return self._fernet.encrypt(envelope)

    def decrypt(self, ciphertext: bytes, context: dict[str, str]) -> str:
        """
        Decrypt *ciphertext* produced by :meth:`encrypt`.

        Validates that the stored encryption context matches *context*.

        Raises:
            ValueError: If the context does not match.
        """
        envelope = self._fernet.decrypt(ciphertext)
        # Extract context tag
        (tag_len,) = struct.unpack_from("!I", envelope, 0)
        stored_tag = envelope[4 : 4 + tag_len]
        expected_tag = self._context_tag(context)
        if stored_tag != expected_tag:
            raise ValueError(
                "Encryption context mismatch: stored context does not match "
                "the context provided for decryption"
            )
        plaintext_bytes = envelope[4 + tag_len :]
        return plaintext_bytes.decode("utf-8")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_encryptor() -> Union[FieldEncryptor, DevEncryptor]:
    """
    Return the appropriate encryptor for the current environment.

    Returns:
        FieldEncryptor when RUNG_ENV=production and FIELD_ENCRYPTION_KEY_ID
        is set; DevEncryptor otherwise.
    """
    env = os.environ.get("RUNG_ENV", "development")
    kms_key_id = os.environ.get("FIELD_ENCRYPTION_KEY_ID")

    if env == "production" and kms_key_id:
        region = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
        return FieldEncryptor(kms_key_id=kms_key_id, region=region)

    return DevEncryptor()
