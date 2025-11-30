"""
Serializers for Vault API endpoints.
"""
from rest_framework import serializers
from vault.models import (
    VaultConfig, VaultCredential, VaultSecureNote,
    VaultFile, VaultAPIKey, VaultSession, VaultAuditLog
)


class VaultConfigSerializer(serializers.ModelSerializer):
    """Serializer for vault configuration."""

    is_locked = serializers.BooleanField(read_only=True)

    class Meta:
        model = VaultConfig
        fields = (
            'is_initialized', 'initialized_at', 'vault_timeout_minutes',
            'max_failed_attempts', 'failed_attempts', 'is_locked',
            'locked_until', 'dek_version', 'last_key_rotation', 'created'
        )
        read_only_fields = (
            'is_initialized', 'initialized_at', 'failed_attempts',
            'locked_until', 'dek_version', 'last_key_rotation', 'created'
        )


class VaultInitializeSerializer(serializers.Serializer):
    """Serializer for initializing vault."""

    master_password = serializers.CharField(
        write_only=True,
        required=True,
        min_length=12,
        style={'input_type': 'password'}
    )
    master_password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    vault_timeout_minutes = serializers.IntegerField(
        required=False,
        default=15,
        min_value=5,
        max_value=1440
    )

    def validate(self, attrs):
        """Validate passwords match."""
        if attrs['master_password'] != attrs['master_password_confirm']:
            raise serializers.ValidationError({
                'master_password_confirm': 'Passwords do not match.'
            })
        return attrs


class VaultUnlockSerializer(serializers.Serializer):
    """Serializer for unlocking vault."""

    master_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )


class VaultPasswordChangeSerializer(serializers.Serializer):
    """Serializer for changing vault master password."""

    current_master_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    new_master_password = serializers.CharField(
        write_only=True,
        required=True,
        min_length=12,
        style={'input_type': 'password'}
    )
    new_master_password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        """Validate new passwords match."""
        if attrs['new_master_password'] != attrs['new_master_password_confirm']:
            raise serializers.ValidationError({
                'new_master_password_confirm': 'Passwords do not match.'
            })
        return attrs


class VaultCredentialSerializer(serializers.ModelSerializer):
    """Serializer for vault credentials."""

    # Note: Decrypted data will be populated in views after decryption
    decrypted_name = serializers.CharField(read_only=True, required=False)
    decrypted_username = serializers.CharField(read_only=True, required=False)
    decrypted_password = serializers.CharField(read_only=True, required=False)
    decrypted_website_url = serializers.CharField(read_only=True, required=False)
    decrypted_email = serializers.CharField(read_only=True, required=False)
    decrypted_notes = serializers.CharField(read_only=True, required=False)
    decrypted_totp_secret = serializers.CharField(read_only=True, required=False)

    class Meta:
        model = VaultCredential
        fields = (
            'id', 'credential_type', 'category', 'is_favorite',
            'password_last_changed', 'password_strength_score',
            'created', 'modified',
            # Decrypted fields (populated in view)
            'decrypted_name', 'decrypted_username', 'decrypted_password',
            'decrypted_website_url', 'decrypted_email', 'decrypted_notes',
            'decrypted_totp_secret'
        )
        read_only_fields = ('id', 'created', 'modified')


class VaultCredentialCreateUpdateSerializer(serializers.Serializer):
    """Serializer for creating/updating credentials."""

    name = serializers.CharField(required=True)
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)
    website_url = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    totp_secret = serializers.CharField(required=False, allow_blank=True)
    credential_type = serializers.ChoiceField(
        choices=VaultCredential.CREDENTIAL_TYPES,
        default='login'
    )
    category = serializers.CharField(required=False, allow_blank=True)
    is_favorite = serializers.BooleanField(default=False)


class VaultSecureNoteSerializer(serializers.ModelSerializer):
    """Serializer for vault secure notes."""

    decrypted_name = serializers.CharField(read_only=True, required=False)
    decrypted_content = serializers.CharField(read_only=True, required=False)
    decrypted_notes = serializers.CharField(read_only=True, required=False)

    class Meta:
        model = VaultSecureNote
        fields = (
            'id', 'content_type', 'category', 'is_favorite',
            'created', 'modified',
            'decrypted_name', 'decrypted_content', 'decrypted_notes'
        )
        read_only_fields = ('id', 'created', 'modified')


class VaultSecureNoteCreateUpdateSerializer(serializers.Serializer):
    """Serializer for creating/updating secure notes."""

    name = serializers.CharField(required=True)
    content = serializers.CharField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    content_type = serializers.ChoiceField(
        choices=VaultSecureNote.CONTENT_TYPES,
        default='plaintext'
    )
    category = serializers.CharField(required=False, allow_blank=True)
    is_favorite = serializers.BooleanField(default=False)


class VaultFileSerializer(serializers.ModelSerializer):
    """Serializer for vault files."""

    decrypted_name = serializers.CharField(read_only=True, required=False)
    decrypted_original_filename = serializers.CharField(read_only=True, required=False)
    decrypted_notes = serializers.CharField(read_only=True, required=False)
    file_size_human = serializers.CharField(source='get_file_size_human', read_only=True)

    class Meta:
        model = VaultFile
        fields = (
            'id', 'file_size', 'encrypted_file_size', 'mime_type',
            'file_extension', 'category', 'is_favorite',
            'created', 'modified', 'file_size_human',
            'decrypted_name', 'decrypted_original_filename', 'decrypted_notes'
        )
        read_only_fields = (
            'id', 'file_size', 'encrypted_file_size', 'mime_type',
            'file_extension', 'created', 'modified'
        )


class VaultFileCreateSerializer(serializers.Serializer):
    """Serializer for uploading files to vault."""

    name = serializers.CharField(required=True)
    file = serializers.FileField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField(required=False, allow_blank=True)
    is_favorite = serializers.BooleanField(default=False)


class VaultAPIKeySerializer(serializers.ModelSerializer):
    """Serializer for vault API keys."""

    decrypted_name = serializers.CharField(read_only=True, required=False)
    decrypted_service_name = serializers.CharField(read_only=True, required=False)
    decrypted_api_key = serializers.CharField(read_only=True, required=False)
    decrypted_api_secret = serializers.CharField(read_only=True, required=False)
    decrypted_notes = serializers.CharField(read_only=True, required=False)
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = VaultAPIKey
        fields = (
            'id', 'api_key_type', 'category', 'is_favorite',
            'expires_at', 'is_expired', 'created', 'modified',
            'decrypted_name', 'decrypted_service_name',
            'decrypted_api_key', 'decrypted_api_secret', 'decrypted_notes'
        )
        read_only_fields = ('id', 'created', 'modified')

    def get_is_expired(self, obj):
        """Check if API key is expired."""
        if obj.expires_at:
            from django.utils import timezone
            return obj.expires_at < timezone.now()
        return False


class VaultAPIKeyCreateUpdateSerializer(serializers.Serializer):
    """Serializer for creating/updating API keys."""

    name = serializers.CharField(required=True)
    service_name = serializers.CharField(required=True)
    api_key = serializers.CharField(required=True)
    api_secret = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    api_key_type = serializers.ChoiceField(
        choices=VaultAPIKey.API_KEY_TYPES,
        default='api_key'
    )
    category = serializers.CharField(required=False, allow_blank=True)
    is_favorite = serializers.BooleanField(default=False)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)


class VaultAuditLogSerializer(serializers.ModelSerializer):
    """Serializer for vault audit logs."""

    class Meta:
        model = VaultAuditLog
        fields = (
            'id', 'action_type', 'item_type', 'item_id',
            'description', 'ip_address', 'user_agent',
            'success', 'error_message', 'created'
        )
        read_only_fields = fields


class VaultSearchSerializer(serializers.Serializer):
    """Serializer for vault search."""

    query = serializers.CharField(required=True, min_length=1)
    item_types = serializers.MultipleChoiceField(
        choices=['credentials', 'secure_notes', 'files', 'api_keys'],
        required=False,
        default=['credentials', 'secure_notes', 'files', 'api_keys']
    )


class VaultStatsSerializer(serializers.Serializer):
    """Serializer for vault statistics."""

    total_items = serializers.IntegerField()
    credentials_count = serializers.IntegerField()
    secure_notes_count = serializers.IntegerField()
    files_count = serializers.IntegerField()
    api_keys_count = serializers.IntegerField()
    total_file_size = serializers.IntegerField()
    total_file_size_human = serializers.CharField()
    weak_passwords_count = serializers.IntegerField()
    expired_keys_count = serializers.IntegerField()
