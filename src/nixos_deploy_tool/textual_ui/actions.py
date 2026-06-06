from __future__ import annotations


class LoggingMixin:
    def log_event(self, msg: str) -> None:
        self.app.log(msg)  # type: ignore[attr-defined]


class RefreshMixin:
    async def action_refresh(self) -> None:
        pass


class SelectionMixin:
    _selected: str | None = None

    @property
    def selected(self) -> str | None:
        return self._selected

    async def action_select(self) -> None:
        pass


class NavigationMixin:
    async def action_back(self) -> None:
        self.app.pop_screen()  # type: ignore[attr-defined]

    async def action_forward(self) -> None:
        pass
