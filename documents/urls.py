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

    # Document CRUD
    path('upload/', views.document_upload, name='document_upload'),
    path('<uuid:pk>/', views.document_detail, name='document_detail'),
    path('<uuid:pk>/edit/', views.document_edit, name='document_edit'),
    path('<uuid:pk>/delete/', views.document_delete, name='document_delete'),

    # Document actions
    path('<uuid:pk>/download/', views.document_download, name='document_download'),
    path('<uuid:pk>/preview/', views.document_preview, name='document_preview'),
    path('<uuid:pk>/toggle-favorite/', views.toggle_favorite, name='toggle_favorite'),

    # Categories
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
