from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.text import slugify
from django.core.validators import FileExtensionValidator
from taggit.managers import TaggableManager
from core.models import TimeStampedModel
from core.utils import generate_unique_slug, get_file_path
import bleach

User = get_user_model()


class Notebook(TimeStampedModel):
    """Notebook model to organize notes."""
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notebooks')
    is_default = models.BooleanField(default=False)
    color = models.CharField(
        max_length=7, 
        default='#007bff',
        help_text='Hex color code for notebook theme'
    )
    
    class Meta:
        ordering = ['name']
        unique_together = ['user', 'name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, 'name')
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('notes:notebook_detail', kwargs={'slug': self.slug})
    
    def get_note_count(self):
        return self.notes.count()


class Note(TimeStampedModel):
    """Main note model."""
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, blank=True)
    content = models.TextField(blank=True)
    content_html = models.TextField(blank=True, help_text='HTML version of content')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    notebook = models.ForeignKey(
        Notebook, 
        on_delete=models.CASCADE, 
        related_name='notes',
        null=True,
        blank=True
    )
    is_pinned = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)
    
    # Tagging support
    tags = TaggableManager(blank=True)
    
    class Meta:
        ordering = ['-is_pinned', '-modified']
        unique_together = ['user', 'slug']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, 'title')
        
        # Clean HTML content
        if self.content:
            allowed_tags = [
                'p', 'br', 'strong', 'em', 'u', 'strike', 'ul', 'ol', 'li',
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'code',
                'pre', 'a', 'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td'
            ]
            allowed_attributes = {
                'a': ['href', 'title'],
                'img': ['src', 'alt', 'width', 'height'],
                '*': ['class', 'id']
            }
            self.content_html = bleach.clean(
                self.content, 
                tags=allowed_tags, 
                attributes=allowed_attributes,
                strip=True
            )
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('notes:note_detail', kwargs={'slug': self.slug})
    
    def get_word_count(self):
        """Return approximate word count."""
        if self.content:
            return len(self.content.split())
        return 0
    
    def get_reading_time(self):
        """Estimate reading time in minutes."""
        words = self.get_word_count()
        return max(1, words // 200)  # Average reading speed: 200 words/minute


class NoteAttachment(TimeStampedModel):
    """File attachments for notes."""
    
    # File type choices
    TYPE_CHOICES = [
        ('image', 'Image'),
        ('document', 'Document'),
        ('audio', 'Audio'),
        ('video', 'Video'),
        ('archive', 'Archive'),
        ('other', 'Other'),
    ]
    
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(
        upload_to=get_file_path,
        validators=[FileExtensionValidator(
            allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg',  # Images
                              'pdf', 'doc', 'docx', 'txt', 'rtf', 'odt',  # Documents
                              'mp3', 'wav', 'ogg', 'm4a',  # Audio
                              'mp4', 'avi', 'mov', 'wmv', 'mkv',  # Video
                              'zip', 'rar', '7z', 'tar', 'gz']  # Archives
        )]
    )
    original_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    file_type = models.CharField(max_length=100)
    attachment_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='other')
    description = models.TextField(blank=True)
    is_image = models.BooleanField(default=False)
    thumbnail = models.ImageField(upload_to='thumbnails/', blank=True, null=True)
    
    class Meta:
        ordering = ['-created']
    
    def __str__(self):
        return f'{self.note.title} - {self.original_name}'
    
    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
            
            # Get file type from the file object
            try:
                # Try to get content type from the file
                if hasattr(self.file, 'content_type'):
                    self.file_type = self.file.content_type
                else:
                    # Fallback: use mimetypes to guess from filename
                    import mimetypes
                    guessed_type, _ = mimetypes.guess_type(self.file.name)
                    self.file_type = guessed_type or 'application/octet-stream'
            except:
                self.file_type = 'application/octet-stream'
            
            if not self.original_name:
                self.original_name = self.file.name
            
            # Determine if it's an image
            self.is_image = self.file_type.startswith('image/')
            
            # Determine attachment type
            self.attachment_type = self._get_attachment_type()
            
            # Create thumbnail for images
            if self.is_image:
                self._create_thumbnail()
                
        super().save(*args, **kwargs)
    
    def _get_attachment_type(self):
        """Determine attachment type based on file type."""
        if self.file_type.startswith('image/'):
            return 'image'
        elif self.file_type.startswith('audio/'):
            return 'audio'
        elif self.file_type.startswith('video/'):
            return 'video'
        elif self.file_type in ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
            return 'document'
        elif self.file_type in ['application/zip', 'application/x-rar-compressed', 'application/x-7z-compressed']:
            return 'archive'
        else:
            return 'other'
    
    def _create_thumbnail(self):
        """Create thumbnail for images."""
        try:
            from PIL import Image
            import io
            from django.core.files.base import ContentFile
            
            # Open the image
            image = Image.open(self.file)
            
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            
            # Create thumbnail
            image.thumbnail((200, 200), Image.Resampling.LANCZOS)
            
            # Save thumbnail
            thumb_io = io.BytesIO()
            image.save(thumb_io, format='JPEG', quality=85)
            thumb_io.seek(0)
            
            # Generate thumbnail filename
            thumb_name = f"thumb_{self.original_name}.jpg"
            self.thumbnail.save(thumb_name, ContentFile(thumb_io.getvalue()), save=False)
            
        except Exception as e:
            # If thumbnail creation fails, continue without it
            pass
    
    def get_file_size_human(self):
        """Return human readable file size."""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f'{size:.1f} {unit}'
            size /= 1024.0
        return f'{size:.1f} TB'
    
    def get_file_icon(self):
        """Return appropriate icon for file type."""
        icons = {
            'image': 'fas fa-image',
            'document': 'fas fa-file-alt',
            'audio': 'fas fa-music',
            'video': 'fas fa-video',
            'archive': 'fas fa-file-archive',
            'other': 'fas fa-file',
        }
        return icons.get(self.attachment_type, 'fas fa-file')
    
    def is_previewable(self):
        """Check if file can be previewed in browser."""
        return self.is_image or self.file_type in [
            'text/plain', 'text/html', 'application/pdf'
        ]


class SharedNote(TimeStampedModel):
    """Model for sharing notes with other users."""
    
    PERMISSION_CHOICES = [
        ('view', 'View Only'),
        ('edit', 'Can Edit'),
    ]
    
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name='shares')
    shared_with = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shared_notes')
    permission = models.CharField(max_length=10, choices=PERMISSION_CHOICES, default='view')
    shared_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes_shared')
    
    class Meta:
        unique_together = ['note', 'shared_with']
    
    def __str__(self):
        return f'{self.note.title} shared with {self.shared_with.email}'


class NoteVersion(TimeStampedModel):
    """Version history for notes."""
    
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name='versions')
    title = models.CharField(max_length=200)
    content = models.TextField()
    version_number = models.PositiveIntegerField()
    
    class Meta:
        ordering = ['-version_number']
        unique_together = ['note', 'version_number']
    
    def __str__(self):
        return f'{self.note.title} - v{self.version_number}'


class Todo(TimeStampedModel):
    """Todo/Task model for both note-based and standalone task management."""
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name='todos', null=True, blank=True)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='todos', default=1)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_completed = models.BooleanField(default=False)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    due_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    tags = TaggableManager(blank=True)
    
    class Meta:
        ordering = ['order', '-created']
        unique_together = ['user', 'note', 'title']
    
    def is_standalone(self):
        """Check if this is a standalone todo (not linked to a note)."""
        return self.note is None
    
    def __str__(self):
        status_icon = '✅' if self.is_completed else '⏳'
        return f'{status_icon} {self.title}'
    
    def save(self, *args, **kwargs):
        # Auto-set completion timestamp
        if self.is_completed and not self.completed_at:
            from django.utils import timezone
            self.completed_at = timezone.now()
        elif not self.is_completed and self.completed_at:
            self.completed_at = None
            
        # Auto-set status based on completion
        if self.is_completed and self.status != 'completed':
            self.status = 'completed'
        elif not self.is_completed and self.status == 'completed':
            self.status = 'pending'
            
        super().save(*args, **kwargs)
    
    @property
    def is_overdue(self):
        """Check if todo is overdue."""
        if self.due_date and not self.is_completed:
            from django.utils import timezone
            return self.due_date < timezone.now()
        return False
    
    @property
    def days_until_due(self):
        """Get days until due date."""
        if self.due_date:
            from django.utils import timezone
            delta = self.due_date.date() - timezone.now().date()
            return delta.days
        return None
    
    def get_priority_color(self):
        """Get Bootstrap color class for priority."""
        colors = {
            'low': 'success',
            'medium': 'info',
            'high': 'warning',
            'urgent': 'danger',
        }
        return colors.get(self.priority, 'secondary')
    
    def get_status_color(self):
        """Get Bootstrap color class for status."""
        colors = {
            'pending': 'secondary',
            'in_progress': 'primary',
            'completed': 'success',
            'cancelled': 'danger',
        }
        return colors.get(self.status, 'secondary')
