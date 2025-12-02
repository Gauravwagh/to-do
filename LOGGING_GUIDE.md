# Logging and Error Handling Guide

This guide explains how to use the logging and error handling system integrated with Sentry.

## Overview

The application has a comprehensive logging system that automatically captures:
- All unhandled exceptions
- Request/response context
- User information
- Performance metrics
- Custom log messages

All errors are automatically sent to Sentry with full context.

## Quick Start

### 1. Basic Logging in Views

```python
from config.logging_utils import get_logger, log_with_context

logger = get_logger(__name__)

def my_view(request):
    # Log with automatic request context
    log_with_context(
        logger,
        'info',
        'User accessed the dashboard',
        request=request
    )

    try:
        # Your code here
        pass
    except Exception as e:
        # Exception is automatically logged and sent to Sentry
        logger.error(f"Error in view: {str(e)}", exc_info=True)
        raise
```

### 2. Using Custom Exceptions

```python
from config.exceptions import ValidationError, ResourceNotFoundError

def process_data(data):
    if not data.get('required_field'):
        # This will be logged and sent to Sentry automatically
        raise ValidationError(
            "Required field missing",
            field="required_field",
            provided_data=data
        )
```

### 3. Using the Log Decorator

```python
from config.logging_utils import log_decorator

@log_decorator(log_args=True, log_result=True)
def complex_calculation(x, y):
    # Function calls and exceptions are automatically logged
    return x * y
```

### 4. Logging with Context

```python
from config.logging_utils import get_context_logger

# Create logger with permanent context
logger = get_context_logger(
    __name__,
    service='payment',
    operation='process_payment'
)

# All logs from this logger will include the context
logger.info("Processing payment")  # Includes service and operation tags
```

### 5. Manual Exception Logging

```python
from config.logging_utils import get_logger, log_exception

logger = get_logger(__name__)

try:
    # Risky operation
    process_payment()
except Exception as e:
    # Log with full context and send to Sentry
    log_exception(
        logger,
        e,
        request=request,
        extra={'payment_id': payment_id}
    )
    # Handle the error appropriately
```

## Custom Exception Classes

Use these instead of generic exceptions for better error tracking:

| Exception | Use Case | HTTP Status |
|-----------|----------|-------------|
| `ValidationError` | Data validation failures | 400 |
| `AuthenticationError` | Authentication failures | 401 |
| `PermissionError` | Authorization failures | 403 |
| `ResourceNotFoundError` | Resource not found | 404 |
| `ResourceConflictError` | Duplicate resources | 409 |
| `BusinessLogicError` | Business rule violations | 422 |
| `ExternalServiceError` | External API failures | 502 |
| `DatabaseError` | Database operation failures | 500 |
| `ConfigurationError` | Configuration errors | 500 |
| `RateLimitError` | Rate limit exceeded | 429 |

Example:

```python
from config.exceptions import ResourceNotFoundError, ValidationError

def get_note(note_id):
    try:
        note = Note.objects.get(id=note_id)
    except Note.DoesNotExist:
        raise ResourceNotFoundError(
            f"Note with ID {note_id} not found",
            note_id=note_id
        )
    return note

def update_note(note, data):
    if not data.get('title'):
        raise ValidationError(
            "Title is required",
            field='title',
            provided=data
        )
```

## Model Error Handling

```python
from django.db import IntegrityError
from config.logging_utils import get_logger
from config.exceptions import DatabaseError

logger = get_logger(__name__)

def create_note(user, title, content):
    try:
        note = Note.objects.create(
            user=user,
            title=title,
            content=content
        )
        logger.info(f"Note created: {note.id}", extra={
            'context': {'note_id': note.id, 'user_id': user.id}
        })
        return note
    except IntegrityError as e:
        logger.error("Database integrity error", exc_info=True)
        raise DatabaseError(
            "Failed to create note due to constraint violation",
            user_id=user.id,
            title=title
        )
```

## Middleware Features

### Automatic Error Handling

All unhandled exceptions are automatically:
1. Logged with full context
2. Sent to Sentry
3. Returned as appropriate error responses (JSON for APIs, HTML for web)

### Request ID Tracking

Every request gets a unique ID that appears in:
- Logs
- Sentry events
- Response headers (`X-Request-ID`)

Use it to trace requests across systems.

### Slow Request Detection

Requests taking longer than 3 seconds are automatically logged as warnings.

## Logging Levels

- **DEBUG**: Detailed information for debugging
- **INFO**: General information about application flow
- **WARNING**: Something unexpected but not an error
- **ERROR**: Errors that should be investigated
- **CRITICAL**: Severe errors requiring immediate attention

## Environment Variables

Configure logging behavior via environment variables:

```bash
# Log level for application logs
LOG_LEVEL=INFO

# Log level for Django core
DJANGO_LOG_LEVEL=WARNING

# Sentry configuration
SENTRY_DSN=your-sentry-dsn
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.1
```

## Log Files

Logs are stored in the `logs/` directory:

- `django.log` - All application logs
- `error.log` - ERROR level and above
- `security.log` - Security-related logs

Files automatically rotate at 10MB with 5 backups.

## Best Practices

### DO:
✅ Use custom exception classes for application errors
✅ Include relevant context in log messages
✅ Use appropriate log levels
✅ Log exceptions with `exc_info=True`
✅ Use structured logging with extra context

### DON'T:
❌ Log sensitive data (passwords, tokens, credit cards)
❌ Use print statements for debugging
❌ Swallow exceptions without logging
❌ Log at DEBUG level in production
❌ Include PII in logs without sanitization

## Testing Logging

To test that logging and Sentry integration work:

```python
from config.logging_utils import get_logger
import sentry_sdk

logger = get_logger(__name__)

# Test log message
logger.info("Test log message")

# Test Sentry integration
try:
    1 / 0
except Exception as e:
    sentry_sdk.capture_exception(e)
    logger.error("Test error", exc_info=True)
```

## Viewing Logs in Sentry

1. Go to your Sentry dashboard
2. Navigate to Issues to see all errors
3. Click on an issue to see:
   - Full stack trace
   - Request context
   - User information
   - Breadcrumbs (user actions before error)
   - Tags for filtering

## Troubleshooting

### Logs not appearing in Sentry

1. Check SENTRY_DSN is set in environment
2. Verify Gunicorn/application process has the environment variable
3. Check log level is ERROR or above for Sentry events
4. Review `logs/django.log` for local logs

### Request ID not appearing

Ensure middleware order is correct - RequestIDMiddleware should be early in the stack.

### Performance issues

If logging impacts performance:
1. Reduce LOG_LEVEL in production (WARNING or ERROR)
2. Disable DEBUG level logging
3. Adjust Sentry sample rates

## Example: Complete View with Error Handling

```python
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from config.logging_utils import get_logger, log_with_context
from config.exceptions import ValidationError, ResourceNotFoundError
from .models import Note

logger = get_logger(__name__)

@login_required
def note_detail(request, note_id):
    # Log request with context
    log_with_context(
        logger,
        'info',
        f'User accessing note detail',
        request=request,
        extra={'note_id': note_id}
    )

    try:
        # Get note
        note = Note.objects.get(id=note_id, user=request.user)

        # Process any POST data
        if request.method == 'POST':
            title = request.POST.get('title')
            if not title:
                raise ValidationError(
                    "Title is required",
                    field='title'
                )

            note.title = title
            note.save()

            logger.info(
                f"Note updated successfully",
                extra={'context': {'note_id': note_id}}
            )

        return render(request, 'notes/detail.html', {'note': note})

    except Note.DoesNotExist:
        # Custom exception automatically logged
        raise ResourceNotFoundError(
            f"Note {note_id} not found",
            note_id=note_id,
            user_id=request.user.id
        )
    except Exception as e:
        # Unexpected errors automatically logged and sent to Sentry
        logger.error(f"Unexpected error in note_detail", exc_info=True)
        raise
```

## Support

For issues with logging or Sentry integration, check:
1. Application logs in `logs/` directory
2. Sentry dashboard for captured events
3. Django settings in `config/settings/`
