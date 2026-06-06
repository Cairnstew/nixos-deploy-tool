from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static


class MainScreen(Screen[None]):
    CSS_PATH = "../styles/main.tcss"
    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static("nixos-deploy-tool", classes="title"),
            Static("NixOS deployment dashboard", classes="subtitle"),
            Horizontal(
                Button("Build ISO", id="iso", variant="primary"),
                Button("Deploy", id="deploy", variant="primary"),
                Button("Secrets", id="secrets", variant="primary"),
                Button("Tailscale", id="tailscale", variant="primary"),
                classes="button-row",
            ),
            classes="container",
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.app.log(f"Button pressed: {event.button.id}")
