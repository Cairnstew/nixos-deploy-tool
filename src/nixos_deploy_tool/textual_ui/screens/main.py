from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static


class MainScreen(Screen[None]):
    CSS_PATH = "../styles/main.tcss"
    BINDINGS = [("d", "deploy", "Deploy Wizard"), ("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static("nixos-deploy-tool", classes="title"),
            Static("NixOS deployment dashboard", classes="subtitle"),
            Horizontal(
                Button("Build ISO", id="iso", variant="primary"),
                Button("Deploy Wizard", id="deploy", variant="primary"),
                Button("Secrets", id="secrets", variant="primary"),
                Button("Tailscale", id="tailscale", variant="primary"),
                classes="button-row",
            ),
            classes="container",
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "deploy":
            self.app.push_screen("wizard_host")

    def action_deploy(self) -> None:
        self.app.push_screen("wizard_host")
