from __future__ import annotations

import asyncio
import threading

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Label, Select, Static

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
        self._part_choices: dict[str, str] = {}

    def compose_content(self) -> ComposeResult:
        yield Vertical(
            Label("Partition Configuration", classes="title"),
            Static(
                f"Choose which partitions to create on '{self._state.ssh_target}':",
                id="intro",
            ),
            Vertical(id="part-choices-container"),
            Horizontal(
                Button("Create Selected & Deploy", id="create-deploy", variant="primary"),
                Button("Skip All & Deploy", id="skip-deploy", variant="default"),
                Button("Back", id="back", variant="default"),
                classes="button-row",
            ),
            Static("", id="status"),
        )

    async def on_mount(self) -> None:
        self._loop = asyncio.get_running_loop()
        self.creation_done.clear()
        container = self.query_one("#part-choices-container", Vertical)
        for label in self._state.missing_partlabels:
            self._part_choices[label] = "create"
            row = Horizontal(
                Label(f"  {label}", classes="part-label"),
                Select(
                    options=[("Create", "create"), ("Skip", "skip")],
                    value="create",
                    id=f"part-{label}",
                ),
            )
            await container.mount(row)
        if self._state.create_partitions:
            self._create_selected()
            return

    def on_select_changed(self, event: Select.Changed) -> None:
        prefix = "part-"
        if event.select.id and event.select.id.startswith(prefix):
            label = event.select.id[len(prefix):]
            self._part_choices[label] = str(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create-deploy":
            self._create_selected()
        elif event.button.id == "skip-deploy":
            self._go_to_deploy()
        elif event.button.id == "back":
            self.app.pop_screen()

    def _create_selected(self) -> None:
        """Create only the partitions marked for creation."""
        to_create = [lbl for lbl, choice in self._part_choices.items() if choice == "create"]
        if not to_create:
            self._go_to_deploy()
            return
        self.query_one("#create-deploy", Button).disabled = True
        self.query_one("#skip-deploy", Button).disabled = True
        self.query_one("#back", Button).disabled = True
        self.query_one("#status", Static).update("Creating partitions...")
        thread = threading.Thread(target=self._create_thread, args=(to_create,), daemon=True)
        thread.start()

    def _create_thread(self, to_create: list[str]) -> None:
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
            device = self._state.disko_disk_overrides.get(disk_name, disk.get("device", ""))
            for part in (disk.get("content", {}).get("partitions", []) or []):
                part_name = part.get("name", "")
                label = f"disk-{disk_name}-{part_name}"
                if label in to_create:
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
            "Selected partitions created successfully",
        )
        self.app.call_from_thread(self._go_to_deploy)
        self._loop.call_soon_threadsafe(self.creation_done.set)

    def _reenable_buttons(self) -> None:
        self.query_one("#create-deploy", Button).disabled = False
        self.query_one("#skip-deploy", Button).disabled = False
        self.query_one("#back", Button).disabled = False

    def _go_to_deploy(self) -> None:
        self.app.push_screen(WizardDeployScreen(self._svc, self._state))
