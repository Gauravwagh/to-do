from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Test Sentry error tracking'

    def handle(self, *args, **options):
        self.stdout.write('Testing Sentry integration...')
        
        # Trigger a test error
        try:
            1 / 0
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Test error triggered: {e}'))
            # Re-raise to send to Sentry
            raise
        
        self.stdout.write(self.style.SUCCESS('If you see this, the error was caught locally'))
