"""
API URL configuration for documents app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .api_views import (
    DocumentCategoryViewSet,
    DocumentTagViewSet,
    DocumentViewSet,
    StorageQuotaViewSet,
    CompressionStatsViewSet,
)

app_name = 'documents_api'

# Create router
router = DefaultRouter()
router.register(r'categories', DocumentCategoryViewSet, basename='category')
router.register(r'tags', DocumentTagViewSet, basename='tag')
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'storage', StorageQuotaViewSet, basename='storage')
router.register(r'stats', CompressionStatsViewSet, basename='stats')

urlpatterns = [
    path('', include(router.urls)),
]
