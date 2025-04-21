"""Custom exceptions for the Dell AI SDK."""


class DellAIError(Exception):
    """Base exception for all Dell AI SDK exceptions."""

    pass


class AuthenticationError(DellAIError):
    """Raised when authentication fails."""

    pass


class APIError(DellAIError):
    """Raised when the API returns an error."""

    def __init__(self, message, status_code=None, response=None):
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class ResourceNotFoundError(DellAIError):
    """Raised when a requested resource is not found."""

    pass


class ValidationError(DellAIError):
    """Raised when input validation fails."""

    pass
