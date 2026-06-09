from __future__ import annotations

from textual.app import App
from textual.screen import Screen

from nixos_deploy_tool.cli.context import AppContext
from nixos_deploy_tool.textual_ui.screens.wizard_host import WizardHostScreen


class DeployToolApp(App[Screen[None]]):
    SCREENS = {
        "wizard_host": WizardHostScreen,
    }

    def __init__(self, context: AppContext | None = None) -> None:
        super().__init__()
        self.context = context

    def on_mount(self) -> None:
        self.push_screen("wizard_host")
