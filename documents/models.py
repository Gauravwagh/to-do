"""
Document Library Models

This module contains all models for the personal document library system:
- DocumentCategory: Organize documents into folders/categories
- DocumentTag: Flexible tagging system
- Document: Core document model with compression metadata
- DocumentShareLog: Audit trail for sharing operations
- UserStorageQuota: Track user storage usage
- DocumentBackup: Keep original files for recovery
- CompressionStats: Track compression performance metrics
"""
import uuid
import hashlib
from datetime import timedelta
from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from django.utils.crypto import get_random_string


class DocumentCategory(models.Model):
    """
    Folder model for organizing documents (Google Drive-like structure).
    Supports nested folders with unlimited depth.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='document_categories'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#3B82F6', help_text='Hex color code')
    icon = models.CharField(max_length=50, default='folder', help_text='Icon name')
    
    # Parent folder for nesting (null = root level)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subfolders'
    )
    
    # Cached path for efficient queries
    path = models.CharField(max_length=1000, blank=True, help_text='Cached full path')
    depth = models.PositiveIntegerField(default=0, help_text='Nesting depth level')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Folder'
        verbose_name_plural = 'Folders'
        unique_together = ('user', 'name', 'parent')
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['user', 'parent']),
            models.Index(fields=['user', 'path']),
        ]
        ordering = ['name']

    def __str__(self):
        return f"{self.user.username} - {self.full_path}"

    def save(self, *args, **kwargs):
        """Update path and depth on save"""
        self._update_path_and_depth()
        super().save(*args, **kwargs)
        # Update children paths if this folder's path changed
        self._update_children_paths()

    def _update_path_and_depth(self):
        """Calculate and set the path and depth"""
        if self.parent:
            self.path = f"{self.parent.path}/{self.name}"
            self.depth = self.parent.depth + 1
        else:
            self.path = self.name
            self.depth = 0

    def _update_children_paths(self):
        """Recursively update all children's paths"""
        for child in self.subfolders.all():
            child.save()

    @property
    def full_path(self):
        """Get full path from root"""
        return self.path or self.name

    @property
    def breadcrumbs(self):
        """Get list of ancestors for breadcrumb navigation"""
        crumbs = []
        current = self
        while current:
            crumbs.insert(0, current)
            current = current.parent
        return crumbs

    @property
    def document_count(self):
        """Count of documents directly in this folder"""
        return self.documents.count()

    @property
    def total_document_count(self):
        """Count of all documents including subfolders"""
        count = self.documents.count()
        for subfolder in self.subfolders.all():
            count += subfolder.total_document_count
        return count

    @property
    def subfolder_count(self):
        """Count of direct subfolders"""
        return self.subfolders.count()

    def get_ancestors(self):
        """Get all ancestor folders"""
        ancestors = []
        current = self.parent
        while current:
            ancestors.insert(0, current)
            current = current.parent
        return ancestors

    def get_descendants(self):
        """Get all descendant folders"""
        descendants = list(self.subfolders.all())
        for subfolder in self.subfolders.all():
            descendants.extend(subfolder.get_descendants())
        return descendants

    def can_move_to(self, target_folder):
        """Check if this folder can be moved to target (prevent circular references)"""
        if target_folder is None:
            return True
        if target_folder == self:
            return False
        # Check if target is a descendant of this folder
        return target_folder not in self.get_descendants()


class DocumentTag(models.Model):
    """Flexible tagging system for document organization"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='document_tags'
    )
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Document Tags'
        unique_together = ('user', 'name')
        ordering = ['name']

    def __str__(self):
        return f"{self.user.username} - {self.name}"

    @property
    def document_count(self):
        """Count of documents with this tag"""
        return self.documents.count()


class Document(models.Model):
    """
    Core document model with compression metadata.
    Stores document metadata and tracks compression status.
    """

    FILE_TYPE_CHOICES = [
        ('pdf', 'PDF'),
        ('docx', 'Word Document'),
        ('xlsx', 'Excel Spreadsheet'),
        ('pptx', 'PowerPoint Presentation'),
        ('txt', 'Text File'),
        ('csv', 'CSV File'),
        ('png', 'PNG Image'),
        ('jpg', 'JPG Image'),
        ('jpeg', 'JPEG Image'),
        ('gif', 'GIF Image'),
        ('zip', 'ZIP Archive'),
    ]

    COMPRESSION_ALGORITHM_CHOICES = [
        ('zstd', 'Zstandard'),
        ('deflate', 'DEFLATE'),
        ('brotli', 'Brotli'),
        ('none', 'None'),
    ]

    COMPRESSION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('compressing', 'Compressing'),
        ('compressed', 'Compressed'),
        ('failed', 'Failed'),
        ('uncompressed', 'Uncompressed'),
    ]

    # Core fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='documents/%Y/%m/%d/')
    file_original_name = models.CharField(max_length=255)

    # File metadata
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES)
    original_file_size = models.BigIntegerField(help_text='Size in bytes before compression')
    compressed_file_size = models.BigIntegerField(
        null=True,
        blank=True,
        help_text='Actual stored size in bytes'
    )
    compression_ratio = models.FloatField(
        null=True,
        blank=True,
        help_text='Compression ratio (0.0 to 1.0)'
    )
    compression_algorithm = models.CharField(
        max_length=10,
        choices=COMPRESSION_ALGORITHM_CHOICES,
        default='none'
    )
    is_compressed = models.BooleanField(default=False)

    # Compression metadata
    original_file_checksum = models.CharField(max_length=64, help_text='SHA256 hash')
    compressed_file_checksum = models.CharField(
        max_length=64,
        blank=True,
        help_text='SHA256 hash of compressed file'
    )
    compression_timestamp = models.DateTimeField(null=True, blank=True)
    decompression_failed = models.BooleanField(default=False)
    compression_status = models.CharField(
        max_length=20,
        choices=COMPRESSION_STATUS_CHOICES,
        default='pending'
    )

    # Organization - folder (category) is the parent folder (null = root/My Drive)
    category = models.ForeignKey(
        DocumentCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents',
        verbose_name='Folder'
    )
    tags = models.ManyToManyField(DocumentTag, blank=True, related_name='documents')
    is_favorite = models.BooleanField(default=False)

    @property
    def folder(self):
        """Alias for category - treat as folder"""
        return self.category

    @folder.setter
    def folder(self, value):
        """Alias setter for category"""
        self.category = value

    # Timestamps
    upload_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    last_accessed = models.DateTimeField(null=True, blank=True)

    # Sharing
    is_public = models.BooleanField(default=False)
    share_token = models.CharField(max_length=64, unique=True, null=True, blank=True)
    share_expiry = models.DateTimeField(null=True, blank=True)
    share_password = models.CharField(max_length=128, blank=True)

    # Analytics
    download_count = models.IntegerField(default=0)
    view_count = models.IntegerField(default=0)
    access_count = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['user', '-upload_date']),
            models.Index(fields=['user', 'category']),
            models.Index(fields=['user', 'is_favorite']),
            models.Index(fields=['user', 'compression_status']),
            models.Index(fields=['share_token']),
            models.Index(fields=['user', 'file_type']),
        ]
        ordering = ['-upload_date']

    def __str__(self):
        return f"{self.title} ({self.file_type})"

    def save(self, *args, **kwargs):
        """Generate share token if needed"""
        if self.is_public and not self.share_token:
            self.share_token = get_random_string(length=64)
        super().save(*args, **kwargs)

    def generate_share_token(self):
        """Generate a new share token"""
        self.share_token = get_random_string(length=64)
        self.is_public = True
        self.save(update_fields=['share_token', 'is_public'])
        return self.share_token

    def revoke_share(self):
        """Revoke public sharing"""
        self.is_public = False
        self.share_token = None
        self.share_expiry = None
        self.save(update_fields=['is_public', 'share_token', 'share_expiry'])

    def is_share_expired(self):
        """Check if share link is expired"""
        if not self.share_expiry:
            return False
        return timezone.now() > self.share_expiry

    def increment_download_count(self):
        """Increment download counter"""
        self.download_count += 1
        self.last_accessed = timezone.now()
        self.save(update_fields=['download_count', 'last_accessed'])

    def increment_view_count(self):
        """Increment view counter"""
        self.view_count += 1
        self.last_accessed = timezone.now()
        self.save(update_fields=['view_count', 'last_accessed'])

    def increment_access_count(self):
        """Increment access counter"""
        self.access_count += 1
        self.last_accessed = timezone.now()
        self.save(update_fields=['access_count', 'last_accessed'])

    @property
    def compression_savings(self):
        """Calculate compression savings in bytes"""
        if self.is_compressed and self.compressed_file_size:
            return self.original_file_size - self.compressed_file_size
        return 0

    @property
    def compression_ratio_percentage(self):
        """Get compression ratio as percentage"""
        if self.compression_ratio:
            return round(self.compression_ratio * 100, 2)
        return 0

    @property
    def file_size_display(self):
        """Human-readable file size"""
        size = self.compressed_file_size if self.is_compressed else self.original_file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"


class DocumentShareLog(models.Model):
    """Audit trail for all sharing operations"""

    SHARE_METHOD_CHOICES = [
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
        ('direct_link', 'Direct Link'),
        ('internal_user', 'Internal User'),
    ]

    RECIPIENT_TYPE_CHOICES = [
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('user', 'User'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('opened', 'Opened'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='share_logs'
    )
    shared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shared_documents'
    )
    share_method = models.CharField(max_length=20, choices=SHARE_METHOD_CHOICES)
    recipient = models.CharField(max_length=255, help_text='Email, phone, or username')
    recipient_type = models.CharField(max_length=10, choices=RECIPIENT_TYPE_CHOICES)
    shared_at = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)
    access_count = models.IntegerField(default=0)
    last_accessed = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['document', '-shared_at']),
            models.Index(fields=['shared_by', '-shared_at']),
            models.Index(fields=['recipient', 'status']),
        ]
        ordering = ['-shared_at']

    def __str__(self):
        return f"{self.document.title} shared via {self.share_method} to {self.recipient}"

    def is_expired(self):
        """Check if share is expired"""
        if not self.expiry_date:
            return False
        return timezone.now() > self.expiry_date

    def increment_access(self):
        """Increment access counter"""
        self.access_count += 1
        self.last_accessed = timezone.now()
        self.status = 'opened'
        self.save(update_fields=['access_count', 'last_accessed', 'status'])


class UserStorageQuota(models.Model):
    """Track user storage usage"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='storage_quota'
    )
    original_quota = models.BigIntegerField(
        default=1099511627776,  # 1TB in bytes
        help_text='Allowed storage in bytes'
    )
    original_used = models.BigIntegerField(
        default=0,
        help_text='Sum of original file sizes'
    )
    compressed_used = models.BigIntegerField(
        default=0,
        help_text='Actual disk usage'
    )
    compression_savings = models.BigIntegerField(
        default=0,
        help_text='Bytes saved by compression'
    )
    last_calculated = models.DateTimeField(auto_now=True)
    document_count = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = 'User Storage Quotas'

    def __str__(self):
        return f"{self.user.username} - {self.original_used}/{self.original_quota} bytes"

    @property
    def original_available(self):
        """Calculate available storage based on original sizes"""
        return self.original_quota - self.original_used

    @property
    def original_used_percentage(self):
        """Percentage of quota used"""
        if self.original_quota == 0:
            return 0
        return round((self.original_used / self.original_quota) * 100, 2)

    @property
    def compression_ratio(self):
        """Overall compression ratio"""
        if self.original_used == 0:
            return 0
        return round(self.compressed_used / self.original_used, 2)

    def recalculate(self):
        """Recalculate storage usage from documents"""
        from django.db.models import Sum, Count

        stats = self.user.documents.aggregate(
            total_original=Sum('original_file_size'),
            total_compressed=Sum('compressed_file_size'),
            count=Count('id')
        )

        self.original_used = stats['total_original'] or 0
        self.compressed_used = stats['total_compressed'] or stats['total_original'] or 0
        self.compression_savings = self.original_used - self.compressed_used
        self.document_count = stats['count'] or 0
        self.save()

    def is_over_quota(self):
        """Check if user is over quota"""
        return self.original_used > self.original_quota


class DocumentBackup(models.Model):
    """Keep original files for recovery (24-48 hours)"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
        related_name='backup'
    )
    backup_file = models.FileField(upload_to='backups/%Y/%m/%d/')
    backup_created = models.DateTimeField(auto_now_add=True)
    backup_expires = models.DateTimeField()
    is_used_for_recovery = models.BooleanField(default=False)

    class Meta:
        ordering = ['-backup_created']

    def __str__(self):
        return f"Backup for {self.document.title}"

    def save(self, *args, **kwargs):
        """Set expiry date automatically if not set"""
        if not self.backup_expires:
            self.backup_expires = timezone.now() + timedelta(hours=48)
        super().save(*args, **kwargs)

    def is_expired(self):
        """Check if backup is expired"""
        return timezone.now() > self.backup_expires


class CompressionStats(models.Model):
    """Track compression performance metrics"""

    ALGORITHM_CHOICES = Document.COMPRESSION_ALGORITHM_CHOICES
    FILE_TYPE_CHOICES = Document.FILE_TYPE_CHOICES

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='compression_stats'
    )
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES)
    algorithm = models.CharField(max_length=10, choices=ALGORITHM_CHOICES)
    total_files = models.IntegerField(default=0)
    avg_compression_ratio = models.FloatField(default=0.0)
    total_original_size = models.BigIntegerField(default=0)
    total_compressed_size = models.BigIntegerField(default=0)
    avg_compression_time = models.FloatField(
        default=0.0,
        help_text='Average compression time in milliseconds'
    )
    failure_count = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Compression Statistics'
        unique_together = ('user', 'file_type', 'algorithm')
        indexes = [
            models.Index(fields=['user', 'file_type']),
            models.Index(fields=['user', 'algorithm']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.file_type} ({self.algorithm})"

    def update_stats(self, original_size, compressed_size, compression_time, failed=False):
        """Update statistics with new compression result"""
        if failed:
            self.failure_count += 1
        else:
            # Update running averages
            new_total = self.total_files + 1
            self.avg_compression_ratio = (
                (self.avg_compression_ratio * self.total_files + (compressed_size / original_size))
                / new_total
            )
            self.avg_compression_time = (
                (self.avg_compression_time * self.total_files + compression_time)
                / new_total
            )
            self.total_files = new_total
            self.total_original_size += original_size
            self.total_compressed_size += compressed_size

        self.save()
