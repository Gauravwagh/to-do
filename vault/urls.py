"""
URL configuration for vault app.
"""
from django.urls import path
from . import views

app_name = 'vault'

urlpatterns = [
    # Vault setup and authentication
    path('', views.VaultDashboardView.as_view(), name='dashboard'),
    path('setup/', views.VaultSetupView.as_view(), name='setup'),
    path('unlock/', views.VaultUnlockView.as_view(), name='unlock'),
    path('lock/', views.vault_lock, name='lock'),

    # Vault configuration
    path('settings/', views.VaultSettingsView.as_view(), name='settings'),
    path('audit-log/', views.VaultAuditLogView.as_view(), name='audit_log'),

    # Credentials
    path('credentials/', views.CredentialListView.as_view(), name='credential_list'),
    path('credentials/create/', views.CredentialCreateView.as_view(), name='credential_create'),
    path('credentials/<int:pk>/', views.CredentialDetailView.as_view(), name='credential_detail'),
    path('credentials/<int:pk>/edit/', views.CredentialUpdateView.as_view(), name='credential_update'),
    path('credentials/<int:pk>/delete/', views.CredentialDeleteView.as_view(), name='credential_delete'),

    # Secure Notes
    path('notes/', views.SecureNoteListView.as_view(), name='note_list'),
    path('notes/create/', views.SecureNoteCreateView.as_view(), name='note_create'),
    path('notes/<int:pk>/', views.SecureNoteDetailView.as_view(), name='note_detail'),
    path('notes/<int:pk>/edit/', views.SecureNoteUpdateView.as_view(), name='note_update'),
    path('notes/<int:pk>/delete/', views.SecureNoteDeleteView.as_view(), name='note_delete'),

    # Files
    path('files/', views.FileListView.as_view(), name='file_list'),
    path('files/create/', views.FileCreateView.as_view(), name='file_create'),
    path('files/<int:pk>/', views.FileDetailView.as_view(), name='file_detail'),
    path('files/<int:pk>/download/', views.file_download, name='file_download'),
    path('files/<int:pk>/delete/', views.FileDeleteView.as_view(), name='file_delete'),

    # API Keys
    path('apikeys/', views.APIKeyListView.as_view(), name='apikey_list'),
    path('apikeys/create/', views.APIKeyCreateView.as_view(), name='apikey_create'),
    path('apikeys/<int:pk>/', views.APIKeyDetailView.as_view(), name='apikey_detail'),
    path('apikeys/<int:pk>/edit/', views.APIKeyUpdateView.as_view(), name='apikey_update'),
    path('apikeys/<int:pk>/delete/', views.APIKeyDeleteView.as_view(), name='apikey_delete'),

    # Search
    path('search/', views.VaultSearchView.as_view(), name='search'),

    # Re-authentication
    path('reauth/<int:pk>/', views.VaultReAuthView.as_view(), name='reauth'),
]
