from __future__ import annotations

from typing import Any

import pydantic


class BaseResult(pydantic.BaseModel):
    ok: bool
    message: str = ""


class SuccessResult(BaseResult):
    ok: bool = True
    data: Any = None


class ErrorResult(BaseResult):
    ok: bool = False
    error_type: str = ""
