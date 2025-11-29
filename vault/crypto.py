"""
Cryptography service for vault operations.

This module provides all encryption, decryption, and key derivation
functionality for the vault feature using industry-standard algorithms.
"""

import base64
import secrets
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class VaultCryptoService:
    """
    Centralized cryptography service for vault operations.
    Uses Fernet (AES-256-GCM) for symmetric encryption.
    """

    @staticmethod
    def derive_key_from_master_password(
        master_password: str,
        salt: bytes,
        iterations: int = 600000
    ) -> bytes:
        """
        Derive encryption key from master password using PBKDF2.

        Args:
            master_password: The master password provided by user
            salt: Random salt for key derivation
            iterations: Number of PBKDF2 iterations (default: 600,000)

        Returns:
            32-byte key suitable for Fernet, base64url-encoded
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
        )
        key_bytes = kdf.derive(master_password.encode('utf-8'))
        return base64.urlsafe_b64encode(key_bytes)

    @staticmethod
    def generate_dek() -> bytes:
        """
        Generate random Data Encryption Key (DEK).

        Returns:
            Fernet-compatible encryption key
        """
        return Fernet.generate_key()

    @staticmethod
    def encrypt_dek(dek: bytes, master_key: bytes) -> bytes:
        """
        Encrypt DEK with master password-derived key.

        Args:
            dek: Data Encryption Key to encrypt
            master_key: Key derived from master password

        Returns:
            Encrypted DEK
        """
        f = Fernet(master_key)
        return f.encrypt(dek)

    @staticmethod
    def decrypt_dek(encrypted_dek: bytes, master_key: bytes) -> bytes:
        """
        Decrypt DEK using master password-derived key.

        Args:
            encrypted_dek: Encrypted Data Encryption Key
            master_key: Key derived from master password

        Returns:
            Decrypted DEK

        Raises:
            cryptography.fernet.InvalidToken: If decryption fails
        """
        f = Fernet(master_key)
        return f.decrypt(encrypted_dek)

    @staticmethod
    def encrypt_field(plaintext: str, dek: bytes) -> str:
        """
        Encrypt a single field value.

        Args:
            plaintext: String value to encrypt
            dek: Data Encryption Key

        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            return ''
        f = Fernet(dek)
        return f.encrypt(plaintext.encode('utf-8')).decode('ascii')

    @staticmethod
    def decrypt_field(ciphertext: str, dek: bytes) -> str:
        """
        Decrypt a single field value.

        Args:
            ciphertext: Encrypted string value
            dek: Data Encryption Key

        Returns:
            Decrypted string

        Raises:
            cryptography.fernet.InvalidToken: If decryption fails
        """
        if not ciphertext:
            return ''
        f = Fernet(dek)
        return f.decrypt(ciphertext.encode('ascii')).decode('utf-8')

    @staticmethod
    def encrypt_file(file_content: bytes, dek: bytes) -> bytes:
        """
        Encrypt file contents.

        Args:
            file_content: Binary file content
            dek: Data Encryption Key

        Returns:
            Encrypted file content
        """
        f = Fernet(dek)
        return f.encrypt(file_content)

    @staticmethod
    def decrypt_file(encrypted_content: bytes, dek: bytes) -> bytes:
        """
        Decrypt file contents.

        Args:
            encrypted_content: Encrypted binary content
            dek: Data Encryption Key

        Returns:
            Decrypted file content

        Raises:
            cryptography.fernet.InvalidToken: If decryption fails
        """
        f = Fernet(dek)
        return f.decrypt(encrypted_content)

    @staticmethod
    def hash_master_password(
        master_password: str,
        salt: bytes,
        iterations: int = 600000
    ) -> str:
        """
        Create verification hash of master password.

        Args:
            master_password: The master password to hash
            salt: Random salt for hashing
            iterations: Number of PBKDF2 iterations

        Returns:
            Base64-encoded hash string for storage
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
        )
        hash_bytes = kdf.derive(master_password.encode('utf-8'))
        return base64.b64encode(hash_bytes).decode('ascii')

    @staticmethod
    def verify_master_password(
        master_password: str,
        salt: bytes,
        stored_hash: str,
        iterations: int = 600000
    ) -> bool:
        """
        Verify master password against stored hash.
        Uses constant-time comparison to prevent timing attacks.

        Args:
            master_password: Password to verify
            salt: Salt used for hashing
            stored_hash: Previously stored hash
            iterations: Number of PBKDF2 iterations

        Returns:
            True if password is correct, False otherwise
        """
        computed_hash = VaultCryptoService.hash_master_password(
            master_password,
            salt,
            iterations
        )
        # Constant-time comparison to prevent timing attacks
        return secrets.compare_digest(computed_hash, stored_hash)

    @staticmethod
    def generate_salt() -> bytes:
        """
        Generate cryptographically secure random salt.

        Returns:
            32 bytes of random data
        """
        return secrets.token_bytes(32)
