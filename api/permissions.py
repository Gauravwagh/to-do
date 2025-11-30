"""
Custom permissions for API access control.
"""
from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """
    Permission to only allow owners of an object to access it.
    """
    def has_object_permission(self, request, view, obj):
        # Check if object has a user/owner attribute
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'owner'):
            return obj.owner == request.user
        return False


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission to allow read-only access to everyone,
    but write access only to the owner.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions for safe methods
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for owner
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'owner'):
            return obj.owner == request.user
        return False


class IsPremiumUser(permissions.BasePermission):
    """
    Permission to check if user has premium access.
    """
    message = 'Premium subscription required for this feature.'

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and \
               hasattr(request.user, 'is_premium') and request.user.is_premium


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission to allow read access to authenticated users,
    but write access only to admin users.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_staff


class CanManageVault(permissions.BasePermission):
    """
    Permission to check if user can manage vault items.
    """
    message = 'You do not have permission to manage vault items.'

    def has_permission(self, request, view):
        # User must be authenticated and have vault unlocked
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # User must own the vault item
        return obj.user == request.user
