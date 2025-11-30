"""
API v1 URL configuration.
"""
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

app_name = 'v1'

urlpatterns = [
    # Authentication endpoints
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # Feature endpoints will be added here
    # path('notes/', include('api.v1.views.notes')),
    # path('notebooks/', include('api.v1.views.notebooks')),
    # path('todos/', include('api.v1.views.todos')),
    # path('vault/', include('api.v1.views.vault')),
]
