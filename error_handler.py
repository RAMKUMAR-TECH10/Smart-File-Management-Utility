"""Standardised results and friendly error messages for every operation."""

from __future__ import annotations

from typing import Any

from logger import get_logger

LOG = get_logger()


class OperationResult(str):
    """A string message that also carries structured success information."""

    def __new__(
        cls,
        message: str,
        success: bool = True,
        path: str | None = None,
        **details: Any,
    ) -> "OperationResult":
        instance = str.__new__(cls, message)
        instance.success = success
        instance.path = path
        instance.details = details
        return instance

    @classmethod
    def ok(cls, message: str, path: str | None = None, **details: Any) -> "OperationResult":
        return cls(message, True, path, **details)

    @classmethod
    def fail(cls, message: str, path: str | None = None, **details: Any) -> "OperationResult":
        return cls(f"Error: {message}", False, path, **details)


def handle_exception(operation: str, error: Exception, path: str | None = None) -> OperationResult:
    """Convert an exception into a user-facing result and log the technical detail."""
    if isinstance(error, FileNotFoundError):
        message = "File or folder not found"
    elif isinstance(error, FileExistsError):
        message = "Destination already exists"
    elif isinstance(error, PermissionError):
        message = "Permission denied (access is blocked or the file is in use)"
    elif isinstance(error, IsADirectoryError):
        message = "Expected a file but found a folder"
    elif isinstance(error, NotADirectoryError):
        message = "Expected a folder but found a file"
    elif isinstance(error, OSError):
        if getattr(error, "winerror", None) == 112:
            message = "Not enough disk space to complete the operation"
        else:
            message = f"File operation failed: {error.strerror or error}"
    else:
        message = f"Unexpected error during {operation}: {error}"

    LOG.exception("%s failed for %s: %s", operation, path or "<unknown>", error)
    return OperationResult.fail(message, path, operation=operation, exception=type(error).__name__)


def require_confirmation(confirmed: bool, action: str) -> OperationResult | None:
    """Return a failed result when a destructive action was not confirmed."""
    if not confirmed:
        return OperationResult.fail(f"{action} cancelled: confirmation is required")
    return None
