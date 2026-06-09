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

    def compose_content(self) -> ComposeResult:
        yield Vertical(
            Static("", id="disk-status"),
            Label("Available disks on target:", classes="label"),
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
            f"Found {len(self._target_disks)} disk(s) — select one"
        )
        if self._target_disks:
            self.query_one("#target-disks-table", DataTable).focus()

    def _update_planned_layout(self) -> None:
        if not self._state.manual_disk_selection:
            self.query_one("#planned-layout", Static).update("")
            self.query_one("#continue", Button).disabled = True
            return

        # Find the selected disk info
        selected = None
        for disk in self._target_disks:
            if f"/dev/{disk['name']}" == self._state.manual_disk_selection:
                selected = disk
                break

        info = f"Selected: {self._state.manual_disk_selection}"
        if selected:
            children = selected.get("children") or []
            existing = ", ".join(
                f"{c['name']}({c.get('fstype', '?')})" for c in children
            ) if children else "(empty)"
            info += f"  |  Existing partitions: {existing}"
        self.query_one("#selected-disk-info", Static).update(info)

        # Show planned layout from flake
        lines: list[str] = []
        for name, disk in self._flake_devices.items():
            content = disk.get("content", {})
            part_names = DeployService._parse_partition_names(content)
            if part_names:
                lines.append(f"Will create on {self._state.manual_disk_selection}:")
                for pn in part_names:
                    content_type = disk.get("content", {})
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
        # Map selected disk to first flake disk (if available)
        flake_disk_name = next(iter(self._flake_devices.keys()), "")
        if flake_disk_name:
            self._state.disko_disk_overrides = {flake_disk_name: self._state.manual_disk_selection}
        else:
            self._state.disko_disk_overrides = {"main": self._state.manual_disk_selection}

        self._state.disko_mode = "mount"

        if self._state.missing_partlabels:
            self.app.push_screen(WizardPartitionScreen(self._svc, self._state))
        else:
            self.app.push_screen(WizardConfirmScreen(self._svc, self._state))
