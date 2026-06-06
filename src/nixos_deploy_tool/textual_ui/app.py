from textual.app import App
from textual.screen import Screen

from nixos_deploy_tool.textual_ui.screens.main import MainScreen


class DeployToolApp(App[Screen[None]]):
    SCREENS = {
        "main": MainScreen,
    }

    def on_mount(self) -> None:
        self.push_screen("main")
