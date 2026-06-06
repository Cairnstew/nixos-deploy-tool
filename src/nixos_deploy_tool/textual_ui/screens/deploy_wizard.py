from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, Static


class DeployWizardScreen(Screen[None]):
    BINDINGS = [("q", "quit", "Quit"), ("escape", "back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Deploy Wizard - Not yet implemented")
        yield Footer()

    def action_back(self) -> None:
        self.app.pop_screen()
