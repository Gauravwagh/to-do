"""
Logging utilities for structured logging with automatic context.
"""
import logging
import functools
import traceback
from typing import Any, Dict, Optional
from django.http import HttpRequest
import sentry_sdk


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def get_request_context(request: Optional[HttpRequest] = None) -> Dict[str, Any]:
    """
    Extract context information from Django request.

    Args:
        request: Django HttpRequest object

    Returns:
        Dictionary with request context
    """
    if not request:
        return {}

    context = {
        'method': request.method,
        'path': request.path,
        'query_string': request.GET.dict() if request.GET else {},
    }

    # Add user information if available
    if hasattr(request, 'user') and request.user.is_authenticated:
        context['user_id'] = request.user.id
        context['username'] = request.user.username
        context['user_email'] = getattr(request.user, 'email', None)

    # Add client IP
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        context['client_ip'] = x_forwarded_for.split(',')[0].strip()
    else:
        context['client_ip'] = request.META.get('REMOTE_ADDR')

    # Add user agent
    context['user_agent'] = request.META.get('HTTP_USER_AGENT', '')

    return context


def log_with_context(logger: logging.Logger, level: str, message: str,
                     request: Optional[HttpRequest] = None,
                     extra: Optional[Dict] = None,
                     exc_info: bool = False):
    """
    Log a message with automatic context from request.

    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        request: Optional Django request object
        extra: Additional context data
        exc_info: Whether to include exception info
    """
    context = get_request_context(request) if request else {}

    if extra:
        context.update(extra)

    log_func = getattr(logger, level.lower())
    log_func(message, extra={'context': context}, exc_info=exc_info)


def log_exception(logger: logging.Logger, exc: Exception,
                 request: Optional[HttpRequest] = None,
                 extra: Optional[Dict] = None):
    """
    Log an exception with full context and send to Sentry.

    Args:
        logger: Logger instance
        exc: Exception to log
        request: Optional Django request object
        extra: Additional context data
    """
    context = get_request_context(request) if request else {}

    if extra:
        context.update(extra)

    # Add exception details
    context['exception_type'] = type(exc).__name__
    context['exception_message'] = str(exc)

    # Log with full traceback
    logger.error(
        f"Exception occurred: {type(exc).__name__}: {str(exc)}",
        extra={'context': context},
        exc_info=True
    )

    # Send to Sentry with context
    with sentry_sdk.push_scope() as scope:
        for key, value in context.items():
            scope.set_tag(key, value)
        sentry_sdk.capture_exception(exc)


def log_decorator(logger: Optional[logging.Logger] = None,
                 level: str = 'info',
                 log_args: bool = False,
                 log_result: bool = False):
    """
    Decorator to automatically log function calls and exceptions.

    Args:
        logger: Logger instance (if None, creates one from function name)
        level: Log level for successful calls
        log_args: Whether to log function arguments
        log_result: Whether to log function result

    Usage:
        @log_decorator(log_args=True)
        def my_function(arg1, arg2):
            return arg1 + arg2
    """
    def decorator(func):
        nonlocal logger
        if logger is None:
            logger = logging.getLogger(func.__module__)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__name__}"

            # Log function call
            context = {'function': func_name}
            if log_args:
                context['args'] = str(args)[:200]  # Limit length
                context['kwargs'] = str(kwargs)[:200]

            try:
                result = func(*args, **kwargs)

                if log_result:
                    context['result'] = str(result)[:200]

                log_func = getattr(logger, level.lower())
                log_func(f"Function executed: {func_name}", extra={'context': context})

                return result

            except Exception as exc:
                context['exception'] = str(exc)
                logger.error(
                    f"Exception in function {func_name}: {str(exc)}",
                    extra={'context': context},
                    exc_info=True
                )

                # Send to Sentry
                with sentry_sdk.push_scope() as scope:
                    scope.set_context("function_call", context)
                    sentry_sdk.capture_exception(exc)

                raise

        return wrapper
    return decorator


class LoggerAdapter(logging.LoggerAdapter):
    """
    Custom logger adapter that automatically includes context in all log messages.
    """

    def process(self, msg, kwargs):
        # Add context from extra if not already present
        if 'extra' not in kwargs:
            kwargs['extra'] = {}

        if 'context' not in kwargs['extra']:
            kwargs['extra']['context'] = {}

        # Merge any additional context from the adapter
        if self.extra:
            kwargs['extra']['context'].update(self.extra)

        return msg, kwargs


def get_context_logger(name: str, **context) -> LoggerAdapter:
    """
    Get a logger adapter with predefined context.

    Args:
        name: Logger name
        **context: Context to include in all log messages

    Returns:
        LoggerAdapter with context

    Usage:
        logger = get_context_logger(__name__, service='payment', operation='charge')
        logger.info("Processing payment")
    """
    logger = logging.getLogger(name)
    return LoggerAdapter(logger, context)
