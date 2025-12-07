"""
Django Admin configuration for Document Library models
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    DocumentCategory,
    DocumentTag,
    Document,
    DocumentShareLog,
    UserStorageQuota,
    DocumentBackup,
    CompressionStats,
)


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    """Admin interface for Document Categories"""

    list_display = ('name', 'user', 'color_box', 'icon', 'document_count', 'created_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('name', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('user', 'name')

    def color_box(self, obj):
        """Display color as a colored box"""
        return format_html(
            '<div style="width: 30px; height: 20px; background-color: {};"></div>',
            obj.color
        )
    color_box.short_description = 'Color'


@admin.register(DocumentTag)
class DocumentTagAdmin(admin.ModelAdmin):
    """Admin interface for Document Tags"""

    list_display = ('name', 'user', 'document_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'user__username', 'user__email')
    readonly_fields = ('created_at',)
    ordering = ('user', 'name')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Admin interface for Documents"""

    list_display = (
        'title',
        'user',
        'file_type',
        'compression_status',
        'is_compressed',
        'original_size_display',
        'compressed_size_display',
        'compression_ratio_display',
        'upload_date',
    )
    list_filter = (
        'file_type',
        'compression_status',
        'is_compressed',
        'compression_algorithm',
        'is_favorite',
        'is_public',
        'upload_date',
    )
    search_fields = ('title', 'description', 'user__username', 'user__email')
    readonly_fields = (
        'id',
        'upload_date',
        'last_modified',
        'last_accessed',
        'original_file_checksum',
        'compressed_file_checksum',
        'compression_timestamp',
        'compression_savings_display',
    )
    filter_horizontal = ('tags',)

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'title', 'description', 'file', 'file_original_name')
        }),
        ('File Metadata', {
            'fields': (
                'file_type',
                'original_file_size',
                'compressed_file_size',
                'compression_ratio',
            )
        }),
        ('Compression Details', {
            'fields': (
                'compression_algorithm',
                'is_compressed',
                'compression_status',
                'original_file_checksum',
                'compressed_file_checksum',
                'compression_timestamp',
                'decompression_failed',
            )
        }),
        ('Organization', {
            'fields': ('category', 'tags', 'is_favorite')
        }),
        ('Sharing', {
            'fields': ('is_public', 'share_token', 'share_expiry', 'share_password')
        }),
        ('Analytics', {
            'fields': (
                'download_count',
                'view_count',
                'access_count',
                'upload_date',
                'last_modified',
                'last_accessed',
            )
        }),
    )

    def original_size_display(self, obj):
        """Display original file size in human-readable format"""
        return self._format_bytes(obj.original_file_size)
    original_size_display.short_description = 'Original Size'

    def compressed_size_display(self, obj):
        """Display compressed file size in human-readable format"""
        if obj.compressed_file_size:
            return self._format_bytes(obj.compressed_file_size)
        return '-'
    compressed_size_display.short_description = 'Compressed Size'

    def compression_ratio_display(self, obj):
        """Display compression ratio as percentage"""
        if obj.compression_ratio:
            return f"{obj.compression_ratio_percentage}%"
        return '-'
    compression_ratio_display.short_description = 'Compression Ratio'

    def compression_savings_display(self, obj):
        """Display compression savings"""
        if obj.compression_savings:
            return self._format_bytes(obj.compression_savings)
        return '-'
    compression_savings_display.short_description = 'Savings'

    @staticmethod
    def _format_bytes(bytes_value):
        """Format bytes into human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"


@admin.register(DocumentShareLog)
class DocumentShareLogAdmin(admin.ModelAdmin):
    """Admin interface for Document Share Logs"""

    list_display = (
        'document',
        'shared_by',
        'share_method',
        'recipient',
        'recipient_type',
        'status',
        'shared_at',
        'access_count',
    )
    list_filter = ('share_method', 'recipient_type', 'status', 'shared_at')
    search_fields = (
        'document__title',
        'shared_by__username',
        'recipient',
    )
    readonly_fields = ('id', 'shared_at', 'last_accessed')
    ordering = ('-shared_at',)

    fieldsets = (
        ('Share Information', {
            'fields': ('id', 'document', 'shared_by', 'share_method')
        }),
        ('Recipient', {
            'fields': ('recipient', 'recipient_type')
        }),
        ('Status', {
            'fields': ('status', 'error_message', 'expiry_date')
        }),
        ('Analytics', {
            'fields': ('access_count', 'shared_at', 'last_accessed')
        }),
    )


@admin.register(UserStorageQuota)
class UserStorageQuotaAdmin(admin.ModelAdmin):
    """Admin interface for User Storage Quotas"""

    list_display = (
        'user',
        'original_quota_display',
        'original_used_display',
        'original_available_display',
        'compression_savings_display',
        'document_count',
        'original_used_percentage',
    )
    search_fields = ('user__username', 'user__email')
    readonly_fields = (
        'id',
        'last_calculated',
        'original_available',
        'original_used_percentage',
        'compression_ratio',
    )

    fieldsets = (
        ('User', {
            'fields': ('id', 'user')
        }),
        ('Storage', {
            'fields': (
                'original_quota',
                'original_used',
                'original_available',
                'original_used_percentage',
            )
        }),
        ('Compression', {
            'fields': (
                'compressed_used',
                'compression_savings',
                'compression_ratio',
            )
        }),
        ('Statistics', {
            'fields': ('document_count', 'last_calculated')
        }),
    )

    def original_quota_display(self, obj):
        return self._format_bytes(obj.original_quota)
    original_quota_display.short_description = 'Quota'

    def original_used_display(self, obj):
        return self._format_bytes(obj.original_used)
    original_used_display.short_description = 'Used'

    def original_available_display(self, obj):
        return self._format_bytes(obj.original_available)
    original_available_display.short_description = 'Available'

    def compression_savings_display(self, obj):
        return self._format_bytes(obj.compression_savings)
    compression_savings_display.short_description = 'Savings'

    @staticmethod
    def _format_bytes(bytes_value):
        """Format bytes into human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"


@admin.register(DocumentBackup)
class DocumentBackupAdmin(admin.ModelAdmin):
    """Admin interface for Document Backups"""

    list_display = (
        'document',
        'backup_created',
        'backup_expires',
        'is_expired',
        'is_used_for_recovery',
    )
    list_filter = ('backup_created', 'is_used_for_recovery')
    search_fields = ('document__title', 'document__user__username')
    readonly_fields = ('id', 'backup_created')
    ordering = ('-backup_created',)


@admin.register(CompressionStats)
class CompressionStatsAdmin(admin.ModelAdmin):
    """Admin interface for Compression Statistics"""

    list_display = (
        'user',
        'file_type',
        'algorithm',
        'total_files',
        'avg_compression_ratio_display',
        'total_savings_display',
        'failure_count',
        'last_updated',
    )
    list_filter = ('file_type', 'algorithm', 'last_updated')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('id', 'last_updated')
    ordering = ('user', 'file_type', 'algorithm')

    def avg_compression_ratio_display(self, obj):
        """Display average compression ratio as percentage"""
        return f"{obj.avg_compression_ratio * 100:.2f}%"
    avg_compression_ratio_display.short_description = 'Avg Ratio'

    def total_savings_display(self, obj):
        """Display total compression savings"""
        savings = obj.total_original_size - obj.total_compressed_size
        return self._format_bytes(savings)
    total_savings_display.short_description = 'Total Savings'

    @staticmethod
    def _format_bytes(bytes_value):
        """Format bytes into human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"
