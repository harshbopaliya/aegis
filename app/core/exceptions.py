"""
Production error handling and utilities.

Provides structured error handling, validation, and exception management
for enterprise deployments.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from fastapi import HTTPException, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """Standard error codes for API responses."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    GATEWAY_ERROR = "GATEWAY_ERROR"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    EXECUTION_FAILED = "EXECUTION_FAILED"


class ErrorResponse(BaseModel):
    """Structured error response model."""

    code: ErrorCode
    message: str
    detail: str | None = None
    request_id: str | None = None
    timestamp: str | None = None
    path: str | None = None


class GatewayException(Exception):
    """Base exception for gateway errors."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        detail: str | None = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ):
        self.code = code
        self.message = message
        self.detail = detail
        self.status_code = status_code
        super().__init__(message)

    def to_http_exception(self, request_id: str | None = None) -> HTTPException:
        """Convert to FastAPI HTTPException."""
        return HTTPException(
            status_code=self.status_code,
            detail={
                "code": self.code,
                "message": self.message,
                "detail": self.detail,
                "request_id": request_id,
            },
        )


class ValidationError(GatewayException):
    """Raised when input validation fails."""

    def __init__(self, message: str, detail: str | None = None):
        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            message=message,
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class AuthenticationError(GatewayException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed", detail: str | None = None):
        super().__init__(
            code=ErrorCode.AUTHENTICATION_ERROR,
            message=message,
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class AuthorizationError(GatewayException):
    """Raised when authorization fails."""

    def __init__(self, message: str = "Authorization denied", detail: str | None = None):
        super().__init__(
            code=ErrorCode.AUTHORIZATION_ERROR,
            message=message,
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class NotFoundError(GatewayException):
    """Raised when a resource is not found."""

    def __init__(self, resource: str, detail: str | None = None):
        super().__init__(
            code=ErrorCode.NOT_FOUND,
            message=f"{resource} not found",
            detail=detail,
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ConflictError(GatewayException):
    """Raised when there's a conflict (e.g., duplicate resource)."""

    def __init__(self, message: str, detail: str | None = None):
        super().__init__(
            code=ErrorCode.CONFLICT,
            message=message,
            detail=detail,
            status_code=status.HTTP_409_CONFLICT,
        )


class RateLimitError(GatewayException):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", detail: str | None = None):
        super().__init__(
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message=message,
            detail=detail,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )


class ServiceUnavailableError(GatewayException):
    """Raised when service is unavailable."""

    def __init__(self, message: str = "Service unavailable", detail: str | None = None):
        super().__init__(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message=message,
            detail=detail,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class InternalServerError(GatewayException):
    """Raised for internal server errors."""

    def __init__(self, message: str = "Internal server error", detail: str | None = None):
        super().__init__(
            code=ErrorCode.INTERNAL_SERVER_ERROR,
            message=message,
            detail=detail,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class PolicyViolationError(GatewayException):
    """Raised when action violates policy."""

    def __init__(self, message: str, detail: str | None = None):
        super().__init__(
            code=ErrorCode.POLICY_VIOLATION,
            message=message,
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class ApprovalRequiredError(GatewayException):
    """Raised when action requires human approval."""

    def __init__(self, request_id: str, reason: str, detail: str | None = None):
        super().__init__(
            code=ErrorCode.APPROVAL_REQUIRED,
            message="Human approval required",
            detail=detail or f"Request {request_id}: {reason}",
            status_code=status.HTTP_202_ACCEPTED,
        )


class ExecutionError(GatewayException):
    """Raised when execution fails."""

    def __init__(self, message: str, detail: str | None = None):
        super().__init__(
            code=ErrorCode.EXECUTION_FAILED,
            message=message,
            detail=detail,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def log_error(
    error: Exception,
    context: dict[str, Any] | None = None,
    level: str = "error",
) -> None:
    """Log an error with context."""
    log_fn = getattr(logger, level.lower(), logger.error)
    extra = context or {}
    log_fn(f"{type(error).__name__}: {error}", extra=extra, exc_info=True)
