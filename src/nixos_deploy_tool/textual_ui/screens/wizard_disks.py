from __future__ import annotations

import asyncio
import threading

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Label, Select, Static

from nixos_deploy_tool.services.deploy import DeployService
from nixos_deploy_tool.textual_ui.base import BaseScreen
from nixos_deploy_tool.textual_ui.screens.wizard_confirm import WizardConfirmScreen
from nixos_deploy_tool.textual_ui.screens.wizard_partitions import WizardPartitionScreen
from nixos_deploy_tool.textual_ui.wizard_state import WizardState


class WizardDiskScreen(BaseScreen):
    CSS_PATH = "../styles/wizard.tcss"

    def __init__(self, svc: DeployService, state: WizardState,
                 flake_devices: dict) -> None:
        super().__init__()
        self._svc = svc
        self._state = state
        self._flake_devices = flake_devices.get("disk", {})
        self.disks_loaded = asyncio.Event()
        self._target_disks: list[dict] = []
        self._selectors: list[Select] = []

    def compose_content(self) -> ComposeResult:
        yield Vertical(
            Static("", id="disk-status"),
            Label("Flake declared disks:", classes="label"),
            DataTable(id="flake-disks-table"),
            Label(f"Available on '{self._state.ssh_target}':", classes="label"),
            DataTable(id="target-disks-table"),
            Static("", id="disk-selectors-label"),
            Vertical(id="disk-selectors"),
            Horizontal(
                Button("Continue", id="continue", variant="primary"),
                Button("Back", id="back"),
                classes="button-row",
            ),
        )

    async def on_mount(self) -> None:
        self._loop = asyncio.get_running_loop()
        self.disks_loaded.clear()
        self._populate_flake_table()
        self.query_one("#disk-status", Static).update("Probing target disks...")
        self.query_one("#continue", Button).disabled = True
        threading.Thread(target=self._load_disks_thread, daemon=True).start()

    def _populate_flake_table(self) -> None:
        table = self.query_one("#flake-disks-table", DataTable)
        table.add_columns("Disk", "Device", "Partitions")
        for name, disk in self._flake_devices.items():
            device = disk.get("device", "?")
            content = disk.get("content", {})
            part_names = DeployService._parse_partition_names(content)
            parts_str = ", ".join(part_names) if part_names else "(no partitions)"
            table.add_row(name, device, parts_str)

    def _load_disks_thread(self) -> None:
        try:
            ssh = self._svc.create_ssh(self._state.ssh_target, self._state.ssh_key)
            self._target_disks = ssh.list_disks()
            self.app.call_from_thread(self._populate_target_table)
        except Exception as exc:
            self.app.call_from_thread(self._disk_load_error, str(exc))
        finally:
            self._loop.call_soon_threadsafe(self.disks_loaded.set)

    def _populate_target_table(self) -> None:
        table = self.query_one("#target-disks-table", DataTable)
        table.add_columns("Device", "Size", "Model", "Partitions")
        for disk in self._target_disks:
            children = disk.get("children") or []
            parts = ", ".join(
                f"{c['name']}({c.get('fstype', '?')})" for c in children
            ) if children else "(empty)"
            table.add_row(
                f"/dev/{disk['name']}",
                disk.get("size", "?"),
                disk.get("model", "") or "?",
                parts,
            )
        self.query_one("#disk-status", Static).update(
            f"Found {len(self._target_disks)} disk(s)"
        )
        self._build_disk_selectors()

    def _build_disk_selectors(self) -> None:
        options = [
            (f"/dev/{d['name']}", f"/dev/{d['name']}")
            for d in self._target_disks
        ]
        if not options:
            self.query_one("#disk-status", Static).update(
                "No target disks found — cannot proceed"
            )
            self.query_one("#continue", Button).disabled = True
            return

        container = self.query_one("#disk-selectors", Vertical)
        container.remove_children()
        label = self.query_one("#disk-selectors-label", Static)
        label.update("Map flake disks to target devices:")

        for name in self._flake_devices:
            select = Select(
                options=options,
                prompt=f"Disk '{name}' on target:",
                id=f"disk-map-{name}",
            )
            self._selectors.append(select)
            container.mount(select)

        self.query_one("#continue", Button).disabled = False

    def _disk_load_error(self, msg: str) -> None:
        self.query_one("#disk-status", Static).update(f"Error probing disks: {msg}")
        self.query_one("#continue", Button).disabled = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "continue":
            self._store_selections_and_advance()
        elif event.button.id == "back":
            self.app.pop_screen()

    def _store_selections_and_advance(self) -> None:
        self._state.disko_disk_overrides = {}
        for sel in self._selectors:
            disk_name = sel.id.replace("disk-map-", "")
            if sel.value:
                self._state.disko_disk_overrides[disk_name] = str(sel.value)

        if self._state.missing_partlabels:
            self.app.push_screen(WizardPartitionScreen(self._svc, self._state))
        else:
            self.app.push_screen(WizardConfirmScreen(self._svc, self._state))
