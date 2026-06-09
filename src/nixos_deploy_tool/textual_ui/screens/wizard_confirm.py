from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Label, Static

from nixos_deploy_tool.services.deploy import DeployService
from nixos_deploy_tool.textual_ui.base import BaseScreen
from nixos_deploy_tool.textual_ui.screens.wizard_deploy import WizardDeployScreen
from nixos_deploy_tool.textual_ui.wizard_state import WizardState


class WizardConfirmScreen(BaseScreen):
    """Shows the resolved disk layout and asks for confirmation before deploying."""

    CSS_PATH = "../styles/wizard.tcss"

    def __init__(self, svc: DeployService, state: WizardState) -> None:
        super().__init__()
        self._svc = svc
        self._state = state

    def compose_content(self) -> ComposeResult:
        missing = self._state.missing_partlabels
        status = "All partitions found" if not missing else f"{len(missing)} partition(s) missing"
        yield Vertical(
            Label("Deploy Confirmation", classes="title"),
            Static("", id="confirm-warning"),
            Static(f"Host: {self._state.host_name}", id="confirm-host"),
            Static(f"Target: {self._state.ssh_target}", id="confirm-target"),
            Static(f"Config source: {self._state.config_source}", id="confirm-source"),
            Static(f"Disko mode: {self._state.disko_mode}", id="confirm-mode"),
            Static("", id="confirm-disko-layout"),
            Static(f"Partition status: {status}", id="confirm-status"),
            Static("", id="confirm-disk-map"),
            Horizontal(
                Button("Deploy", id="deploy", variant="primary"),
                Button("Back", id="back", variant="default"),
                classes="button-row",
            ),
            classes="container",
        )

    async def on_mount(self) -> None:
        warning = self.query_one("#confirm-warning", Static)
        devices: list[str] = []
        if self._state.disko_disk_overrides:
            devices = list(self._state.disko_disk_overrides.values())
        elif self._state.manual_disk_selection:
            devices = [self._state.manual_disk_selection]
        elif self._state.disko_device_summary:
            import re
            devices = re.findall(r"/dev/\S+", self._state.disko_device_summary)
        if devices:
            dev_list = ", ".join(devices)
            warning.update(f"[bold $error]DATA LOSS WARNING:[/] The following device(s) will be modified: {dev_list}")
        else:
            warning.update("[bold $error]DATA LOSS WARNING:[/] This will run disko and may DESTROY DATA on the target device(s)")

        layout = self.query_one("#confirm-disko-layout", Static)
        if self._state.disko_device_summary:
            layout.update(f"Disk layout:\n{self._state.disko_device_summary}")
        elif self._state.manual_disk_selection:
            layout.update(f"Selected device: {self._state.manual_disk_selection}")
        else:
            layout.update("No disko devices configured — deploying without disk management")

        disk_map = self.query_one("#confirm-disk-map", Static)
        if self._state.disko_disk_overrides:
            mapping = "; ".join(
                f"{name} → {dev}"
                for name, dev in self._state.disko_disk_overrides.items()
            )
            disk_map.update(f"Disk mapping: {mapping}")
        elif self._state.manual_disk_selection:
            disk_map.update(f"Disk: {self._state.manual_disk_selection}")
        else:
            disk_map.update("")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "deploy":
            self.app.push_screen(WizardDeployScreen(self._svc, self._state))
        elif event.button.id == "back":
            self.app.pop_screen()
