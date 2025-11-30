"""
ViewSets for Tags API endpoints.
"""
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count
from taggit.models import Tag

from notes.models import Note, Todo
from api.v1.serializers.tags import TagSerializer
from api.v1.serializers.notes import NoteListSerializer
from api.v1.serializers.todos import TodoListSerializer
from api.pagination import StandardResultsPagination


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Tag model.

    Provides read-only operations for tags.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TagSerializer
    pagination_class = StandardResultsPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']
    ordering = ['name']

    def get_queryset(self):
        """Get all tags used by current user's content."""
        user = self.request.user

        # Get tags from user's notes
        note_tags = Tag.objects.filter(
            taggit_taggeditem_items__content_type__model='note',
            taggit_taggeditem_items__object_id__in=Note.objects.filter(user=user).values_list('id', flat=True)
        )

        # Get tags from user's todos
        todo_tags = Tag.objects.filter(
            taggit_taggeditem_items__content_type__model='todo',
            taggit_taggeditem_items__object_id__in=Todo.objects.filter(user=user).values_list('id', flat=True)
        )

        # Combine and return unique tags
        tags = (note_tags | todo_tags).distinct()

        # Annotate with usage count
        tags = tags.annotate(
            usage_count=Count('taggit_taggeditem_items')
        )

        return tags

    @action(detail=True, methods=['get'])
    def notes(self, request, pk=None):
        """Get all notes with this tag."""
        tag = self.get_object()
        notes = Note.objects.filter(
            user=request.user,
            tags__in=[tag]
        ).select_related('notebook', 'user').prefetch_related('tags', 'attachments')

        page = self.paginate_queryset(notes)
        if page is not None:
            serializer = NoteListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = NoteListSerializer(notes, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def todos(self, request, pk=None):
        """Get all todos with this tag."""
        tag = self.get_object()
        todos = Todo.objects.filter(
            user=request.user,
            tags__in=[tag]
        ).select_related('note')

        page = self.paginate_queryset(todos)
        if page is not None:
            serializer = TodoListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = TodoListSerializer(todos, many=True, context={'request': request})
        return Response(serializer.data)
