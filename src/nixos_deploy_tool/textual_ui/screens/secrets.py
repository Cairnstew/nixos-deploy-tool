from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, Static


class SecretsListScreen(Screen[None]):
    BINDINGS = [("q", "quit", "Quit"), ("escape", "back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Secrets - Not yet implemented")
        yield Footer()

    def action_back(self) -> None:
        self.app.pop_screen()
