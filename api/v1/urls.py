"""
API v1 URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)
from rest_framework_nested import routers

from .views import (
    NoteViewSet,
    NotebookViewSet,
    NoteAttachmentViewSet,
    TodoViewSet,
    TagViewSet,
    SearchViewSet,
    StatisticsViewSet,
    AuthViewSet,
    CustomTokenObtainPairView,
    VaultConfigViewSet,
    VaultCredentialViewSet,
    VaultSecureNoteViewSet,
    VaultFileViewSet,
    VaultAPIKeyViewSet,
    VaultUtilityViewSet,
    SyncViewSet,
    NotificationViewSet,
)

app_name = 'v1'

# Main router
router = DefaultRouter()

# Register viewsets
router.register(r'notes', NoteViewSet, basename='note')
router.register(r'notebooks', NotebookViewSet, basename='notebook')
router.register(r'todos', TodoViewSet, basename='todo')
router.register(r'tags', TagViewSet, basename='tag')

# Vault viewsets
router.register(r'vault/credentials', VaultCredentialViewSet, basename='vault-credential')
router.register(r'vault/secure-notes', VaultSecureNoteViewSet, basename='vault-secure-note')
router.register(r'vault/files', VaultFileViewSet, basename='vault-file')
router.register(r'vault/api-keys', VaultAPIKeyViewSet, basename='vault-api-key')

# Nested router for note attachments
notes_router = routers.NestedDefaultRouter(router, r'notes', lookup='note')
notes_router.register(r'attachments', NoteAttachmentViewSet, basename='note-attachments')

urlpatterns = [
    # Authentication endpoints
    path('auth/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    # path('auth/register/', AuthViewSet.as_view({'post': 'register'}), name='auth-register'),  # Disabled
    path('auth/logout/', AuthViewSet.as_view({'post': 'logout'}), name='auth-logout'),
    path('auth/me/', AuthViewSet.as_view({'get': 'me'}), name='auth-me'),
    path('auth/me/update/', AuthViewSet.as_view({'put': 'update_profile', 'patch': 'update_profile'}), name='auth-update-profile'),
    path('auth/password/change/', AuthViewSet.as_view({'post': 'change_password'}), name='auth-change-password'),
    path('auth/password/reset/', AuthViewSet.as_view({'post': 'password_reset_request'}), name='auth-password-reset'),
    path('auth/password/reset/confirm/', AuthViewSet.as_view({'post': 'password_reset_confirm'}), name='auth-password-reset-confirm'),
    path('auth/account/delete/', AuthViewSet.as_view({'delete': 'delete_account'}), name='auth-delete-account'),

    # Vault configuration endpoints
    path('vault/config/', VaultConfigViewSet.as_view({'get': 'config'}), name='vault-config'),
    path('vault/initialize/', VaultConfigViewSet.as_view({'post': 'initialize'}), name='vault-initialize'),
    path('vault/unlock/', VaultConfigViewSet.as_view({'post': 'unlock'}), name='vault-unlock'),
    path('vault/lock/', VaultConfigViewSet.as_view({'post': 'lock'}), name='vault-lock'),
    path('vault/password/change/', VaultConfigViewSet.as_view({'post': 'change_password'}), name='vault-change-password'),

    # Vault utility endpoints
    path('vault/search/', VaultUtilityViewSet.as_view({'get': 'search'}), name='vault-search'),
    path('vault/stats/', VaultUtilityViewSet.as_view({'get': 'stats'}), name='vault-stats'),
    path('vault/audit-logs/', VaultUtilityViewSet.as_view({'get': 'audit_logs'}), name='vault-audit-logs'),

    # Sync endpoints
    path('sync/status/', SyncViewSet.as_view({'get': 'status'}), name='sync-status'),
    path('sync/pull/', SyncViewSet.as_view({'post': 'pull'}), name='sync-pull'),
    path('sync/push/', SyncViewSet.as_view({'post': 'push'}), name='sync-push'),
    path('sync/resolve-conflicts/', SyncViewSet.as_view({'post': 'resolve_conflicts'}), name='sync-resolve-conflicts'),

    # Notification endpoints
    path('notifications/register/', NotificationViewSet.as_view({'post': 'register_device'}), name='notifications-register'),
    path('notifications/unregister/', NotificationViewSet.as_view({'post': 'unregister_device'}), name='notifications-unregister'),
    path('notifications/devices/', NotificationViewSet.as_view({'get': 'list_devices'}), name='notifications-devices'),
    path('notifications/', NotificationViewSet.as_view({'get': 'get_notifications'}), name='notifications-list'),
    path('notifications/read/', NotificationViewSet.as_view({'post': 'mark_read'}), name='notifications-mark-read'),
    path('notifications/read/all/', NotificationViewSet.as_view({'post': 'mark_all_read'}), name='notifications-mark-all-read'),
    path('notifications/preferences/', NotificationViewSet.as_view({'get': 'preferences', 'put': 'preferences'}), name='notifications-preferences'),
    path('notifications/test/', NotificationViewSet.as_view({'post': 'send_test'}), name='notifications-test'),

    # Search endpoints
    path('search/', SearchViewSet.as_view({'get': 'global_search'}), name='search-global'),
    path('search/notes/', SearchViewSet.as_view({'get': 'notes'}), name='search-notes'),
    path('search/todos/', SearchViewSet.as_view({'get': 'todos'}), name='search-todos'),

    # Statistics endpoints
    path('dashboard/', StatisticsViewSet.as_view({'get': 'dashboard'}), name='dashboard'),
    path('stats/notes/', StatisticsViewSet.as_view({'get': 'notes'}), name='stats-notes'),
    path('stats/todos/', StatisticsViewSet.as_view({'get': 'todos'}), name='stats-todos'),

    # Include router URLs
    path('', include(router.urls)),
    path('', include(notes_router.urls)),
]
