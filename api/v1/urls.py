"""
API v1 URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
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
)

app_name = 'v1'

# Main router
router = DefaultRouter()

# Register viewsets
router.register(r'notes', NoteViewSet, basename='note')
router.register(r'notebooks', NotebookViewSet, basename='notebook')
router.register(r'todos', TodoViewSet, basename='todo')
router.register(r'tags', TagViewSet, basename='tag')

# Nested router for note attachments
notes_router = routers.NestedDefaultRouter(router, r'notes', lookup='note')
notes_router.register(r'attachments', NoteAttachmentViewSet, basename='note-attachments')

urlpatterns = [
    # Authentication endpoints (JWT)
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

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
