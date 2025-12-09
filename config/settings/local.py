"""
Local development settings for Evernote Clone project.
"""
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']

# Override logging for local development to show full tracebacks
from .logging import get_logging_config
LOGGING = get_logging_config(debug=True)

# Database for local development (SQLite for simplicity)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Use local memory cache for development (simpler, no external dependencies)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Silence django_ratelimit checks in development (not critical for local dev)
# Rate limiting requires Redis/Memcached which may not be available locally
SILENCED_SYSTEM_CHECKS = ['django_ratelimit.W001', 'django_ratelimit.E003']

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# REST Framework debug settings - show full error details
REST_FRAMEWORK = {
    **globals().get('REST_FRAMEWORK', {}),
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
}

# Django Debug Toolbar
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    
    INTERNAL_IPS = [
        '127.0.0.1',
    ]
    

# Static files for development
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Media files for development
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Debug toolbar configuration to avoid profiling conflicts
DEBUG_TOOLBAR_CONFIG = {
    'DISABLE_PANELS': [
        'debug_toolbar.panels.redirects.RedirectsPanel',
        'debug_toolbar.panels.profiling.ProfilingPanel',  # Disable profiling to avoid conflicts
    ],
    'SHOW_TEMPLATE_CONTEXT': True,
    'SHOW_COLLAPSED': True,
    'INSERT_BEFORE': '</body>',  # Ensure it doesn't overlap content
}

# Add margin to prevent debug toolbar overlap
DEBUG_TOOLBAR_PANELS = [
    'debug_toolbar.panels.history.HistoryPanel',
    'debug_toolbar.panels.versions.VersionsPanel',
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.cache.CachePanel',
    'debug_toolbar.panels.signals.SignalsPanel',
    'debug_toolbar.panels.logging.LoggingPanel',
]


