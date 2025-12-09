"""
Error handling middleware for automatic exception capture and logging.
"""
import logging
import traceback
import uuid
import time
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

# Import Sentry conditionally
try:
    import sentry_sdk
    SENTRY_AVAILABLE = True
except ImportError:
    sentry_sdk = None
    SENTRY_AVAILABLE = False

from config.exceptions import ApplicationError
from config.logging_utils import get_request_context, log_exception


logger = logging.getLogger(__name__)


class RequestIDMiddleware(MiddlewareMixin):
    """
    Adds a unique request ID to each request for tracking across logs.
    """

    def process_request(self, request):
        request.id = str(uuid.uuid4())
        request.start_time = time.time()

        # Set request ID in Sentry scope (if available)
        if SENTRY_AVAILABLE and sentry_sdk:
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("request_id", request.id)

        return None

    def process_response(self, request, response):
        # Add request ID to response headers
        if hasattr(request, 'id'):
            response['X-Request-ID'] = request.id

        # Log request duration
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            if duration > 3.0:  # Log slow requests (>3 seconds)
                logger.warning(
                    f"Slow request detected: {request.method} {request.path}",
                    extra={
                        'context': {
                            'request_id': getattr(request, 'id', 'unknown'),
                            'duration': duration,
                            'method': request.method,
                            'path': request.path,
                        }
                    }
                )

        return response


class ErrorHandlingMiddleware(MiddlewareMixin):
    """
    Middleware to catch and log all unhandled exceptions.
    Provides proper error responses and sends errors to Sentry.
    """

    def process_exception(self, request, exception):
        """
        Handle exceptions and return appropriate responses.
        """
        request_id = getattr(request, 'id', 'unknown')

        # Get request context
        context = get_request_context(request)
        context['request_id'] = request_id
        context['exception_type'] = type(exception).__name__

        # Handle custom application errors
        if isinstance(exception, ApplicationError):
            logger.warning(
                f"Application error: {exception.message}",
                extra={'context': {**context, **exception.extra_data}},
                exc_info=False
            )

            # Send to Sentry with lower severity (if available)
            if SENTRY_AVAILABLE and sentry_sdk:
                with sentry_sdk.push_scope() as scope:
                    scope.set_level('warning')
                    scope.set_tag('error_code', exception.error_code)
                    for key, value in context.items():
                        scope.set_tag(key, str(value)[:200])
                    sentry_sdk.capture_exception(exception)

            return self._create_error_response(
                request,
                exception.message,
                exception.status_code,
                exception.error_code,
                request_id
            )

        # Handle all other exceptions
        logger.error(
            f"Unhandled exception: {str(exception)}",
            extra={'context': context},
            exc_info=True
        )

        # Send full exception to Sentry (if available)
        if SENTRY_AVAILABLE and sentry_sdk:
            with sentry_sdk.push_scope() as scope:
                scope.set_level('error')
                scope.set_tag('request_id', request_id)
                for key, value in context.items():
                    scope.set_tag(key, str(value)[:200])

                # Add request data
                scope.set_context("request", {
                    'method': request.method,
                    'url': request.build_absolute_uri(),
                    'headers': dict(request.headers),
                    'data': self._sanitize_data(request.POST.dict()) if request.POST else None,
                })

                sentry_sdk.capture_exception(exception)

        # Return appropriate error response
        return self._create_error_response(
            request,
            "An internal server error occurred" if not settings.DEBUG else str(exception),
            500,
            "INTERNAL_ERROR",
            request_id
        )

    def _create_error_response(self, request, message, status_code, error_code, request_id):
        """Create an appropriate error response based on request type."""

        # Check if request expects JSON
        if (request.content_type == 'application/json' or
            request.META.get('HTTP_ACCEPT', '').startswith('application/json') or
            request.path.startswith('/api/')):

            return JsonResponse({
                'error': {
                    'message': message,
                    'code': error_code,
                    'request_id': request_id,
                }
            }, status=status_code)

        # Return HTML error page
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error {status_code}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 50px; }}
                .error-container {{ max-width: 600px; margin: 0 auto; }}
                h1 {{ color: #d32f2f; }}
                .error-code {{ color: #666; font-size: 14px; }}
                .request-id {{ color: #999; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="error-container">
                <h1>Error {status_code}</h1>
                <p>{message}</p>
                <p class="error-code">Error Code: {error_code}</p>
                <p class="request-id">Request ID: {request_id}</p>
            </div>
        </body>
        </html>
        """
        return HttpResponse(html_content, status=status_code)

    def _sanitize_data(self, data):
        """Remove sensitive fields from data before logging."""
        sensitive_fields = ['password', 'token', 'secret', 'api_key', 'credit_card']
        sanitized = data.copy()

        for key in list(sanitized.keys()):
            if any(field in key.lower() for field in sensitive_fields):
                sanitized[key] = '***REDACTED***'

        return sanitized


class SentryContextMiddleware(MiddlewareMixin):
    """
    Middleware to add user and request context to all Sentry events.
    """

    def process_request(self, request):
        # Skip if Sentry is not available
        if not SENTRY_AVAILABLE or not sentry_sdk:
            return None

        # Set user context in Sentry
        if hasattr(request, 'user') and request.user.is_authenticated:
            sentry_sdk.set_user({
                'id': request.user.id,
                'username': request.user.username,
                'email': getattr(request.user, 'email', None),
            })
        else:
            sentry_sdk.set_user(None)

        # Add request tags
        sentry_sdk.set_tag('method', request.method)
        sentry_sdk.set_tag('path', request.path)

        # Add breadcrumb
        sentry_sdk.add_breadcrumb(
            category='request',
            message=f'{request.method} {request.path}',
            level='info',
        )

        return None
