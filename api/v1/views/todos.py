"""
ViewSets for Todos API endpoints.
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Case, When
from django.utils import timezone

from notes.models import Todo
from api.v1.serializers.todos import (
    TodoListSerializer,
    TodoDetailSerializer,
    TodoCreateUpdateSerializer,
    TodoBulkUpdateSerializer,
)
from api.permissions import IsOwnerOrReadOnly
from api.pagination import StandardResultsPagination


class TodoViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Todo model.

    Provides CRUD operations and additional actions for todos.
    """
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_completed', 'priority', 'status', 'note']
    search_fields = ['title', 'description', 'tags__name']
    ordering_fields = ['created', 'modified', 'due_date', 'priority', 'order']
    ordering = ['order', '-created']

    def get_queryset(self):
        """Get todos for current user."""
        queryset = Todo.objects.filter(user=self.request.user).select_related('note')

        # Filter by tags if provided
        tags = self.request.query_params.get('tags', None)
        if tags:
            tag_list = tags.split(',')
            queryset = queryset.filter(tags__name__in=tag_list).distinct()

        # Filter by due date range
        due_from = self.request.query_params.get('due_from', None)
        due_to = self.request.query_params.get('due_to', None)

        if due_from:
            queryset = queryset.filter(due_date__gte=due_from)
        if due_to:
            queryset = queryset.filter(due_date__lte=due_to)

        # Filter overdue todos
        show_overdue = self.request.query_params.get('overdue', None)
        if show_overdue == 'true':
            queryset = queryset.filter(
                due_date__lt=timezone.now(),
                is_completed=False
            )

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return TodoListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return TodoCreateUpdateSerializer
        elif self.action == 'bulk_update':
            return TodoBulkUpdateSerializer
        else:
            return TodoDetailSerializer

    def perform_create(self, serializer):
        """Save todo with current user."""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def toggle(self, request, pk=None):
        """Toggle completion status of a todo."""
        todo = self.get_object()
        todo.is_completed = not todo.is_completed
        todo.save()

        return Response({
            'success': True,
            'is_completed': todo.is_completed,
            'completed_at': todo.completed_at,
            'message': f'Todo marked as {"completed" if todo.is_completed else "incomplete"}.'
        })

    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """Bulk update multiple todos."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        todo_ids = serializer.validated_data['todo_ids']
        update_data = {k: v for k, v in serializer.validated_data.items() if k != 'todo_ids'}

        # Update only todos owned by current user
        updated_count = Todo.objects.filter(
            id__in=todo_ids,
            user=request.user
        ).update(**update_data)

        return Response({
            'success': True,
            'updated_count': updated_count,
            'message': f'{updated_count} todos updated successfully.'
        })

    @action(detail=False, methods=['get'])
    def standalone(self, request):
        """Get standalone todos (not linked to any note)."""
        todos = self.get_queryset().filter(note__isnull=True)

        page = self.paginate_queryset(todos)
        if page is not None:
            serializer = TodoListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = TodoListSerializer(todos, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='note/(?P<note_id>[^/.]+)')
    def by_note(self, request, note_id=None):
        """Get todos for a specific note."""
        todos = self.get_queryset().filter(note_id=note_id)

        page = self.paginate_queryset(todos)
        if page is not None:
            serializer = TodoListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = TodoListSerializer(todos, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get todo dashboard statistics."""
        user_todos = self.get_queryset()

        # Calculate statistics
        total_count = user_todos.count()
        completed_count = user_todos.filter(is_completed=True).count()
        pending_count = user_todos.filter(is_completed=False).count()
        overdue_count = user_todos.filter(
            due_date__lt=timezone.now(),
            is_completed=False
        ).count()

        # Count by priority
        priority_counts = {}
        for priority_key, priority_label in Todo.PRIORITY_CHOICES:
            priority_counts[priority_key] = user_todos.filter(priority=priority_key).count()

        # Count by status
        status_counts = {}
        for status_key, status_label in Todo.STATUS_CHOICES:
            status_counts[status_key] = user_todos.filter(status=status_key).count()

        # Recent todos
        recent_todos = user_todos.order_by('-created')[:5]
        recent_serializer = TodoListSerializer(recent_todos, many=True, context={'request': request})

        # Upcoming due todos
        upcoming_todos = user_todos.filter(
            due_date__gte=timezone.now(),
            is_completed=False
        ).order_by('due_date')[:5]
        upcoming_serializer = TodoListSerializer(upcoming_todos, many=True, context={'request': request})

        return Response({
            'statistics': {
                'total': total_count,
                'completed': completed_count,
                'pending': pending_count,
                'overdue': overdue_count,
                'completion_rate': (completed_count / total_count * 100) if total_count > 0 else 0,
                'by_priority': priority_counts,
                'by_status': status_counts,
            },
            'recent_todos': recent_serializer.data,
            'upcoming_dues': upcoming_serializer.data,
        })
