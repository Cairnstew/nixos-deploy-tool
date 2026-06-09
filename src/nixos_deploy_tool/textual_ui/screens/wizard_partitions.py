from __future__ import annotations

import threading

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Label, Static

from nixos_deploy_tool.core.ssh import SshClient
from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.services.deploy import DeployService
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
        self.query_one("#create-deploy", Button).disabled = True
        self.query_one("#skip-deploy", Button).disabled = True
        self.query_one("#back", Button).disabled = True
        self.query_one("#status", Static).update("Creating partitions...")
        thread = threading.Thread(target=self._create_thread, daemon=True)
        thread.start()

    def _create_thread(self) -> None:
        app = self.app
        ctx = getattr(app, "context", None)
        cfg = ctx.config if ctx else DeployConfig()
        svc = DeployService(cfg)
        try:
            devices_raw = svc._eval_disko_devices(self.state.host_name)
        except Exception:
            self.call_from_thread(
                self.query_one("#status", Static).update,
                "Error: could not evaluate disko config",
            )
            self.call_from_thread(self._reenable_buttons)
            return
        ssh = SshClient(self.state.ssh_target, self.state.ssh_key)
        for disk_name, disk in devices_raw.get("disk", {}).items():
            device = disk.get("device", "")
            partitions = disk.get("content", {}).get("partitions", []) or []
            for part in partitions:
                part_name = part.get("name", "")
                label = f"disk-{disk_name}-{part_name}"
                if label in self.state.missing_partlabels:
                    self.call_from_thread(
                        self.query_one("#status", Static).update,
                        f"Creating partition '{label}' on {device}...",
                    )
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
                        self.call_from_thread(
                            self.query_one("#status", Static).update,
                            f"Failed to create {label}: {exc}",
                        )
                        self.call_from_thread(self._reenable_buttons)
                        return
        self.call_from_thread(
            self.query_one("#status", Static).update,
            "All partitions created successfully",
        )
        self.call_from_thread(self._go_to_deploy)

    def _go_to_deploy(self) -> None:
        from nixos_deploy_tool.textual_ui.screens.wizard_deploy import WizardDeployScreen
        self.app.push_screen(WizardDeployScreen(self.state))
