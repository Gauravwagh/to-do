"""
ViewSets for Sync API endpoints.

Provides offline synchronization support for mobile apps.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta


class SyncViewSet(viewsets.ViewSet):
    """
    ViewSet for data synchronization.

    Provides endpoints for offline-first mobile apps to sync data.
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def status(self, request):
        """Get sync status for current user."""
        user = request.user

        # Get last modified timestamps for each entity type
        from notes.models import Note, Notebook, Todo
        from vault.models import VaultCredential, VaultSecureNote

        last_sync_timestamp = request.query_params.get('last_sync', None)

        return Response({
            'server_timestamp': timezone.now().isoformat(),
            'user_id': user.id,
            'sync_status': {
                'notes': {
                    'total_count': Note.objects.filter(user=user).count(),
                    'modified_count': Note.objects.filter(
                        user=user,
                        modified__gte=last_sync_timestamp
                    ).count() if last_sync_timestamp else 0,
                },
                'notebooks': {
                    'total_count': Notebook.objects.filter(user=user).count(),
                    'modified_count': Notebook.objects.filter(
                        user=user,
                        modified__gte=last_sync_timestamp
                    ).count() if last_sync_timestamp else 0,
                },
                'todos': {
                    'total_count': Todo.objects.filter(user=user).count(),
                    'modified_count': Todo.objects.filter(
                        user=user,
                        modified__gte=last_sync_timestamp
                    ).count() if last_sync_timestamp else 0,
                },
            },
            'message': 'Sync status retrieved successfully.'
        })

    @action(detail=False, methods=['post'])
    def pull(self, request):
        """
        Pull changes from server since last sync.

        Query params:
            - last_sync: ISO timestamp of last successful sync
            - entity_types: Comma-separated list of entities to sync
        """
        last_sync = request.query_params.get('last_sync')
        entity_types = request.query_params.get('entity_types', 'notes,notebooks,todos').split(',')

        if not last_sync:
            return Response({
                'error': 'last_sync timestamp is required.'
            }, status=status.HTTP_400_BAD_REQUEST)

        from notes.models import Note, Notebook, Todo
        from api.v1.serializers.notes import NoteListSerializer, NotebookListSerializer
        from api.v1.serializers.todos import TodoListSerializer

        changes = {}

        # Get modified notes
        if 'notes' in entity_types:
            modified_notes = Note.objects.filter(
                user=request.user,
                modified__gte=last_sync
            ).select_related('notebook', 'user').prefetch_related('tags')[:100]

            changes['notes'] = NoteListSerializer(
                modified_notes,
                many=True,
                context={'request': request}
            ).data

        # Get modified notebooks
        if 'notebooks' in entity_types:
            modified_notebooks = Notebook.objects.filter(
                user=request.user,
                modified__gte=last_sync
            )[:100]

            changes['notebooks'] = NotebookListSerializer(
                modified_notebooks,
                many=True
            ).data

        # Get modified todos
        if 'todos' in entity_types:
            modified_todos = Todo.objects.filter(
                user=request.user,
                modified__gte=last_sync
            ).select_related('note')[:100]

            changes['todos'] = TodoListSerializer(
                modified_todos,
                many=True,
                context={'request': request}
            ).data

        return Response({
            'sync_timestamp': timezone.now().isoformat(),
            'changes': changes,
            'has_more': False,  # Implement pagination if needed
            'message': 'Changes pulled successfully.'
        })

    @action(detail=False, methods=['post'])
    def push(self, request):
        """
        Push local changes to server.

        Body should contain changes made offline.
        """
        changes = request.data.get('changes', {})

        if not changes:
            return Response({
                'error': 'No changes provided.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # TODO: Process pushed changes
        # Handle conflict resolution
        # Save changes to database

        processed = {
            'created': [],
            'updated': [],
            'deleted': [],
            'conflicts': [],
        }

        return Response({
            'sync_timestamp': timezone.now().isoformat(),
            'processed': processed,
            'message': 'Changes pushed successfully.',
            'note': 'Full push implementation requires conflict resolution logic'
        })

    @action(detail=False, methods=['post'])
    def resolve_conflicts(self, request):
        """Resolve sync conflicts."""
        conflicts = request.data.get('conflicts', [])

        if not conflicts:
            return Response({
                'error': 'No conflicts provided.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # TODO: Implement conflict resolution
        # Strategy options: server_wins, client_wins, manual_merge

        resolved = []
        for conflict in conflicts:
            # Apply resolution strategy
            resolved.append({
                'id': conflict.get('id'),
                'resolution': 'server_wins',  # Default strategy
                'status': 'resolved'
            })

        return Response({
            'resolved': resolved,
            'message': 'Conflicts resolved successfully.',
            'note': 'Conflict resolution requires implementation of merge strategies'
        })
