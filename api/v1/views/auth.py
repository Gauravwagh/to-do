"""
ViewSets for Authentication API endpoints.
"""
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings

from api.v1.serializers.auth import (
    UserSerializer,
    UserProfileUpdateSerializer,
    UserRegistrationSerializer,
    PasswordChangeSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    CustomTokenObtainPairSerializer,
)

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom JWT token view with user data."""
    serializer_class = CustomTokenObtainPairSerializer


class AuthViewSet(viewsets.GenericViewSet):
    """
    ViewSet for authentication operations.

    Provides registration, login, logout, password reset, etc.
    """
    serializer_class = UserSerializer

    def get_permissions(self):
        """Set permissions based on action."""
        if self.action in ['register', 'password_reset_request', 'password_reset_confirm']:
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        """Register a new user."""
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': 'Registration successful. Welcome!'
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def logout(self, request):
        """Logout user by blacklisting refresh token."""
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
                return Response({
                    'success': True,
                    'message': 'Logout successful.'
                })
            return Response({
                'error': 'Refresh token is required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'Invalid token or token already blacklisted.'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user profile."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        """Update current user profile."""
        serializer = UserProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=request.method == 'PATCH'
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            'user': UserSerializer(request.user).data,
            'message': 'Profile updated successfully.'
        })

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change user password."""
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            'success': True,
            'message': 'Password changed successfully.'
        })

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def password_reset_request(self, request):
        """Request password reset email."""
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        user = User.objects.get(email=email)

        # Generate password reset token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        # In production, send email with reset link
        reset_link = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"

        # For now, just return the link in response (in production, send via email)
        # TODO: Send email in production
        send_password_reset_email(user, reset_link)

        return Response({
            'success': True,
            'message': 'Password reset email sent. Please check your inbox.',
            # Remove this in production:
            'reset_link': reset_link if settings.DEBUG else None
        })

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def password_reset_confirm(self, request):
        """Confirm password reset with token."""
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            uid = force_str(urlsafe_base64_decode(serializer.validated_data['uid']))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({
                'error': 'Invalid reset link.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Verify token
        if not default_token_generator.check_token(user, serializer.validated_data['token']):
            return Response({
                'error': 'Invalid or expired reset link.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Set new password
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        return Response({
            'success': True,
            'message': 'Password reset successful. You can now login with your new password.'
        })

    @action(detail=False, methods=['delete'])
    def delete_account(self, request):
        """Delete user account (soft delete)."""
        # Require password confirmation
        password = request.data.get('password')
        if not password:
            return Response({
                'error': 'Password confirmation is required.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not request.user.check_password(password):
            return Response({
                'error': 'Incorrect password.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Deactivate account instead of deleting
        request.user.is_active = False
        request.user.save()

        return Response({
            'success': True,
            'message': 'Account deactivated successfully.'
        })


def send_password_reset_email(user, reset_link):
    """Send password reset email to user."""
    subject = 'Password Reset Request - Notes & Todos'
    message = f"""
    Hi {user.username},

    You requested to reset your password. Click the link below to reset it:

    {reset_link}

    If you didn't request this, please ignore this email.

    This link will expire in 24 hours.

    Best regards,
    Notes & Todos Team
    """

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
    except Exception as e:
        # Log error in production
        print(f"Failed to send password reset email: {e}")
