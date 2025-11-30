from django.contrib.auth.models import AbstractUser
from django.db import models
from core.models import TimeStampedModel


class User(AbstractUser, TimeStampedModel):
    """
    Custom user model extending Django's AbstractUser.
    Includes role-based authentication for API access control.
    """
    # User roles
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrator'
        PREMIUM = 'premium', 'Premium User'
        FREE = 'free', 'Free User'

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    # Role-based fields
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.FREE,
        help_text='User role for access control'
    )
    is_premium = models.BooleanField(
        default=False,
        help_text='Premium subscription status'
    )
    premium_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Premium subscription expiration date'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'auth_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def is_role_admin(self):
        """Check if user has admin role."""
        return self.role == self.Role.ADMIN or self.is_superuser

    def is_role_premium(self):
        """Check if user has premium role."""
        return self.role == self.Role.PREMIUM or self.is_premium

    def has_active_premium(self):
        """Check if user has active premium subscription."""
        if not self.is_premium:
            return False
        if self.premium_expires_at is None:
            return True
        from django.utils import timezone
        return self.premium_expires_at > timezone.now()
