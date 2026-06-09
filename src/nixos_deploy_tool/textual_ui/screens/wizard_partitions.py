from __future__ import annotations

import asyncio
import threading

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Label, Static

from nixos_deploy_tool.services.deploy import DeployService
from nixos_deploy_tool.textual_ui.base import BaseScreen
from nixos_deploy_tool.textual_ui.screens.wizard_deploy import WizardDeployScreen
from nixos_deploy_tool.textual_ui.wizard_state import WizardState


class WizardPartitionScreen(BaseScreen):
    CSS_PATH = "../styles/wizard.tcss"

    def __init__(self, svc: DeployService, state: WizardState) -> None:
        super().__init__()
        self._svc = svc
        self._state = state
        self.creation_done = asyncio.Event()

    def compose_content(self) -> ComposeResult:
        yield Vertical(
            Label("Partition Validation Results", classes="title"),
            Static(
                f"The following partitions are missing on '{self._state.ssh_target}':",
                id="intro",
            ),
            DataTable(id="partitions-table"),
            Static("", id="command-display"),
            Horizontal(
                Button("Create All & Deploy", id="create-deploy", variant="primary"),
                Button("Skip & Deploy", id="skip-deploy", variant="default"),
                Button("Back", id="back", variant="default"),
                classes="button-row",
            ),
            Static("", id="status"),
        )

    async def on_mount(self) -> None:
        self._loop = asyncio.get_running_loop()
        self.creation_done.clear()
        table = self.query_one("#partitions-table", DataTable)
        table.add_columns("Partition", "Status")
        for label in self._state.missing_partlabels:
            table.add_row(label, "missing")
        if self._state.create_partitions:
            self._create_all_and_deploy()
            return
        table.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create-deploy":
            self._create_all_and_deploy()
        elif event.button.id == "skip-deploy":
            self._go_to_deploy()
        elif event.button.id == "back":
            self.app.pop_screen()

    def _create_all_and_deploy(self) -> None:
        self.query_one("#create-deploy", Button).disabled = True
        self.query_one("#skip-deploy", Button).disabled = True
        self.query_one("#back", Button).disabled = True
        self.query_one("#status", Static).update("Creating partitions...")
        thread = threading.Thread(target=self._create_thread, daemon=True)
        thread.start()

    def _create_thread(self) -> None:
        try:
            devices_raw = self._svc.get_disko_devices(self._state.host_name)
        except Exception:
            self.app.call_from_thread(
                self.query_one("#status", Static).update,
                "Error: could not evaluate disko config",
            )
            self.app.call_from_thread(self._reenable_buttons)
            return

        ssh = self._svc.create_ssh(self._state.ssh_target, self._state.ssh_key)
        for disk_name, disk in devices_raw.get("disk", {}).items():
            device = disk.get("device", "")
            partitions = disk.get("content", {}).get("partitions", []) or []
            for part in partitions:
                part_name = part.get("name", "")
                label = f"disk-{disk_name}-{part_name}"
                if label in self._state.missing_partlabels:
                    self.app.call_from_thread(
                        self.query_one("#status", Static).update,
                        f"Creating partition '{label}' on {device}...",
                    )
                    try:
                        ssh.create_partition(device, label)
                        fstype = part.get("content", {}).get("format", "") or "ext4"
                        part_path = ssh.path_for_partlabel(label)
                        if part_path:
                            ssh.mkfs(part_path, fstype, label)
                    except RuntimeError as exc:
                        self.app.call_from_thread(
                            self.query_one("#status", Static).update,
                            f"Failed to create {label}: {exc}",
                        )
                        self.app.call_from_thread(self._reenable_buttons)
                        return

        self.app.call_from_thread(
            self.query_one("#status", Static).update,
            "All partitions created successfully",
        )
        self.app.call_from_thread(self._go_to_deploy)
        self._loop.call_soon_threadsafe(self.creation_done.set)

    def _reenable_buttons(self) -> None:
        self.query_one("#create-deploy", Button).disabled = False
        self.query_one("#skip-deploy", Button).disabled = False
        self.query_one("#back", Button).disabled = False

    def _go_to_deploy(self) -> None:
        self.app.push_screen(WizardDeployScreen(self._svc, self._state))
