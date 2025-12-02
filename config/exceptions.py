"""
Custom exception classes for the application.
These exceptions provide better error handling and Sentry tracking.
"""


class ApplicationError(Exception):
    """Base exception for all application-specific errors."""
    default_message = "An application error occurred"
    status_code = 500
    error_code = "APP_ERROR"

    def __init__(self, message=None, **kwargs):
        self.message = message or self.default_message
        self.extra_data = kwargs
        super().__init__(self.message)


class ValidationError(ApplicationError):
    """Raised when validation fails."""
    default_message = "Validation failed"
    status_code = 400
    error_code = "VALIDATION_ERROR"


class AuthenticationError(ApplicationError):
    """Raised when authentication fails."""
    default_message = "Authentication failed"
    status_code = 401
    error_code = "AUTH_ERROR"


class PermissionError(ApplicationError):
    """Raised when user lacks permission."""
    default_message = "Permission denied"
    status_code = 403
    error_code = "PERMISSION_ERROR"


class ResourceNotFoundError(ApplicationError):
    """Raised when a resource is not found."""
    default_message = "Resource not found"
    status_code = 404
    error_code = "NOT_FOUND"


class ResourceConflictError(ApplicationError):
    """Raised when there's a conflict (e.g., duplicate resource)."""
    default_message = "Resource conflict"
    status_code = 409
    error_code = "CONFLICT_ERROR"


class BusinessLogicError(ApplicationError):
    """Raised when business logic validation fails."""
    default_message = "Business logic validation failed"
    status_code = 422
    error_code = "BUSINESS_LOGIC_ERROR"


class ExternalServiceError(ApplicationError):
    """Raised when an external service fails."""
    default_message = "External service error"
    status_code = 502
    error_code = "EXTERNAL_SERVICE_ERROR"


class DatabaseError(ApplicationError):
    """Raised for database-related errors."""
    default_message = "Database operation failed"
    status_code = 500
    error_code = "DATABASE_ERROR"


class ConfigurationError(ApplicationError):
    """Raised for configuration-related errors."""
    default_message = "Configuration error"
    status_code = 500
    error_code = "CONFIG_ERROR"


class RateLimitError(ApplicationError):
    """Raised when rate limit is exceeded."""
    default_message = "Rate limit exceeded"
    status_code = 429
    error_code = "RATE_LIMIT_ERROR"
