"""
Management command to create a superuser from environment variables.
This command is idempotent and safe to run multiple times.
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates a superuser from environment variables if it does not exist'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Superuser email address',
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Superuser username',
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Superuser password',
        )

    def handle(self, *args, **options):
        # Get credentials from arguments or environment variables
        email = options.get('email') or os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
        username = options.get('username') or os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
        password = options.get('password') or os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')

        # Check if superuser already exists (by email OR username)
        user = None
        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)
        elif User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)

        if user:
            self.stdout.write(
                self.style.WARNING(f'Superuser already exists: {user.email}')
            )

            # Update password and ensure superuser status (don't change username/email to avoid conflicts)
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.save(update_fields=['password', 'is_staff', 'is_superuser', 'is_active'])

            self.stdout.write(
                self.style.SUCCESS(f'Updated superuser: {user.email} (username: {user.username})')
            )
        else:
            # Create new superuser
            try:
                user = User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password
                )
                user.is_staff = True
                user.is_active = True
                user.save()
                
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created superuser: {email}')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating superuser: {str(e)}')
                )
                raise

        # Display credentials (be careful with this in production)
        self.stdout.write(
            self.style.SUCCESS('\n=== Superuser Credentials ===')
        )
        self.stdout.write(f'Email: {email}')
        self.stdout.write(f'Username: {username}')
        self.stdout.write(f'Password: {password}')
        self.stdout.write(
            self.style.SUCCESS('=============================\n')
        )
