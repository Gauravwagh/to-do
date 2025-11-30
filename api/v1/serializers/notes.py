"""
Serializers for Notes API endpoints.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from notes.models import (
    Note, Notebook, NoteAttachment, SharedNote, NoteVersion, Todo
)
from taggit.serializers import TagListSerializerField, TaggitSerializer

User = get_user_model()


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user serializer for nested relationships."""

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name')
        read_only_fields = fields


class NotebookListSerializer(serializers.ModelSerializer):
    """Serializer for notebook list view."""

    note_count = serializers.IntegerField(source='get_note_count', read_only=True)

    class Meta:
        model = Notebook
        fields = (
            'id', 'name', 'slug', 'description', 'color',
            'is_default', 'note_count', 'created', 'modified'
        )
        read_only_fields = ('id', 'slug', 'created', 'modified')


class NotebookDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for notebook."""

    note_count = serializers.IntegerField(source='get_note_count', read_only=True)
    user = UserMinimalSerializer(read_only=True)

    class Meta:
        model = Notebook
        fields = (
            'id', 'name', 'slug', 'description', 'color',
            'is_default', 'note_count', 'user', 'created', 'modified'
        )
        read_only_fields = ('id', 'slug', 'user', 'created', 'modified')


class NotebookCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating notebooks."""

    class Meta:
        model = Notebook
        fields = ('name', 'description', 'color', 'is_default')

    def validate_is_default(self, value):
        """Ensure only one default notebook per user."""
        user = self.context['request'].user
        if value:
            # Check if user already has a default notebook
            existing_default = Notebook.objects.filter(
                user=user, is_default=True
            ).exclude(pk=self.instance.pk if self.instance else None)

            if existing_default.exists():
                raise serializers.ValidationError(
                    "You already have a default notebook. Please unset the current default first."
                )
        return value


class NoteAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for note attachments."""

    file_size_human = serializers.CharField(source='get_file_size_human', read_only=True)
    file_icon = serializers.CharField(source='get_file_icon', read_only=True)
    is_previewable = serializers.BooleanField(read_only=True)
    file_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = NoteAttachment
        fields = (
            'id', 'file', 'original_name', 'file_size', 'file_size_human',
            'file_type', 'attachment_type', 'description', 'is_image',
            'thumbnail', 'file_icon', 'is_previewable', 'file_url',
            'thumbnail_url', 'created', 'modified'
        )
        read_only_fields = (
            'id', 'file_size', 'file_type', 'attachment_type',
            'is_image', 'thumbnail', 'created', 'modified'
        )

    def get_file_url(self, obj):
        """Get absolute URL for file."""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None

    def get_thumbnail_url(self, obj):
        """Get absolute URL for thumbnail."""
        if obj.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
            return obj.thumbnail.url
        return None


class TodoSerializer(serializers.ModelSerializer):
    """Serializer for todos."""

    tags = TagListSerializerField(required=False)
    is_overdue = serializers.BooleanField(read_only=True)
    days_until_due = serializers.IntegerField(read_only=True)
    priority_color = serializers.CharField(source='get_priority_color', read_only=True)
    status_color = serializers.CharField(source='get_status_color', read_only=True)
    is_standalone = serializers.BooleanField(read_only=True)

    class Meta:
        model = Todo
        fields = (
            'id', 'title', 'description', 'is_completed', 'priority',
            'status', 'due_date', 'completed_at', 'order', 'tags',
            'is_overdue', 'days_until_due', 'priority_color', 'status_color',
            'is_standalone', 'created', 'modified'
        )
        read_only_fields = (
            'id', 'completed_at', 'created', 'modified'
        )


class SharedNoteSerializer(serializers.ModelSerializer):
    """Serializer for shared notes."""

    shared_with = UserMinimalSerializer(read_only=True)
    shared_by = UserMinimalSerializer(read_only=True)
    shared_with_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='shared_with',
        write_only=True
    )

    class Meta:
        model = SharedNote
        fields = (
            'id', 'shared_with', 'shared_with_id', 'shared_by',
            'permission', 'created', 'modified'
        )
        read_only_fields = ('id', 'shared_by', 'created', 'modified')


class NoteVersionSerializer(serializers.ModelSerializer):
    """Serializer for note versions."""

    class Meta:
        model = NoteVersion
        fields = ('id', 'title', 'content', 'version_number', 'created')
        read_only_fields = fields


class NoteListSerializer(TaggitSerializer, serializers.ModelSerializer):
    """Serializer for note list view (lighter payload)."""

    tags = TagListSerializerField(required=False)
    notebook = NotebookListSerializer(read_only=True)
    user = UserMinimalSerializer(read_only=True)
    word_count = serializers.IntegerField(source='get_word_count', read_only=True)
    reading_time = serializers.IntegerField(source='get_reading_time', read_only=True)
    attachment_count = serializers.SerializerMethodField()
    todo_count = serializers.SerializerMethodField()

    class Meta:
        model = Note
        fields = (
            'id', 'title', 'slug', 'content', 'user', 'notebook',
            'is_pinned', 'is_archived', 'is_public', 'tags',
            'word_count', 'reading_time', 'attachment_count',
            'todo_count', 'created', 'modified'
        )
        read_only_fields = ('id', 'slug', 'user', 'created', 'modified')

    def get_attachment_count(self, obj):
        """Get count of attachments."""
        return obj.attachments.count()

    def get_todo_count(self, obj):
        """Get count of todos."""
        return obj.todos.count()


class NoteDetailSerializer(TaggitSerializer, serializers.ModelSerializer):
    """Detailed serializer for note with all related data."""

    tags = TagListSerializerField(required=False)
    notebook = NotebookListSerializer(read_only=True)
    user = UserMinimalSerializer(read_only=True)
    attachments = NoteAttachmentSerializer(many=True, read_only=True)
    todos = TodoSerializer(many=True, read_only=True)
    shares = SharedNoteSerializer(many=True, read_only=True)
    word_count = serializers.IntegerField(source='get_word_count', read_only=True)
    reading_time = serializers.IntegerField(source='get_reading_time', read_only=True)

    class Meta:
        model = Note
        fields = (
            'id', 'title', 'slug', 'content', 'content_html', 'user',
            'notebook', 'is_pinned', 'is_archived', 'is_public', 'tags',
            'attachments', 'todos', 'shares', 'word_count', 'reading_time',
            'created', 'modified'
        )
        read_only_fields = ('id', 'slug', 'content_html', 'user', 'created', 'modified')


class NoteCreateUpdateSerializer(TaggitSerializer, serializers.ModelSerializer):
    """Serializer for creating/updating notes."""

    tags = TagListSerializerField(required=False)
    notebook_id = serializers.PrimaryKeyRelatedField(
        queryset=Notebook.objects.all(),
        source='notebook',
        required=False,
        allow_null=True
    )

    class Meta:
        model = Note
        fields = (
            'title', 'content', 'notebook_id', 'is_pinned',
            'is_archived', 'is_public', 'tags'
        )

    def validate_notebook_id(self, value):
        """Ensure notebook belongs to current user."""
        if value and value.user != self.context['request'].user:
            raise serializers.ValidationError("You can only add notes to your own notebooks.")
        return value

    def create(self, validated_data):
        """Create note with current user."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class NoteCopySerializer(serializers.Serializer):
    """Serializer for copying a note."""

    title = serializers.CharField(required=False)
    notebook_id = serializers.PrimaryKeyRelatedField(
        queryset=Notebook.objects.all(),
        required=False,
        allow_null=True
    )

    def validate_notebook_id(self, value):
        """Ensure notebook belongs to current user."""
        if value and value.user != self.context['request'].user:
            raise serializers.ValidationError("You can only copy notes to your own notebooks.")
        return value


class NoteMoveSerializer(serializers.Serializer):
    """Serializer for moving a note to different notebook."""

    notebook_id = serializers.PrimaryKeyRelatedField(
        queryset=Notebook.objects.all(),
        required=True
    )

    def validate_notebook_id(self, value):
        """Ensure notebook belongs to current user."""
        if value.user != self.context['request'].user:
            raise serializers.ValidationError("You can only move notes to your own notebooks.")
        return value
