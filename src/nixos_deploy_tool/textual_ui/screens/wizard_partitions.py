from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Label, Static

from nixos_deploy_tool.core.ssh import SshClient
from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.services.deploy import DeployService
from nixos_deploy_tool.textual_ui.screens.wizard_deploy import WizardDeployScreen
from nixos_deploy_tool.textual_ui.wizard_state import WizardState


CREATE_PARTITION_CMD = (
    'sudo sgdisk -n 0:0:0 -t 0:8300 -c 0:{label} {device} '
    '&& sudo mkfs.ext4 -L {label} /dev/disk/by-partlabel/{label}'
)


class WizardPartitionScreen(Screen[None]):
    CSS_PATH = "../styles/wizard.tcss"
    state: WizardState

    def __init__(self, state: WizardState) -> None:
        super().__init__()
        self.state = state

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Label("Partition Validation Results", classes="title"),
            Static(
                f"The following partitions are missing on '{self.state.ssh_target}':",
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
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#partitions-table", DataTable)
        table.add_columns("Partition", "Status")
        for label in self.state.missing_partlabels:
            table.add_row(label, "missing")
        table.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create-deploy":
            self._create_all_and_deploy()
        elif event.button.id == "skip-deploy":
            self._go_to_deploy()
        elif event.button.id == "back":
            self.app.pop_screen()

    def _create_all_and_deploy(self) -> None:
        status = self.query_one("#status", Static)
        app = self.app
        ctx = getattr(app, "context", None)
        cfg = ctx.config if ctx else DeployConfig()
        svc = DeployService(cfg)
        try:
            devices_raw = svc._eval_disko_devices(self.state.host_name)
        except Exception:
            status.update("Error: could not evaluate disko config")
            return
        ssh = SshClient(self.state.ssh_target, self.state.ssh_key)
        for disk_name, disk in devices_raw.get("disk", {}).items():
            device = disk.get("device", "")
            partitions = disk.get("content", {}).get("partitions", []) or []
            for part in partitions:
                part_name = part.get("name", "")
                label = f"disk-{disk_name}-{part_name}"
                if label in self.state.missing_partlabels:
                    status.update(f"Creating partition '{label}' on {device}...")
                    try:
                        ssh.create_partition(device, label)
                        fstype = (
                            part.get("content", {}).get("format", "")
                            or "ext4"
                        )
                        part_path = ssh.path_for_partlabel(label)
                        if part_path:
                            ssh.mkfs(part_path, fstype, label)
                    except RuntimeError as exc:
                        status.update(f"Failed to create {label}: {exc}")
                        return
        status.update("All partitions created successfully")
        self._go_to_deploy()

    def _go_to_deploy(self) -> None:
        self.app.push_screen("wizard_deploy", self.state)
