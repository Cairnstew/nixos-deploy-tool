from __future__ import annotations

from typing import Any

from nixos_deploy_tool.models.result import ErrorResult, SuccessResult


def build_success(data: Any = None, message: str = "OK") -> SuccessResult:
    """Build a SuccessResult with optional data payload."""
    return SuccessResult(data=data, message=message)


def build_error(message: str = "Error", error_type: str = "") -> ErrorResult:
    """Build an ErrorResult with optional machine-readable type."""
    return ErrorResult(message=message, error_type=error_type)
