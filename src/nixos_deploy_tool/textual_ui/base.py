from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from nixos_deploy_tool.textual_ui.actions import (
    LoggingMixin,
    NavigationMixin,
    RefreshMixin,
    SelectionMixin,
)


class BaseScreen(Screen[None], LoggingMixin):
    CSS_PATH = "../styles/base.tcss"
    BINDINGS = [("q", "quit", "Quit"), ("?", "help", "Help")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield from self.compose_content()
        yield Footer()

    def compose_content(self) -> ComposeResult:
        return
        yield


class ListScreen(BaseScreen, RefreshMixin, SelectionMixin):
    def compose_content(self) -> ComposeResult:
        yield DataTable()

    def load_rows(self) -> list[tuple[str, ...]]:
        return []

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        for row in self.load_rows():
            table.add_row(*row)


class DetailScreen(BaseScreen, NavigationMixin):
    def compose_content(self) -> ComposeResult:
        yield Static("")
        yield VerticalScroll()

    def load_detail(self, key: str) -> str:
        return ""
