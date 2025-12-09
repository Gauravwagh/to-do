"""
Comprehensive logging configuration for Django application.
Integrates with Sentry for automatic error tracking.
"""
import os
from pathlib import Path

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = BASE_DIR / 'logs'

# Ensure logs directory exists
LOGS_DIR.mkdir(exist_ok=True)

# Get log level from environment
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
DJANGO_LOG_LEVEL = os.environ.get('DJANGO_LOG_LEVEL', 'INFO')


def get_logging_config(debug=False):
    """
    Get logging configuration based on environment.

    Args:
        debug: Whether running in debug mode

    Returns:
        Dict with logging configuration
    """
    # Common formatters
    formatters = {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {module}.{funcName}:{lineno} - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '[{levelname}] {name} - {message}',
            'style': '{',
        },
        'json': {
            'format': '[{levelname}] {asctime} {name} - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    }

    # Common handlers
    handlers = {
        'console': {
            'level': 'DEBUG' if debug else LOG_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'verbose' if debug else 'simple',
        },
        'file': {
            'level': LOG_LEVEL,
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'error.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'security.log',
            'maxBytes': 1024 * 1024 * 5,  # 5MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'null': {
            'class': 'logging.NullHandler',
        },
    }

    # Loggers configuration
    loggers = {
        # Root logger
        '': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'DEBUG' if debug else LOG_LEVEL,
        },
        # Django core
        'django': {
            'handlers': ['console', 'file'],
            'level': DJANGO_LOG_LEVEL,
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.template': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'] if debug else ['null'],
            'level': 'DEBUG' if debug else 'INFO',
            'propagate': False,
        },
        # Security
        'django.security': {
            'handlers': ['console', 'security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.security.csrf': {
            'handlers': ['console', 'security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        # Application loggers
        'notes': {
            'handlers': ['console', 'file', 'error_file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'accounts': {
            'handlers': ['console', 'file', 'error_file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'vault': {
            'handlers': ['console', 'file', 'error_file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'api': {
            'handlers': ['console', 'file', 'error_file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'documents': {
            'handlers': ['console', 'file', 'error_file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        # Middleware
        'config.middleware': {
            'handlers': ['console', 'file', 'error_file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
    }

    return {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': formatters,
        'handlers': handlers,
        'loggers': loggers,
    }


# Export the configuration
LOGGING = get_logging_config()
