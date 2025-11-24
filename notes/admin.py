from django.contrib import admin
from django.utils.html import format_html
from .models import Notebook, Note, NoteAttachment, SharedNote, NoteVersion, Todo


@admin.register(Notebook)
class NotebookAdmin(admin.ModelAdmin):
    """Admin configuration for Notebook model."""
    
    list_display = ('name', 'user', 'get_note_count', 'is_default', 'created')
    list_filter = ('is_default', 'created', 'user')
    search_fields = ('name', 'description', 'user__email')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created', 'modified')
    
    def get_note_count(self, obj):
        return obj.get_note_count()
    get_note_count.short_description = 'Notes'


class NoteAttachmentInline(admin.TabularInline):
    """Inline admin for note attachments."""
    model = NoteAttachment
    extra = 0
    readonly_fields = ('file_size', 'file_type', 'created')


class SharedNoteInline(admin.TabularInline):
    """Inline admin for shared notes."""
    model = SharedNote
    extra = 0
    readonly_fields = ('created',)


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    """Admin configuration for Note model."""
    
    list_display = ('title', 'user', 'notebook', 'is_pinned', 'is_archived', 'get_word_count', 'modified')
    list_filter = ('is_pinned', 'is_archived', 'is_public', 'created', 'notebook', 'user')
    search_fields = ('title', 'content', 'user__email', 'tags__name')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('content_html', 'get_word_count', 'get_reading_time', 'created', 'modified')
    inlines = [NoteAttachmentInline, SharedNoteInline]
    
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'user', 'notebook')
        }),
        ('Content', {
            'fields': ('content', 'content_html', 'tags')
        }),
        ('Settings', {
            'fields': ('is_pinned', 'is_archived', 'is_public')
        }),
        ('Statistics', {
            'fields': ('get_word_count', 'get_reading_time'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created', 'modified'),
            'classes': ('collapse',)
        }),
    )
    
    def get_word_count(self, obj):
        return obj.get_word_count()
    get_word_count.short_description = 'Words'


@admin.register(NoteAttachment)
class NoteAttachmentAdmin(admin.ModelAdmin):
    """Admin configuration for NoteAttachment model."""
    
    list_display = ('original_name', 'note', 'get_file_size_human', 'file_type', 'created')
    list_filter = ('file_type', 'created')
    search_fields = ('original_name', 'note__title')
    readonly_fields = ('file_size', 'file_type', 'created', 'modified')


@admin.register(SharedNote)
class SharedNoteAdmin(admin.ModelAdmin):
    """Admin configuration for SharedNote model."""
    
    list_display = ('note', 'shared_with', 'permission', 'shared_by', 'created')
    list_filter = ('permission', 'created')
    search_fields = ('note__title', 'shared_with__email', 'shared_by__email')
    readonly_fields = ('created', 'modified')


@admin.register(NoteVersion)
class NoteVersionAdmin(admin.ModelAdmin):
    """Admin configuration for NoteVersion model."""
    
    list_display = ('note', 'version_number', 'title', 'created')
    list_filter = ('created',)
    search_fields = ('note__title', 'title', 'content')
    readonly_fields = ('created', 'modified')


@admin.register(Todo)
class TodoAdmin(admin.ModelAdmin):
    """Admin configuration for Todo model."""
    
    list_display = ('title', 'note', 'priority', 'status', 'is_completed', 'due_date', 'created')
    list_filter = ('priority', 'status', 'is_completed', 'created', 'due_date', 'note__notebook')
    search_fields = ('title', 'description', 'note__title', 'tags__name')
    readonly_fields = ('created', 'modified', 'completed_at')
    
    fieldsets = (
        (None, {
            'fields': ('title', 'note', 'description')
        }),
        ('Status & Priority', {
            'fields': ('priority', 'status', 'is_completed')
        }),
        ('Scheduling', {
            'fields': ('due_date', 'completed_at')
        }),
        ('Organization', {
            'fields': ('tags', 'order')
        }),
        ('Timestamps', {
            'fields': ('created', 'modified'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('note', 'note__notebook')
