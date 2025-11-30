"""
Serializers for Todos API endpoints.
"""
from rest_framework import serializers
from notes.models import Todo
from taggit.serializers import TagListSerializerField, TaggitSerializer


class TodoListSerializer(TaggitSerializer, serializers.ModelSerializer):
    """Serializer for todo list view."""

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
            'is_standalone', 'note', 'created', 'modified'
        )
        read_only_fields = (
            'id', 'completed_at', 'created', 'modified'
        )


class TodoDetailSerializer(TaggitSerializer, serializers.ModelSerializer):
    """Detailed serializer for todo."""

    tags = TagListSerializerField(required=False)
    is_overdue = serializers.BooleanField(read_only=True)
    days_until_due = serializers.IntegerField(read_only=True)
    priority_color = serializers.CharField(source='get_priority_color', read_only=True)
    status_color = serializers.CharField(source='get_status_color', read_only=True)
    is_standalone = serializers.BooleanField(read_only=True)
    note_title = serializers.CharField(source='note.title', read_only=True, allow_null=True)

    class Meta:
        model = Todo
        fields = (
            'id', 'title', 'description', 'is_completed', 'priority',
            'status', 'due_date', 'completed_at', 'order', 'tags',
            'is_overdue', 'days_until_due', 'priority_color', 'status_color',
            'is_standalone', 'note', 'note_title', 'created', 'modified'
        )
        read_only_fields = (
            'id', 'completed_at', 'created', 'modified'
        )


class TodoCreateUpdateSerializer(TaggitSerializer, serializers.ModelSerializer):
    """Serializer for creating/updating todos."""

    tags = TagListSerializerField(required=False)

    class Meta:
        model = Todo
        fields = (
            'title', 'description', 'is_completed', 'priority',
            'status', 'due_date', 'order', 'tags', 'note'
        )

    def validate_note(self, value):
        """Ensure note belongs to current user."""
        if value and value.user != self.context['request'].user:
            raise serializers.ValidationError("You can only add todos to your own notes.")
        return value

    def create(self, validated_data):
        """Create todo with current user."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class TodoBulkUpdateSerializer(serializers.Serializer):
    """Serializer for bulk updating todos."""

    todo_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True
    )
    is_completed = serializers.BooleanField(required=False)
    status = serializers.ChoiceField(
        choices=Todo.STATUS_CHOICES,
        required=False
    )
    priority = serializers.ChoiceField(
        choices=Todo.PRIORITY_CHOICES,
        required=False
    )

    def validate(self, data):
        """Ensure at least one update field is provided."""
        update_fields = ['is_completed', 'status', 'priority']
        if not any(field in data for field in update_fields):
            raise serializers.ValidationError(
                "At least one update field must be provided."
            )
        return data
