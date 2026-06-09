from __future__ import annotations

import asyncio
import threading

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, RichLog, Static

from nixos_deploy_tool.models.result import BaseResult
from nixos_deploy_tool.services.deploy import DeployService
from nixos_deploy_tool.textual_ui.base import BaseScreen
from nixos_deploy_tool.textual_ui.wizard_state import WizardState


class WizardDeployScreen(BaseScreen):
    CSS_PATH = "../styles/wizard.tcss"

    def __init__(self, svc: DeployService, state: WizardState) -> None:
        super().__init__()
        self._svc = svc
        self._state = state
        self.deploy_done = asyncio.Event()

    def compose_content(self) -> ComposeResult:
        yield Vertical(
            Label(f"Deploying {self._state.host_name}...", id="deploy-title"),
            RichLog(id="deploy-log", highlight=True, max_lines=200),
            Static("", id="deploy-status"),
            Button("Back to Dashboard", id="back", variant="primary", disabled=True),
        )

    async def on_mount(self) -> None:
        self._loop = asyncio.get_running_loop()
        self.deploy_done.clear()
        self._log = self.query_one("#deploy-log", RichLog)
        self._run_deploy()

    def _run_deploy(self) -> None:
        thread = threading.Thread(target=self._deploy_thread, daemon=True)
        thread.start()

    def _deploy_thread(self) -> None:
        self._svc.run_streaming(
            self._state.host_name,
            addr=self._state.ssh_target,
            extra_args=self._state.extra_args,
            disko_mode=self._state.disko_mode,
            disk_overrides=self._state.disko_disk_overrides or None,
            on_output=lambda line: self.app.call_from_thread(self._log.write, line),
            on_done=lambda result: self.app.call_from_thread(self._on_result, result),
        )
        self._loop.call_soon_threadsafe(self.deploy_done.set)

    def _on_result(self, result: BaseResult) -> None:
        if result.ok:
            self.query_one("#deploy-status", Static).update("Deploy successful!")
        else:
            self.query_one("#deploy-status", Static).update(result.message)
        self.query_one("#back", Button).disabled = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            app = self.app
            while len(app.screen_stack) > 1:
                app.pop_screen()
