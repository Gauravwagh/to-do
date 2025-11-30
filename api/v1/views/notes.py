"""
ViewSets for Notes API endpoints.
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404

from notes.models import (
    Note, Notebook, NoteAttachment, SharedNote, NoteVersion, Todo
)
from api.v1.serializers.notes import (
    NoteListSerializer,
    NoteDetailSerializer,
    NoteCreateUpdateSerializer,
    NoteCopySerializer,
    NoteMoveSerializer,
    NotebookListSerializer,
    NotebookDetailSerializer,
    NotebookCreateUpdateSerializer,
    NoteAttachmentSerializer,
    SharedNoteSerializer,
    NoteVersionSerializer,
    TodoSerializer,
)
from api.permissions import IsOwnerOrReadOnly
from api.pagination import StandardResultsPagination


class NoteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Note model.

    Provides CRUD operations and additional actions for notes.
    """
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_pinned', 'is_archived', 'is_public', 'notebook']
    search_fields = ['title', 'content', 'tags__name']
    ordering_fields = ['created', 'modified', 'title', 'is_pinned']
    ordering = ['-is_pinned', '-modified']

    def get_queryset(self):
        """Get notes for current user or shared with them."""
        user = self.request.user

        # Base queryset: user's own notes
        queryset = Note.objects.filter(user=user)

        # Add related data for efficiency
        queryset = queryset.select_related('notebook', 'user').prefetch_related(
            'tags', 'attachments', 'todos', 'shares'
        )

        # Filter by tags if provided
        tags = self.request.query_params.get('tags', None)
        if tags:
            tag_list = tags.split(',')
            queryset = queryset.filter(tags__name__in=tag_list).distinct()

        # Filter by notebook slug if provided
        notebook_slug = self.request.query_params.get('notebook_slug', None)
        if notebook_slug:
            queryset = queryset.filter(notebook__slug=notebook_slug)

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return NoteListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return NoteCreateUpdateSerializer
        elif self.action == 'copy':
            return NoteCopySerializer
        elif self.action == 'move':
            return NoteMoveSerializer
        else:
            return NoteDetailSerializer

    def perform_create(self, serializer):
        """Save note with current user."""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def pin(self, request, pk=None):
        """Toggle pin status of a note."""
        note = self.get_object()
        note.is_pinned = not note.is_pinned
        note.save(update_fields=['is_pinned', 'modified'])

        return Response({
            'success': True,
            'is_pinned': note.is_pinned,
            'message': f'Note {"pinned" if note.is_pinned else "unpinned"} successfully.'
        })

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Toggle archive status of a note."""
        note = self.get_object()
        note.is_archived = not note.is_archived
        note.save(update_fields=['is_archived', 'modified'])

        return Response({
            'success': True,
            'is_archived': note.is_archived,
            'message': f'Note {"archived" if note.is_archived else "unarchived"} successfully.'
        })

    @action(detail=True, methods=['post'])
    def copy(self, request, pk=None):
        """Copy a note."""
        original_note = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create a copy of the note
        new_note = Note.objects.create(
            title=serializer.validated_data.get('title', f"{original_note.title} (Copy)"),
            content=original_note.content,
            user=request.user,
            notebook=serializer.validated_data.get('notebook_id', original_note.notebook),
            is_public=False,  # Copies are private by default
        )

        # Copy tags
        for tag in original_note.tags.all():
            new_note.tags.add(tag)

        # Copy todos
        for todo in original_note.todos.all():
            Todo.objects.create(
                note=new_note,
                user=request.user,
                title=todo.title,
                description=todo.description,
                priority=todo.priority,
                due_date=todo.due_date,
            )

        response_serializer = NoteDetailSerializer(new_note, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        """Move note to a different notebook."""
        note = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        note.notebook = serializer.validated_data['notebook_id']
        note.save(update_fields=['notebook', 'modified'])

        response_serializer = NoteDetailSerializer(note, context={'request': request})
        return Response(response_serializer.data)

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """Get version history of a note."""
        note = self.get_object()
        versions = note.versions.all()

        page = self.paginate_queryset(versions)
        if page is not None:
            serializer = NoteVersionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = NoteVersionSerializer(versions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        """Share note with another user."""
        note = self.get_object()
        serializer = SharedNoteSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        # Create share
        shared_note = serializer.save(
            note=note,
            shared_by=request.user
        )

        return Response(
            SharedNoteSerializer(shared_note, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['delete'], url_path='share/(?P<user_id>[^/.]+)')
    def unshare(self, request, pk=None, user_id=None):
        """Unshare note with a user."""
        note = self.get_object()

        try:
            shared_note = SharedNote.objects.get(
                note=note,
                shared_with_id=user_id,
                shared_by=request.user
            )
            shared_note.delete()
            return Response({'success': True, 'message': 'Note unshared successfully.'})
        except SharedNote.DoesNotExist:
            return Response(
                {'error': 'Share not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def shared(self, request):
        """Get notes shared with current user."""
        shared_notes = SharedNote.objects.filter(
            shared_with=request.user
        ).select_related('note__user', 'note__notebook')

        notes = [share.note for share in shared_notes]

        page = self.paginate_queryset(notes)
        if page is not None:
            serializer = NoteListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = NoteListSerializer(notes, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def archived(self, request):
        """Get archived notes."""
        notes = self.get_queryset().filter(is_archived=True)

        page = self.paginate_queryset(notes)
        if page is not None:
            serializer = NoteListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = NoteListSerializer(notes, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Advanced search for notes."""
        query = request.query_params.get('q', '')

        if not query:
            return Response({'error': 'Search query is required.'}, status=status.HTTP_400_BAD_REQUEST)

        notes = self.get_queryset().filter(
            Q(title__icontains=query) |
            Q(content__icontains=query) |
            Q(tags__name__icontains=query)
        ).distinct()

        page = self.paginate_queryset(notes)
        if page is not None:
            serializer = NoteListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = NoteListSerializer(notes, many=True, context={'request': request})
        return Response(serializer.data)


class NotebookViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Notebook model.

    Provides CRUD operations for notebooks.
    """
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    pagination_class = StandardResultsPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created', 'modified']
    ordering = ['name']

    def get_queryset(self):
        """Get notebooks for current user."""
        return Notebook.objects.filter(user=self.request.user).annotate(
            note_count=Count('notes')
        )

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return NotebookListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return NotebookCreateUpdateSerializer
        else:
            return NotebookDetailSerializer

    def perform_create(self, serializer):
        """Save notebook with current user."""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['get'])
    def notes(self, request, pk=None):
        """Get all notes in this notebook."""
        notebook = self.get_object()
        notes = notebook.notes.all().select_related('user').prefetch_related('tags', 'attachments')

        page = self.paginate_queryset(notes)
        if page is not None:
            serializer = NoteListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = NoteListSerializer(notes, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reorder(self, request, pk=None):
        """Reorder notebooks (for future implementation)."""
        # This would require adding an order field to Notebook model
        return Response({'message': 'Reorder functionality coming soon.'})


class NoteAttachmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for NoteAttachment model.

    Provides CRUD operations for note attachments.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = NoteAttachmentSerializer
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        """Get attachments for notes owned by current user."""
        note_id = self.kwargs.get('note_pk')
        if note_id:
            return NoteAttachment.objects.filter(
                note_id=note_id,
                note__user=self.request.user
            )
        return NoteAttachment.objects.filter(note__user=self.request.user)

    def perform_create(self, serializer):
        """Save attachment to specified note."""
        note_id = self.kwargs.get('note_pk')
        note = get_object_or_404(Note, pk=note_id, user=self.request.user)
        serializer.save(note=note)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None, note_pk=None):
        """Download attachment file."""
        attachment = self.get_object()

        # Return file URL for download
        return Response({
            'file_url': request.build_absolute_uri(attachment.file.url),
            'filename': attachment.original_name,
            'file_size': attachment.file_size,
        })

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None, note_pk=None):
        """Get attachment preview if available."""
        attachment = self.get_object()

        if not attachment.is_previewable():
            return Response(
                {'error': 'This file type cannot be previewed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = {
            'file_url': request.build_absolute_uri(attachment.file.url),
            'file_type': attachment.file_type,
            'is_image': attachment.is_image,
        }

        if attachment.thumbnail:
            data['thumbnail_url'] = request.build_absolute_uri(attachment.thumbnail.url)

        return Response(data)
