from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static

from nixos_deploy_tool.services.deploy import DeployService
from nixos_deploy_tool.textual_ui.base import BaseScreen
from nixos_deploy_tool.textual_ui.screens.wizard_host import WizardHostScreen
from nixos_deploy_tool.textual_ui.wizard_state import WizardState


class MainScreen(BaseScreen):
    CSS_PATH = "../styles/main.tcss"

    def __init__(self, svc: DeployService, state: WizardState) -> None:
        super().__init__()
        self._svc = svc
        self._state = state

    def compose_content(self) -> ComposeResult:
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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "deploy":
            self.app.push_screen(WizardHostScreen(self._svc, self._state))

    def action_deploy(self) -> None:
        self.app.push_screen(WizardHostScreen(self._svc, self._state))
