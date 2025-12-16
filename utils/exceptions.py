"""Custom exceptions for the application."""

from fastapi import HTTPException, status


class BaseAppException(Exception):
    """Base exception class for application-specific exceptions."""

    def __init__(
        self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class EmailAlreadyExistsException(BaseAppException):
    """Raised when attempting to register with an email that already exists."""

    def __init__(self, email: str):
        message = f"Email address '{email}' is already registered. Please use a different email or try logging in."
        super().__init__(message, status_code=status.HTTP_409_CONFLICT)
        self.email = email


class EmailNotFoundException(BaseAppException):
    """Raised when an email is not found in the database."""

    def __init__(self, email: str):
        message = f"Email address '{email}' not found in the database."
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND)
        self.email = email


class DatabaseOperationException(BaseAppException):
    """Raised when a database operation fails."""

    def __init__(self, operation: str, details: str = None):
        message = f"Database operation '{operation}' failed."
        if details:
            message += f" Details: {details}"
        super().__init__(message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.operation = operation
        self.details = details


class ValidationException(BaseAppException):
    """Raised when validation fails."""

    def __init__(self, field: str, message: str):
        self.field = field
        full_message = f"Validation error for field '{field}': {message}"
        super().__init__(full_message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


def handle_app_exception(exception: BaseAppException) -> HTTPException:
    """Convert application exception to FastAPI HTTPException.

    Args:
        exception: Application exception instance

    Returns:
        HTTPException: FastAPI HTTP exception
    """
    return HTTPException(
        status_code=exception.status_code,
        detail={
            "error": exception.__class__.__name__,
            "message": exception.message,
        },
    )
