"""
Web URL configuration for documents app.
"""
from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    # Dashboard and list views
    path('', views.dashboard, name='dashboard'),
    path('list/', views.document_list, name='document_list'),
    
    # Drive/Folder browsing (Google Drive-like)
    path('drive/', views.drive, name='drive'),
    path('drive/folder/<uuid:folder_id>/', views.drive, name='drive_folder'),
    
    # Folder CRUD
    path('folder/create/', views.folder_create, name='folder_create'),
    path('folder/create/<uuid:parent_id>/', views.folder_create, name='folder_create_in'),
    path('folder/<uuid:folder_id>/edit/', views.folder_edit, name='folder_edit'),
    path('folder/<uuid:folder_id>/delete/', views.folder_delete, name='folder_delete'),
    
    # Move items
    path('move/', views.move_item, name='move_item'),
    
    # Upload to folder
    path('upload-to-folder/', views.upload_to_folder, name='upload_to_folder'),
    path('upload-to-folder/<uuid:folder_id>/', views.upload_to_folder, name='upload_to_folder_in'),

    # Document CRUD
    path('upload/', views.document_upload, name='document_upload'),
    path('doc/<uuid:pk>/', views.document_detail, name='document_detail'),
    path('doc/<uuid:pk>/edit/', views.document_edit, name='document_edit'),
    path('doc/<uuid:pk>/delete/', views.document_delete, name='document_delete'),

    # Document actions
    path('doc/<uuid:pk>/download/', views.document_download, name='document_download'),
    path('doc/<uuid:pk>/preview/', views.document_preview, name='document_preview'),
    path('doc/<uuid:pk>/toggle-favorite/', views.toggle_favorite, name='toggle_favorite'),

    # Categories (legacy - redirect to folders)
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<uuid:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<uuid:pk>/delete/', views.category_delete, name='category_delete'),

    # Storage and stats
    path('storage/', views.storage_stats, name='storage_stats'),
    path('stats/', views.compression_stats, name='compression_stats'),

    # Sharing
    path('share/<str:token>/', views.public_share, name='public_share'),
]
