"""
ViewSets for Statistics and Dashboard API endpoints.
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q, Sum
from django.utils import timezone
from datetime import timedelta

from notes.models import Note, Notebook, Todo


class StatisticsViewSet(viewsets.ViewSet):
    """
    ViewSet for statistics and dashboard data.

    Provides various statistics endpoints.
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """
        Get comprehensive dashboard statistics.

        Returns statistics for notes, todos, notebooks, and activity.
        """
        user = request.user

        # Notes statistics
        notes_total = Note.objects.filter(user=user).count()
        notes_pinned = Note.objects.filter(user=user, is_pinned=True).count()
        notes_archived = Note.objects.filter(user=user, is_archived=True).count()
        notes_public = Note.objects.filter(user=user, is_public=True).count()

        # Todos statistics
        todos_total = Todo.objects.filter(user=user).count()
        todos_completed = Todo.objects.filter(user=user, is_completed=True).count()
        todos_pending = Todo.objects.filter(user=user, is_completed=False).count()
        todos_overdue = Todo.objects.filter(
            user=user,
            due_date__lt=timezone.now(),
            is_completed=False
        ).count()

        # Notebooks statistics
        notebooks_total = Notebook.objects.filter(user=user).count()
        notebooks_with_notes = Notebook.objects.filter(
            user=user
        ).annotate(note_count=Count('notes')).filter(note_count__gt=0).count()

        # Activity statistics (last 7 days)
        seven_days_ago = timezone.now() - timedelta(days=7)
        notes_created_week = Note.objects.filter(
            user=user,
            created__gte=seven_days_ago
        ).count()
        todos_created_week = Todo.objects.filter(
            user=user,
            created__gte=seven_days_ago
        ).count()
        todos_completed_week = Todo.objects.filter(
            user=user,
            completed_at__gte=seven_days_ago
        ).count()

        # Recent activity
        recent_notes = Note.objects.filter(user=user).order_by('-modified')[:5].values(
            'id', 'title', 'slug', 'modified', 'is_pinned'
        )
        recent_todos = Todo.objects.filter(user=user).order_by('-modified')[:5].values(
            'id', 'title', 'is_completed', 'priority', 'modified'
        )

        # Tags statistics
        from taggit.models import Tag
        note_tags_count = Tag.objects.filter(
            taggit_taggeditem_items__content_type__model='note',
            taggit_taggeditem_items__object_id__in=Note.objects.filter(user=user).values_list('id', flat=True)
        ).distinct().count()

        todo_tags_count = Tag.objects.filter(
            taggit_taggeditem_items__content_type__model='todo',
            taggit_taggeditem_items__object_id__in=Todo.objects.filter(user=user).values_list('id', flat=True)
        ).distinct().count()

        # Top tags
        top_note_tags = Tag.objects.filter(
            taggit_taggeditem_items__content_type__model='note',
            taggit_taggeditem_items__object_id__in=Note.objects.filter(user=user).values_list('id', flat=True)
        ).annotate(
            usage_count=Count('taggit_taggeditem_items')
        ).order_by('-usage_count')[:10].values('name', 'usage_count')

        return Response({
            'notes': {
                'total': notes_total,
                'pinned': notes_pinned,
                'archived': notes_archived,
                'public': notes_public,
                'created_this_week': notes_created_week,
            },
            'todos': {
                'total': todos_total,
                'completed': todos_completed,
                'pending': todos_pending,
                'overdue': todos_overdue,
                'completion_rate': (todos_completed / todos_total * 100) if todos_total > 0 else 0,
                'created_this_week': todos_created_week,
                'completed_this_week': todos_completed_week,
            },
            'notebooks': {
                'total': notebooks_total,
                'with_notes': notebooks_with_notes,
                'empty': notebooks_total - notebooks_with_notes,
            },
            'tags': {
                'note_tags': note_tags_count,
                'todo_tags': todo_tags_count,
                'total_unique': note_tags_count + todo_tags_count,
                'top_tags': list(top_note_tags),
            },
            'recent_activity': {
                'notes': list(recent_notes),
                'todos': list(recent_todos),
            },
        })

    @action(detail=False, methods=['get'])
    def notes(self, request):
        """Get detailed notes statistics."""
        user = request.user

        # Basic counts
        total = Note.objects.filter(user=user).count()
        pinned = Note.objects.filter(user=user, is_pinned=True).count()
        archived = Note.objects.filter(user=user, is_archived=True).count()
        public = Note.objects.filter(user=user, is_public=True).count()

        # By notebook
        by_notebook = Notebook.objects.filter(user=user).annotate(
            note_count=Count('notes')
        ).values('name', 'note_count', 'color').order_by('-note_count')

        # Creation trend (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        created_last_30_days = Note.objects.filter(
            user=user,
            created__gte=thirty_days_ago
        ).count()

        # Top tags
        from taggit.models import Tag
        top_tags = Tag.objects.filter(
            taggit_taggeditem_items__content_type__model='note',
            taggit_taggeditem_items__object_id__in=Note.objects.filter(user=user).values_list('id', flat=True)
        ).annotate(
            usage_count=Count('taggit_taggeditem_items')
        ).order_by('-usage_count')[:10].values('name', 'usage_count')

        # With attachments
        with_attachments = Note.objects.filter(user=user).annotate(
            attachment_count=Count('attachments')
        ).filter(attachment_count__gt=0).count()

        # With todos
        with_todos = Note.objects.filter(user=user).annotate(
            todo_count=Count('todos')
        ).filter(todo_count__gt=0).count()

        return Response({
            'summary': {
                'total': total,
                'pinned': pinned,
                'archived': archived,
                'public': public,
                'with_attachments': with_attachments,
                'with_todos': with_todos,
                'created_last_30_days': created_last_30_days,
            },
            'by_notebook': list(by_notebook),
            'top_tags': list(top_tags),
        })

    @action(detail=False, methods=['get'])
    def todos(self, request):
        """Get detailed todos statistics."""
        user = request.user

        # Basic counts
        total = Todo.objects.filter(user=user).count()
        completed = Todo.objects.filter(user=user, is_completed=True).count()
        pending = Todo.objects.filter(user=user, is_completed=False).count()

        # By priority
        by_priority = {}
        for priority_key, priority_label in Todo.PRIORITY_CHOICES:
            by_priority[priority_key] = {
                'label': priority_label,
                'count': Todo.objects.filter(user=user, priority=priority_key).count(),
                'completed': Todo.objects.filter(
                    user=user, priority=priority_key, is_completed=True
                ).count(),
            }

        # By status
        by_status = {}
        for status_key, status_label in Todo.STATUS_CHOICES:
            by_status[status_key] = {
                'label': status_label,
                'count': Todo.objects.filter(user=user, status=status_key).count(),
            }

        # Overdue
        overdue = Todo.objects.filter(
            user=user,
            due_date__lt=timezone.now(),
            is_completed=False
        ).count()

        # Due soon (next 7 days)
        seven_days_later = timezone.now() + timedelta(days=7)
        due_soon = Todo.objects.filter(
            user=user,
            due_date__gte=timezone.now(),
            due_date__lte=seven_days_later,
            is_completed=False
        ).count()

        # Standalone vs note-based
        standalone = Todo.objects.filter(user=user, note__isnull=True).count()
        note_based = total - standalone

        # Top tags
        from taggit.models import Tag
        top_tags = Tag.objects.filter(
            taggit_taggeditem_items__content_type__model='todo',
            taggit_taggeditem_items__object_id__in=Todo.objects.filter(user=user).values_list('id', flat=True)
        ).annotate(
            usage_count=Count('taggit_taggeditem_items')
        ).order_by('-usage_count')[:10].values('name', 'usage_count')

        # Completion trend (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        completed_last_30_days = Todo.objects.filter(
            user=user,
            completed_at__gte=thirty_days_ago
        ).count()

        return Response({
            'summary': {
                'total': total,
                'completed': completed,
                'pending': pending,
                'overdue': overdue,
                'due_soon': due_soon,
                'standalone': standalone,
                'note_based': note_based,
                'completion_rate': (completed / total * 100) if total > 0 else 0,
                'completed_last_30_days': completed_last_30_days,
            },
            'by_priority': by_priority,
            'by_status': by_status,
            'top_tags': list(top_tags),
        })
