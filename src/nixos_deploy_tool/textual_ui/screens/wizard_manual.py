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


class WizardManualScreen(BaseScreen):
    CSS_PATH = "../styles/wizard.tcss"

    def __init__(self, svc: DeployService, state: WizardState,
                 flake_devices: dict) -> None:
        super().__init__()
        self._svc = svc
        self._state = state
        self._flake_devices = flake_devices.get("disk", {})
        self.disks_loaded = asyncio.Event()
        self._target_disks: list[dict] = []
        self._all_devices: list[dict] = []

    def compose_content(self) -> ComposeResult:
        yield Vertical(
            Static("", id="disk-status"),
            Label("Available devices on target:", classes="label"),
            DataTable(id="target-disks-table", cursor_type="row"),
            Static("", id="selected-disk-info"),
            Static("", id="planned-layout"),
            Horizontal(
                Button("Continue", id="continue", variant="primary"),
                Button("Back", id="back"),
                classes="button-row",
            ),
        )

    async def on_mount(self) -> None:
        self._loop = asyncio.get_running_loop()
        self.disks_loaded.clear()
        self.query_one("#disk-status", Static).update("Probing target disks...")
        self.query_one("#continue", Button).disabled = True
        threading.Thread(target=self._load_disks_thread, daemon=True).start()

    def _flatten_devices(self, disks: list[dict]) -> list[dict]:
        """Flatten disk + children into a flat list with a type field."""
        flat: list[dict] = []
        for disk in disks:
            flat.append({**disk, "_type": "disk"})
            for child in disk.get("children") or []:
                flat.append({**child, "_type": "part", "_parent": disk["name"]})
        return flat

    def _load_disks_thread(self) -> None:
        try:
            ssh = self._svc.create_ssh(self._state.ssh_target, self._state.ssh_key)
            raw = ssh.list_disks()
            self._target_disks = raw
            self._all_devices = self._flatten_devices(raw)
            self.app.call_from_thread(self._populate_target_table)
        except Exception as exc:
            self.app.call_from_thread(self._disk_load_error, str(exc))
        finally:
            self._loop.call_soon_threadsafe(self.disks_loaded.set)

    def _populate_target_table(self) -> None:
        table = self.query_one("#target-disks-table", DataTable)
        table.add_columns("Device", "Size", "Type", "FSTYPE", "Label/Model")
        for dev in self._all_devices:
            label = dev.get("label") or dev.get("model") or ""
            fstype = dev.get("fstype", "") or ""
            table.add_row(
                f"/dev/{dev['name']}",
                dev.get("size", ""),
                dev["_type"],
                fstype,
                label,
            )
        count = len(self._all_devices)
        self.query_one("#disk-status", Static).update(
            f"Found {count} device(s) — select a disk or partition"
        )
        if self._all_devices:
            self.query_one("#target-disks-table", DataTable).focus()

    def _find_parent_disk(self, dev_name: str) -> str:
        """Resolve a partition to its parent disk."""
        for disk in self._target_disks:
            disk_path = f"/dev/{disk['name']}"
            if dev_name == disk_path:
                return dev_name
            for child in disk.get("children") or []:
                if f"/dev/{child['name']}" == dev_name:
                    return disk_path
        return dev_name

    def _update_planned_layout(self) -> None:
        if not self._state.manual_disk_selection:
            self.query_one("#planned-layout", Static).update("")
            self.query_one("#continue", Button).disabled = True
            return

        info = f"Selected: {self._state.manual_disk_selection}"
        # Find which type of device was selected
        selected_dev = None
        for dev in self._all_devices:
            if f"/dev/{dev['name']}" == self._state.manual_disk_selection:
                selected_dev = dev
                break
        if selected_dev:
            parent = self._find_parent_disk(self._state.manual_disk_selection)
            if selected_dev["_type"] == "part":
                info += f"  |  Parent disk: {parent}"
            else:
                children = selected_dev.get("children") or []
                existing = ", ".join(
                    f"{c['name']}({c.get('fstype', '?')})" for c in children
                ) if children else "(empty)"
                info += f"  |  Partitions: {existing}"
        self.query_one("#selected-disk-info", Static).update(info)

        # Show planned layout from flake
        lines: list[str] = []
        target = self._find_parent_disk(self._state.manual_disk_selection)
        for name, fdisk in self._flake_devices.items():
            content = fdisk.get("content", {})
            part_names = DeployService._parse_partition_names(content)
            if part_names:
                lines.append(f"Will create on {target}:")
                for pn in part_names:
                    content_type = fdisk.get("content", {})
                    fstype = "ext4"
                    if isinstance(content_type.get("partitions"), list):
                        for p in content_type["partitions"]:
                            if p.get("name") == pn:
                                fc = p.get("content", {})
                                if isinstance(fc, dict):
                                    fstype = fc.get("format", "ext4")
                    lines.append(f"  {pn} ({fstype})")
        self.query_one("#planned-layout", Static).update("\n".join(lines))
        self.query_one("#continue", Button).disabled = False

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table = self.query_one("#target-disks-table", DataTable)
        row = table.get_row(event.row_key)
        self._state.manual_disk_selection = str(row[0])
        self._update_planned_layout()

    def _disk_load_error(self, msg: str) -> None:
        self.query_one("#disk-status", Static).update(f"Error probing disks: {msg}")
        self.query_one("#continue", Button).disabled = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "continue":
            self._execute_and_advance()
        elif event.button.id == "back":
            self.app.pop_screen()

    def _execute_and_advance(self) -> None:
        if not self._state.manual_disk_selection:
            return
        # Resolve partition to parent disk for nixos-anywhere --disk flag
        disk_device = self._find_parent_disk(self._state.manual_disk_selection)
        flake_disk_name = next(iter(self._flake_devices.keys()), "")
        if flake_disk_name:
            self._state.disko_disk_overrides = {flake_disk_name: disk_device}
        else:
            self._state.disko_disk_overrides = {"main": disk_device}

        self._state.disko_mode = "mount"

        # Always go through partition screen for manual mode so user can
        # create partitions even when missing_partlabels is empty
        if self._state.missing_partlabels or self._state.config_source == "manual":
            self.app.push_screen(WizardPartitionScreen(self._svc, self._state))
        else:
            self.app.push_screen(WizardConfirmScreen(self._svc, self._state))
