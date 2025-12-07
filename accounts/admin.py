from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom User admin with password change functionality.
    """
    list_display = ('email', 'username', 'first_name', 'last_name', 'role', 'is_premium', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'role', 'is_premium')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('-date_joined',)

    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'bio', 'avatar')}),
        (_('Role & Subscription'), {'fields': ('role', 'is_premium', 'premium_expires_at')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Role & Subscription'), {'fields': ('role', 'is_premium')}),
        (_('Permissions'), {'fields': ('is_staff', 'is_active')}),
    )

    readonly_fields = ('date_joined', 'last_login')
    filter_horizontal = ('groups', 'user_permissions')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('groups', 'user_permissions')