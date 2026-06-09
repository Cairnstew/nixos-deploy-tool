from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseRepository(ABC):
    @abstractmethod
    def list(self) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def get(self, key: str) -> dict[str, Any] | None:
        ...
