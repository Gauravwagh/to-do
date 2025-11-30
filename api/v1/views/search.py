"""
ViewSets for Search API endpoints.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from notes.models import Note, Todo
from api.v1.serializers.notes import NoteListSerializer
from api.v1.serializers.todos import TodoListSerializer
from api.pagination import StandardResultsPagination


class SearchViewSet(viewsets.ViewSet):
    """
    ViewSet for global search functionality.

    Provides search across notes, todos, and other content.
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsPagination

    @action(detail=False, methods=['get'])
    def global_search(self, request):
        """
        Perform global search across all content types.

        Query params:
            q: Search query string
            types: Comma-separated list of content types to search (notes, todos)
        """
        query = request.query_params.get('q', '')

        if not query:
            return Response(
                {'error': 'Search query is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get content types to search
        content_types = request.query_params.get('types', 'notes,todos')
        types_list = [t.strip() for t in content_types.split(',')]

        results = {
            'query': query,
            'results': {}
        }

        # Search notes
        if 'notes' in types_list:
            notes = Note.objects.filter(
                user=request.user
            ).filter(
                Q(title__icontains=query) |
                Q(content__icontains=query) |
                Q(tags__name__icontains=query)
            ).distinct().select_related('notebook', 'user').prefetch_related('tags')[:20]

            results['results']['notes'] = {
                'count': notes.count(),
                'items': NoteListSerializer(notes, many=True, context={'request': request}).data
            }

        # Search todos
        if 'todos' in types_list:
            todos = Todo.objects.filter(
                user=request.user
            ).filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(tags__name__icontains=query)
            ).distinct().select_related('note')[:20]

            results['results']['todos'] = {
                'count': todos.count(),
                'items': TodoListSerializer(todos, many=True, context={'request': request}).data
            }

        # Calculate total results
        total_count = sum(
            results['results'].get(t, {}).get('count', 0)
            for t in types_list if t in results['results']
        )
        results['total_count'] = total_count

        return Response(results)

    @action(detail=False, methods=['get'])
    def notes(self, request):
        """Search notes only."""
        query = request.query_params.get('q', '')

        if not query:
            return Response(
                {'error': 'Search query is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        notes = Note.objects.filter(
            user=request.user
        ).filter(
            Q(title__icontains=query) |
            Q(content__icontains=query) |
            Q(tags__name__icontains=query)
        ).distinct().select_related('notebook', 'user').prefetch_related('tags')

        # Paginate results
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(notes, request)

        if page is not None:
            serializer = NoteListSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)

        serializer = NoteListSerializer(notes, many=True, context={'request': request})
        return Response({
            'query': query,
            'count': notes.count(),
            'results': serializer.data
        })

    @action(detail=False, methods=['get'])
    def todos(self, request):
        """Search todos only."""
        query = request.query_params.get('q', '')

        if not query:
            return Response(
                {'error': 'Search query is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        todos = Todo.objects.filter(
            user=request.user
        ).filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(tags__name__icontains=query)
        ).distinct().select_related('note')

        # Paginate results
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(todos, request)

        if page is not None:
            serializer = TodoListSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)

        serializer = TodoListSerializer(todos, many=True, context={'request': request})
        return Response({
            'query': query,
            'count': todos.count(),
            'results': serializer.data
        })
