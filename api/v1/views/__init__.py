"""
API v1 Views.
"""
from .notes import NoteViewSet, NotebookViewSet, NoteAttachmentViewSet
from .todos import TodoViewSet
from .tags import TagViewSet
from .search import SearchViewSet
from .statistics import StatisticsViewSet
from .auth import AuthViewSet, CustomTokenObtainPairView
from .vault import (
    VaultConfigViewSet,
    VaultCredentialViewSet,
    VaultSecureNoteViewSet,
    VaultFileViewSet,
    VaultAPIKeyViewSet,
    VaultUtilityViewSet,
)
from .sync import SyncViewSet
from .notifications import NotificationViewSet

__all__ = [
    'NoteViewSet',
    'NotebookViewSet',
    'NoteAttachmentViewSet',
    'TodoViewSet',
    'TagViewSet',
    'SearchViewSet',
    'StatisticsViewSet',
    'AuthViewSet',
    'CustomTokenObtainPairView',
    'VaultConfigViewSet',
    'VaultCredentialViewSet',
    'VaultSecureNoteViewSet',
    'VaultFileViewSet',
    'VaultAPIKeyViewSet',
    'VaultUtilityViewSet',
    'SyncViewSet',
    'NotificationViewSet',
]
