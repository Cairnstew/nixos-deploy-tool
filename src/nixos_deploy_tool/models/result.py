from __future__ import annotations

from typing import Any

import pydantic


class BaseResult(pydantic.BaseModel):
    """Base for all CLI command results."""

    ok: bool
    message: str = ""


class SuccessResult(BaseResult):
    """Result indicating successful operation with optional payload."""

    ok: bool = True
    data: Any = None


class ErrorResult(BaseResult):
    """Result indicating a failed operation with optional error type."""

    ok: bool = False
    error_type: str = ""
