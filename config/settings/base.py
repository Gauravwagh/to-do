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
    'admin_interface',
    'colorfield',
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

# Login URLs
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'notes:dashboard'
LOGOUT_REDIRECT_URL = 'accounts:login'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

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
        'OPTIONS': {
            'CLIENT_CLASS': 'django.core.cache.backends.redis.RedisClientFactory',
        },
        'KEY_PREFIX': 'evernote_clone',
        'TIMEOUT': 300,  # 5 minutes default
    }
}

# Logging
# Import comprehensive logging configuration
from .logging import get_logging_config

# Set up logging based on DEBUG mode
LOGGING = get_logging_config(debug=False)  # Will be overridden in local.py for dev

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


