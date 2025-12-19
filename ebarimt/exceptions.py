# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
"""
eBarimt Exception Hierarchy

Provides a consistent exception hierarchy for eBarimt operations.
All custom exceptions inherit from EBarimtError for easy catching.
"""

from __future__ import annotations

from typing import Any


class EBarimtError(Exception):
    """Base exception for all eBarimt errors.
    
    All eBarimt-specific exceptions should inherit from this class.
    This allows catching all eBarimt errors with a single except clause.
    
    Example:
        try:
            create_receipt(data)
        except EBarimtError as e:
            handle_ebarimt_error(e)
    """
    
    def __init__(self, message: str, code: str | None = None, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message
    
    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "code": self.code,
            "details": self.details
        }


class EBarimtAPIError(EBarimtError):
    """Error from eBarimt API response.
    
    Raised when the eBarimt API returns an error response.
    
    Attributes:
        status_code: HTTP status code
        response_data: Raw response data from API
    """
    
    def __init__(
        self,
        message: str,
        code: str | None = None,
        status_code: int | None = None,
        response_data: Any = None
    ):
        super().__init__(message, code)
        self.status_code = status_code
        self.response_data = response_data


class EBarimtConnectionError(EBarimtError):
    """Network/connection error to eBarimt API.
    
    Raised when unable to connect to the eBarimt API server.
    """
    pass


class EBarimtAuthError(EBarimtError):
    """Authentication error with eBarimt API.
    
    Raised when API credentials are invalid or token has expired.
    """
    pass


class EBarimtValidationError(EBarimtError):
    """Validation error for eBarimt data.
    
    Raised when input data fails validation before API call.
    
    Attributes:
        field: Field that failed validation
        errors: List of validation errors
    """
    
    def __init__(
        self,
        message: str,
        field: str | None = None,
        errors: list[str] | None = None
    ):
        super().__init__(message, code="VALIDATION_ERROR")
        self.field = field
        self.errors = errors or []


class EBarimtReceiptError(EBarimtError):
    """Error during receipt operations.
    
    Raised when receipt creation, void, or query fails.
    """
    pass


class EBarimtConfigError(EBarimtError):
    """Configuration error for eBarimt.
    
    Raised when required settings are missing or invalid.
    """
    pass


class EBarimtTimeoutError(EBarimtError):
    """Timeout error for eBarimt API call.
    
    Raised when API request exceeds timeout limit.
    """
    pass


class EBarimtRateLimitError(EBarimtError):
    """Rate limit exceeded for eBarimt API.
    
    Raised when too many requests are made in a short period.
    
    Attributes:
        retry_after: Seconds to wait before retrying
    """
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int | None = None):
        super().__init__(message, code="RATE_LIMIT")
        self.retry_after = retry_after


class EBarimtOfflineError(EBarimtError):
    """Offline mode error.
    
    Raised when offline operations fail or queue is full.
    """
    pass


# Export all exceptions
__all__ = [
    "EBarimtError",
    "EBarimtAPIError",
    "EBarimtConnectionError",
    "EBarimtAuthError",
    "EBarimtValidationError",
    "EBarimtReceiptError",
    "EBarimtConfigError",
    "EBarimtTimeoutError",
    "EBarimtRateLimitError",
    "EBarimtOfflineError",
]
