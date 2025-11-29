"""
Vault models for secure data storage.

This module defines all database models for the vault feature including:
- VaultConfig: Per-user vault configuration and encryption keys
- VaultItem: Abstract base for all vault items
- VaultCredential, VaultSecureNote, VaultFile, VaultAPIKey: Specific item types
- VaultSession: Active vault sessions
- VaultAuditLog: Comprehensive audit trail
- VaultPasswordResetToken: Password reset tokens
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from core.models import TimeStampedModel

User = get_user_model()


class VaultConfig(TimeStampedModel):
    """
    One-to-one with User. Stores vault encryption configuration.

    This model contains the encrypted Data Encryption Key (DEK) and
    master password verification data.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='vault_config'
    )

    # Encrypted Data Encryption Key (DEK)
    encrypted_dek = models.BinaryField(
        help_text="DEK encrypted with master password-derived key"
    )

    # Salt for master password PBKDF2
    master_password_salt = models.BinaryField()

    # Master password hash for verification (PBKDF2)
    master_password_hash = models.CharField(max_length=255)

    # Key derivation parameters
    kdf_iterations = models.IntegerField(
        default=600000,
        help_text="PBKDF2 iterations (OWASP 2023 recommendation)"
    )
    kdf_algorithm = models.CharField(
        max_length=50,
        default='pbkdf2_hmac_sha256'
    )

    # Security settings
    vault_timeout_minutes = models.IntegerField(
        default=15,
        help_text="Minutes before vault auto-locks"
    )
    max_failed_attempts = models.IntegerField(
        default=5,
        help_text="Max failed unlock attempts before lockout"
    )
    failed_attempts = models.IntegerField(
        default=0,
        help_text="Current failed unlock attempts"
    )
    locked_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Temporary lockout expiration"
    )

    # Setup tracking
    is_initialized = models.BooleanField(
        default=False,
        help_text="Whether vault has been set up"
    )
    initialized_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Key rotation
    dek_version = models.IntegerField(
        default=1,
        help_text="DEK version for key rotation"
    )
    last_key_rotation = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'vault_config'
        verbose_name = 'Vault Configuration'
        verbose_name_plural = 'Vault Configurations'

    def __str__(self):
        return f"Vault Config for {self.user.email}"

    def is_locked(self):
        """Check if vault is temporarily locked due to failed attempts."""
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False

    def reset_failed_attempts(self):
        """Reset failed attempts counter after successful unlock."""
        self.failed_attempts = 0
        self.locked_until = None
        self.save(update_fields=['failed_attempts', 'locked_until'])


class VaultItem(TimeStampedModel):
    """
    Abstract base model for all vault items.

    All specific vault item types inherit from this base model.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='vault_%(class)s_items'
    )

    # Encrypted fields
    name = models.TextField(
        help_text="Encrypted item name"
    )
    notes = models.TextField(
        blank=True,
        help_text="Encrypted notes"
    )

    # Metadata (unencrypted for filtering/sorting)
    category = models.CharField(
        max_length=100,
        blank=True,
        db_index=True
    )
    is_favorite = models.BooleanField(
        default=False,
        db_index=True
    )

    # Encryption metadata
    encryption_iv = models.BinaryField(
        help_text="Initialization vector for encryption"
    )
    dek_version = models.IntegerField(
        default=1,
        help_text="DEK version used for encryption"
    )

    class Meta:
        abstract = True
        ordering = ['-created']
        indexes = [
            models.Index(fields=['user', '-created']),
            models.Index(fields=['user', 'is_favorite']),
        ]

    def __str__(self):
        return f"{self.__class__.__name__} for {self.user.email}"


class VaultCredential(VaultItem):
    """
    Stores login credentials (username/password pairs).
    """

    CREDENTIAL_TYPES = [
        ('login', 'Login Credentials'),
        ('banking', 'Banking'),
        ('email', 'Email Account'),
        ('social', 'Social Media'),
        ('other', 'Other'),
    ]

    credential_type = models.CharField(
        max_length=20,
        choices=CREDENTIAL_TYPES,
        default='login',
        db_index=True
    )

    # Encrypted fields
    website_url = models.TextField(
        blank=True,
        help_text="Encrypted website URL"
    )
    username = models.TextField(
        help_text="Encrypted username"
    )
    password = models.TextField(
        help_text="Encrypted password"
    )
    email = models.TextField(
        blank=True,
        help_text="Encrypted email address"
    )
    totp_secret = models.TextField(
        blank=True,
        help_text="Encrypted TOTP secret for 2FA"
    )

    # Password metadata (unencrypted)
    password_last_changed = models.DateTimeField(
        null=True,
        blank=True
    )
    password_strength_score = models.IntegerField(
        default=0,
        help_text="Password strength (0-4)"
    )

    class Meta:
        db_table = 'vault_credentials'
        verbose_name = 'Vault Credential'
        verbose_name_plural = 'Vault Credentials'


class VaultSecureNote(VaultItem):
    """
    Encrypted text notes for sensitive information.
    """

    CONTENT_TYPES = [
        ('plaintext', 'Plain Text'),
        ('markdown', 'Markdown'),
        ('code', 'Code Snippet'),
    ]

    # Encrypted field
    content = models.TextField(
        help_text="Encrypted note content"
    )

    content_type = models.CharField(
        max_length=50,
        default='plaintext',
        choices=CONTENT_TYPES
    )

    class Meta:
        db_table = 'vault_secure_notes'
        verbose_name = 'Vault Secure Note'
        verbose_name_plural = 'Vault Secure Notes'


class VaultFile(VaultItem):
    """
    Encrypted file storage.
    """

    # Encrypted file storage
    encrypted_file = models.FileField(
        upload_to='vault/files/',
        help_text="Encrypted file"
    )

    # File metadata (some encrypted, some not)
    original_filename = models.TextField(
        help_text="Encrypted original filename"
    )
    file_size = models.BigIntegerField(
        help_text="Original file size in bytes"
    )
    encrypted_file_size = models.BigIntegerField(
        help_text="Encrypted file size in bytes"
    )
    mime_type = models.CharField(
        max_length=100,
        help_text="File MIME type"
    )
    file_extension = models.CharField(
        max_length=20,
        help_text="File extension"
    )

    # Encryption specific
    file_encryption_iv = models.BinaryField(
        help_text="Initialization vector for file encryption"
    )
    checksum_sha256 = models.CharField(
        max_length=64,
        help_text="SHA-256 checksum for integrity verification"
    )

    class Meta:
        db_table = 'vault_files'
        verbose_name = 'Vault File'
        verbose_name_plural = 'Vault Files'

    def get_file_size_human(self):
        """Return human-readable file size."""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f'{size:.1f} {unit}'
            size /= 1024.0
        return f'{size:.1f} TB'


class VaultAPIKey(VaultItem):
    """
    Store API keys, tokens, and secrets.
    """

    API_KEY_TYPES = [
        ('api_key', 'API Key'),
        ('oauth_token', 'OAuth Token'),
        ('jwt', 'JWT Token'),
        ('ssh_key', 'SSH Key'),
        ('pgp_key', 'PGP Key'),
        ('other', 'Other'),
    ]

    api_key_type = models.CharField(
        max_length=20,
        choices=API_KEY_TYPES,
        default='api_key',
        db_index=True
    )

    # Encrypted fields
    service_name = models.TextField(
        help_text="Encrypted service name"
    )
    api_key = models.TextField(
        help_text="Encrypted API key"
    )
    api_secret = models.TextField(
        blank=True,
        help_text="Encrypted API secret"
    )

    # Token expiration
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Token expiration date"
    )
    expiration_warning_days = models.IntegerField(
        default=30,
        help_text="Days before expiration to show warning"
    )

    class Meta:
        db_table = 'vault_api_keys'
        verbose_name = 'Vault API Key'
        verbose_name_plural = 'Vault API Keys'

    def is_expiring_soon(self):
        """Check if API key is expiring within warning period."""
        if self.expires_at:
            warning_date = self.expires_at - timezone.timedelta(days=self.expiration_warning_days)
            return timezone.now() >= warning_date
        return False

    def is_expired(self):
        """Check if API key has expired."""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False


class VaultSession(TimeStampedModel):
    """
    Track active vault sessions for timeout management.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='vault_sessions'
    )

    session_key = models.CharField(
        max_length=40,
        unique=True,
        help_text="Django session key"
    )

    unlocked_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When vault was unlocked"
    )
    last_activity = models.DateTimeField(
        auto_now=True,
        help_text="Last activity timestamp"
    )
    expires_at = models.DateTimeField(
        help_text="Session expiration time"
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True
    )

    # Connection info
    ip_address = models.GenericIPAddressField(
        help_text="IP address of unlock"
    )
    user_agent = models.CharField(
        max_length=255,
        help_text="User agent string"
    )

    class Meta:
        db_table = 'vault_sessions'
        verbose_name = 'Vault Session'
        verbose_name_plural = 'Vault Sessions'
        ordering = ['-unlocked_at']
        indexes = [
            models.Index(fields=['user', '-unlocked_at']),
            models.Index(fields=['is_active', 'expires_at']),
        ]

    def __str__(self):
        return f"Vault session for {self.user.email} at {self.unlocked_at}"

    def is_expired(self):
        """Check if session has expired."""
        return timezone.now() > self.expires_at


class VaultAuditLog(models.Model):
    """
    Comprehensive audit logging for vault operations.
    """

    ACTION_TYPES = [
        ('unlock', 'Vault Unlocked'),
        ('lock', 'Vault Locked'),
        ('timeout', 'Session Timeout'),
        ('view', 'Item Viewed'),
        ('create', 'Item Created'),
        ('update', 'Item Updated'),
        ('delete', 'Item Deleted'),
        ('password_reveal', 'Password Revealed'),
        ('file_download', 'File Downloaded'),
        ('failed_unlock', 'Failed Unlock Attempt'),
        ('key_rotation', 'Key Rotation'),
        ('password_reset_requested', 'Password Reset Requested'),
        ('password_reset_completed', 'Password Reset Completed'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='vault_audit_logs'
    )

    action = models.CharField(
        max_length=30,
        choices=ACTION_TYPES,
        db_index=True
    )

    item_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Type of vault item (if applicable)"
    )
    item_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="ID of vault item (if applicable)"
    )

    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )

    # Connection info
    ip_address = models.GenericIPAddressField(
        help_text="IP address of action"
    )
    user_agent = models.CharField(
        max_length=255,
        help_text="User agent string"
    )

    success = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether action succeeded"
    )

    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional details about the action"
    )

    class Meta:
        db_table = 'vault_audit_logs'
        verbose_name = 'Vault Audit Log'
        verbose_name_plural = 'Vault Audit Logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['success', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.action} by {self.user.email} at {self.timestamp}"


class VaultPasswordResetToken(models.Model):
    """
    Password reset tokens for vault master password recovery.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='vault_reset_tokens'
    )

    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text="Unique reset token"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )
    expires_at = models.DateTimeField(
        help_text="Token expiration time (typically 1 hour)"
    )

    is_used = models.BooleanField(
        default=False,
        help_text="Whether token has been used"
    )

    ip_address = models.GenericIPAddressField(
        help_text="IP address where reset was requested"
    )

    class Meta:
        db_table = 'vault_password_reset_tokens'
        verbose_name = 'Vault Password Reset Token'
        verbose_name_plural = 'Vault Password Reset Tokens'
        ordering = ['-created_at']

    def __str__(self):
        return f"Reset token for {self.user.email}"

    def is_valid(self):
        """Check if token is still valid."""
        return not self.is_used and timezone.now() < self.expires_at
