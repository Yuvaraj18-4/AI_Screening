class AppError(Exception):
    """Base application exception."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status_code=401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Access forbidden"):
        super().__init__(message, status_code=403)


class ConflictError(AppError):
    def __init__(self, message: str = "Conflict"):
        super().__init__(message, status_code=409)


class ValidationError(AppError):
    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, status_code=422)


class RateLimitError(AppError):
    def __init__(self, message: str = "Too many requests. Please try again later."):
        super().__init__(message, status_code=429)
