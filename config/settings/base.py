"""
Base settings for Evernote Clone project.
"""
import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-change-me-in-production')

# Application definition
# Admin theme apps (must be before django.contrib.admin)
ADMIN_THEME_APPS = [
    'jazzmin',
]

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
]

THIRD_PARTY_APPS = [
    # Forms and tags
    'crispy_forms',
    'crispy_bootstrap5',
    'taggit',
    # REST Framework
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'drf_spectacular',
    'django_ratelimit',
]

LOCAL_APPS = [
    'accounts.apps.AccountsConfig',
    'notes.apps.NotesConfig',
    'core.apps.CoreConfig',
    'vault.apps.VaultConfig',
    'api.apps.ApiConfig',
    'documents.apps.DocumentsConfig',
]

INSTALLED_APPS = ADMIN_THEME_APPS + DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS handling
    'config.middleware.error_handler.RequestIDMiddleware',  # Add request ID tracking
    'config.middleware.error_handler.SentryContextMiddleware',  # Add Sentry context
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'config.middleware.error_handler.ErrorHandlingMiddleware',  # Handle all exceptions
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'vault.context_processors.vault_stats',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DATABASE_NAME', 'evernote_clone'),
        'USER': os.environ.get('DATABASE_USER', 'postgres'),
        'PASSWORD': os.environ.get('DATABASE_PASSWORD', ''),
        'HOST': os.environ.get('DATABASE_HOST', 'localhost'),
        'PORT': os.environ.get('DATABASE_PORT', '5432'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'accounts.User'

# Authentication backends
AUTHENTICATION_BACKENDS = [
    'accounts.backends.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Login URLs
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'notes:dashboard'
LOGOUT_REDIRECT_URL = 'accounts:login'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@evernote-clone.com')
SITE_URL = os.environ.get('SITE_URL', 'http://localhost:8000')

# TinyMCE settings
TINYMCE_API_KEY = '70r2h4ki9m7s4vx8qw2lv8w1cz4izt726m4trl79l5i6bbks'

TINYMCE_DEFAULT_CONFIG = {
    'height': 400,
    'width': '100%',
    'cleanup_on_startup': True,
    'custom_undo_redo_levels': 20,
    'selector': 'textarea',
    'theme': 'silver',
    'plugins': [
        'advlist autolink lists link image charmap print preview anchor',
        'searchreplace visualblocks code fullscreen',
        'insertdatetime media table contextmenu paste code'
    ],
    'toolbar': 'undo redo | formatselect | bold italic backcolor | \
        alignleft aligncenter alignright alignjustify | \
        bullist numlist outdent indent | removeformat | help',
    'menubar': False,
    'statusbar': True,
    'resize': True,
    'branding': False,
    'content_css': '/static/css/style.css',
    'api_key': TINYMCE_API_KEY,
}

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'SAMEORIGIN'  # Allow iframe embedding for file previews

# Vault settings
VAULT_SETTINGS = {
    'DEFAULT_TIMEOUT_MINUTES': 15,
    'MAX_FAILED_ATTEMPTS': 5,
    'LOCKOUT_DURATION_MINUTES': 30,
    'KDF_ITERATIONS': 600000,
    'MAX_FILE_SIZE_MB': 25,
}

# Session security
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'

# Cache configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'KEY_PREFIX': 'evernote_clone',
        'TIMEOUT': 300,  # 5 minutes default
    }
}

# Logging
# Import comprehensive logging configuration
from .logging import get_logging_config

# Set up logging based on DEBUG mode
LOGGING = get_logging_config(debug=True)  # Will be overridden in local.py for dev

# ==============================================================================
# REST FRAMEWORK SETTINGS
# ==============================================================================

REST_FRAMEWORK = {
    # Authentication
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    # Permissions
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    # Pagination
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    # Filtering
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    # Rendering
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    # Schema
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    # Throttling
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    },
    # Exception handling
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
}

# ==============================================================================
# JWT AUTHENTICATION SETTINGS
# ==============================================================================

from datetime import timedelta

SIMPLE_JWT = {
    # Token lifetimes
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,

    # Algorithm
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,

    # Token headers
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',

    # Token claims
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',

    # Token verification
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',

    # Update last login
    'UPDATE_LAST_LOGIN': True,
}

# ==============================================================================
# CORS SETTINGS
# ==============================================================================

# CORS configuration for mobile and web clients
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',  # React Native web development
    'http://localhost:19000',  # Expo web
    'http://localhost:19006',  # Expo web alternative
    'http://127.0.0.1:3000',
    'http://127.0.0.1:19000',
    'http://127.0.0.1:19006',
]

# Allow credentials (cookies, authorization headers)
CORS_ALLOW_CREDENTIALS = True

# Allow all headers for development
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Allow common HTTP methods
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# ==============================================================================
# API DOCUMENTATION SETTINGS (drf-spectacular)
# ==============================================================================

SPECTACULAR_SETTINGS = {
    'TITLE': 'Evernote Clone API',
    'DESCRIPTION': 'Comprehensive API for note-taking application with vault, notebooks, todos, and more',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,

    # Schema generation
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/v1/',

    # API UI
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'REDOC_DIST': 'SIDECAR',

    # Authentication
    'SECURITY': [
        {
            'Bearer': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            }
        }
    ],

    # Contact info
    'CONTACT': {
        'name': 'API Support',
        'email': 'support@evernote-clone.com',
    },

    # License info
    'LICENSE': {
        'name': 'MIT License',
    },
}

# ==============================================================================
# CELERY SETTINGS
# ==============================================================================

# Celery broker and result backend
CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')

# Celery configuration
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# Task settings
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes

# Result backend settings
CELERY_RESULT_EXPIRES = 3600  # 1 hour

# ==============================================================================
# DOCUMENT LIBRARY COMPRESSION SETTINGS
# ==============================================================================

# Compression settings
COMPRESSION_ENABLED = True
COMPRESSION_ALGORITHM = 'zstd'  # zstd, deflate, brotli
COMPRESSION_LEVEL = 6  # 1-9
COMPRESSION_MIN_SIZE = 102400  # 100KB
COMPRESSION_MAX_SIZE = 5368709120  # 5GB
COMPRESSION_TIMEOUT = 300  # seconds
COMPRESSION_THREADS = 4  # CPU threads for compression

# Decompression settings
DECOMPRESSION_TIMEOUT = 30  # seconds
DECOMPRESSION_TEMP_TTL = 3600  # 1 hour
DECOMPRESSION_TEMP_DIR = BASE_DIR / 'media' / 'temp' / 'decompress'

# Backup settings
BACKUP_ENABLED = True
BACKUP_KEEP_DAYS = 2  # Keep original for 2 days

# ==============================================================================
# JAZZMIN ADMIN THEME SETTINGS
# ==============================================================================

JAZZMIN_SETTINGS = {
    # Site branding
    'site_title': 'Evernote Clone Admin',
    'site_header': 'Evernote Clone',
    'site_brand': 'Evernote Clone',
    'site_logo': None,
    'login_logo': None,
    'login_logo_dark': None,
    'site_logo_classes': 'img-circle',
    'site_icon': None,

    # Welcome message
    'welcome_sign': 'Welcome to Evernote Clone Admin',
    'copyright': 'Evernote Clone',

    # Search model
    'search_model': ['auth.User', 'notes.Note', 'documents.Document'],

    # User menu
    'user_avatar': None,

    # Top menu
    'topmenu_links': [
        {'name': 'Home', 'url': 'admin:index', 'permissions': ['auth.view_user']},
        {'name': 'Dashboard', 'url': 'notes:dashboard', 'permissions': ['auth.view_user']},
        {'name': 'Document Library', 'url': 'documents:document_list', 'permissions': ['auth.view_user'], 'icon': 'fas fa-folder-open'},
        {'model': 'auth.User'},
    ],

    # User menu items (dropdown)
    'usermenu_links': [
        {'name': 'Dashboard', 'url': 'notes:dashboard', 'icon': 'fas fa-home'},
        {'name': 'Document Library', 'url': 'documents:document_list', 'icon': 'fas fa-folder-open'},
        {'model': 'auth.user'},
    ],

    # Side menu ordering
    'show_sidebar': True,
    'navigation_expanded': True,
    'hide_apps': [],
    'hide_models': [],

    # Custom links in sidebar
    'custom_links': {
        'documents': [{
            'name': 'Document Library Dashboard',
            'url': 'documents:document_list',
            'icon': 'fas fa-home',
            'permissions': ['documents.view_document']
        }, {
            'name': 'Upload Document',
            'url': 'documents:document_upload',
            'icon': 'fas fa-upload',
            'permissions': ['documents.add_document']
        }, {
            'name': 'Categories',
            'url': 'documents:category_list',
            'icon': 'fas fa-folder-tree',
            'permissions': ['documents.view_category']
        }, {
            'name': 'Statistics',
            'url': 'documents:stats_dashboard',
            'icon': 'fas fa-chart-line',
            'permissions': ['documents.view_compressionstats']
        }]
    },

    # Custom ordering for apps and models
    'order_with_respect_to': [
        'accounts',
        'notes',
        'documents',
        'vault',
        'auth',
        'api',
    ],

    # Icons for apps and models
    'icons': {
        'auth': 'fas fa-users-cog',
        'auth.user': 'fas fa-user',
        'auth.Group': 'fas fa-users',

        'accounts': 'fas fa-user-circle',
        'accounts.User': 'fas fa-user-circle',

        'notes': 'fas fa-sticky-note',
        'notes.Note': 'fas fa-sticky-note',
        'notes.Notebook': 'fas fa-book',
        'notes.Tag': 'fas fa-tag',
        'notes.Todo': 'fas fa-check-square',

        'documents': 'fas fa-folder-open',
        'documents.Document': 'fas fa-file-alt',
        'documents.Category': 'fas fa-folder',
        'documents.Tag': 'fas fa-tags',
        'documents.ShareLink': 'fas fa-share-alt',
        'documents.ShareLog': 'fas fa-history',
        'documents.DocumentQuota': 'fas fa-chart-pie',
        'documents.DocumentBackup': 'fas fa-archive',
        'documents.CompressionStats': 'fas fa-chart-bar',

        'vault': 'fas fa-vault',
        'vault.VaultConfig': 'fas fa-lock',
        'vault.VaultItem': 'fas fa-key',
        'vault.VaultFile': 'fas fa-file-shield',
    },

    # Theme customization
    'default_icon_parents': 'fas fa-chevron-circle-right',
    'default_icon_children': 'fas fa-circle',

    # UI Tweaks
    'related_modal_active': False,
    'custom_css': None,
    'custom_js': None,
    'use_google_fonts_cdn': True,
    'show_ui_builder': False,

    # Change view
    'changeform_format': 'horizontal_tabs',
    'changeform_format_overrides': {
        'auth.user': 'collapsible',
        'auth.group': 'vertical_tabs',
    },

    # Language chooser
    'language_chooser': False,
}

JAZZMIN_UI_TWEAKS = {
    'navbar_small_text': False,
    'footer_small_text': False,
    'body_small_text': False,
    'brand_small_text': False,
    'brand_colour': False,
    'accent': 'accent-primary',
    'navbar': 'navbar-white navbar-light',
    'no_navbar_border': False,
    'navbar_fixed': False,
    'layout_boxed': False,
    'footer_fixed': False,
    'sidebar_fixed': False,
    'sidebar': 'sidebar-dark-primary',
    'sidebar_nav_small_text': False,
    'sidebar_disable_expand': False,
    'sidebar_nav_child_indent': False,
    'sidebar_nav_compact_style': False,
    'sidebar_nav_legacy_style': False,
    'sidebar_nav_flat_style': False,
    'theme': 'default',
    'dark_mode_theme': None,
    'button_classes': {
        'primary': 'btn-primary',
        'secondary': 'btn-secondary',
        'info': 'btn-info',
        'warning': 'btn-warning',
        'danger': 'btn-danger',
        'success': 'btn-success',
    },
}


