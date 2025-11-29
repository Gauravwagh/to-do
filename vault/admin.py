"""
Admin configuration for vault models.
"""
from django.contrib import admin
from .models import (
    VaultConfig, VaultCredential, VaultSecureNote, VaultFile, VaultAPIKey,
    VaultSession, VaultAuditLog, VaultPasswordResetToken
)


@admin.register(VaultConfig)
class VaultConfigAdmin(admin.ModelAdmin):
    """Admin for vault configuration."""
    list_display = ['user', 'is_initialized', 'vault_timeout_minutes', 'failed_attempts', 'created']
    list_filter = ['is_initialized', 'created']
    search_fields = ['user__email', 'user__username']
    readonly_fields = ['encrypted_dek', 'master_password_salt', 'master_password_hash', 'created', 'modified']

    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Encryption', {
            'fields': ('encrypted_dek', 'master_password_salt', 'master_password_hash', 'kdf_iterations', 'kdf_algorithm', 'dek_version')
        }),
        ('Security Settings', {
            'fields': ('vault_timeout_minutes', 'max_failed_attempts', 'failed_attempts', 'locked_until')
        }),
        ('Status', {
            'fields': ('is_initialized', 'initialized_at', 'last_key_rotation', 'created', 'modified')
        }),
    )


@admin.register(VaultCredential)
class VaultCredentialAdmin(admin.ModelAdmin):
    """Admin for vault credentials."""
    list_display = ['id', 'user', 'credential_type', 'category', 'is_favorite', 'created']
    list_filter = ['credential_type', 'is_favorite', 'created']
    search_fields = ['user__email', 'category']
    readonly_fields = ['created', 'modified', 'encryption_iv']

    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Type', {
            'fields': ('credential_type', 'category', 'is_favorite')
        }),
        ('Encrypted Data', {
            'fields': ('name', 'username', 'password', 'email', 'website_url', 'totp_secret', 'notes'),
            'description': 'All fields below are encrypted'
        }),
        ('Encryption', {
            'fields': ('encryption_iv', 'dek_version')
        }),
        ('Metadata', {
            'fields': ('password_last_changed', 'password_strength_score', 'created', 'modified')
        }),
    )


@admin.register(VaultSecureNote)
class VaultSecureNoteAdmin(admin.ModelAdmin):
    """Admin for vault secure notes."""
    list_display = ['id', 'user', 'content_type', 'category', 'is_favorite', 'created']
    list_filter = ['content_type', 'is_favorite', 'created']
    search_fields = ['user__email', 'category']
    readonly_fields = ['created', 'modified', 'encryption_iv']


@admin.register(VaultFile)
class VaultFileAdmin(admin.ModelAdmin):
    """Admin for vault files."""
    list_display = ['id', 'user', 'file_extension', 'file_size', 'category', 'created']
    list_filter = ['file_extension', 'created']
    search_fields = ['user__email', 'category']
    readonly_fields = ['created', 'modified', 'encryption_iv', 'file_encryption_iv', 'checksum_sha256']


@admin.register(VaultAPIKey)
class VaultAPIKeyAdmin(admin.ModelAdmin):
    """Admin for vault API keys."""
    list_display = ['id', 'user', 'api_key_type', 'expires_at', 'category', 'created']
    list_filter = ['api_key_type', 'created']
    search_fields = ['user__email', 'category']
    readonly_fields = ['created', 'modified', 'encryption_iv']


@admin.register(VaultSession)
class VaultSessionAdmin(admin.ModelAdmin):
    """Admin for vault sessions."""
    list_display = ['user', 'unlocked_at', 'expires_at', 'is_active', 'ip_address']
    list_filter = ['is_active', 'unlocked_at']
    search_fields = ['user__email', 'ip_address']
    readonly_fields = ['unlocked_at', 'created', 'modified']


@admin.register(VaultAuditLog)
class VaultAuditLogAdmin(admin.ModelAdmin):
    """Admin for vault audit logs."""
    list_display = ['user', 'action', 'item_type', 'success', 'timestamp', 'ip_address']
    list_filter = ['action', 'success', 'timestamp', 'item_type']
    search_fields = ['user__email', 'ip_address']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'


@admin.register(VaultPasswordResetToken)
class VaultPasswordResetTokenAdmin(admin.ModelAdmin):
    """Admin for vault password reset tokens."""
    list_display = ['user', 'token', 'created_at', 'expires_at', 'is_used']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__email']
    readonly_fields = ['token', 'created_at']
