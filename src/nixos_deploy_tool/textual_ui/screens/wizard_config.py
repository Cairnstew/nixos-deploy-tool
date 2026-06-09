from __future__ import annotations

import threading

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input, Label, RadioSet, RadioButton, Static

from nixos_deploy_tool.services.deploy import DeployService
from nixos_deploy_tool.textual_ui.base import BaseScreen
from nixos_deploy_tool.textual_ui.screens.wizard_deploy import WizardDeployScreen
from nixos_deploy_tool.textual_ui.screens.wizard_partitions import WizardPartitionScreen
from nixos_deploy_tool.textual_ui.wizard_state import WizardState


class WizardConfigScreen(BaseScreen):
    CSS_PATH = "../styles/wizard.tcss"

    def __init__(self, svc: DeployService, state: WizardState) -> None:
        super().__init__()
        self._svc = svc
        self._state = state

    def compose_content(self) -> ComposeResult:
        yield Vertical(
            Static(f"Host: {self._state.host_name}", id="host-display"),
            Static("", id="disko-summary"),
            Label("SSH target address (user@host or IP):"),
            Input(
                placeholder=self._state.host_name,
                id="addr-input",
            ),
            Label("Disko mode:"),
            RadioSet(
                RadioButton("Auto-detect", id="mode-auto", value=True),
                RadioButton("mount (existing partitions)", id="mode-mount"),
                RadioButton("create (destructive)", id="mode-create"),
                RadioButton("skip (no disko)", id="mode-skip"),
                id="mode-select",
            ),
            Label("Extra arguments for nixos-anywhere:"),
            Input(
                placeholder="e.g. --phases kexec,install,reboot",
                id="extra-args-input",
            ),
            Horizontal(
                Button("Validate Partitions & Deploy", id="validate-deploy", variant="primary"),
                Button("Deploy (skip validation)", id="deploy-skip", variant="default"),
                classes="button-row",
            ),
            Static("", id="status"),
        )

    def on_mount(self) -> None:
        threading.Thread(target=self._eval_disko_summary, daemon=True).start()
        self.query_one("#addr-input", Input).focus()

    def _update_disko_summary(self, msg: str) -> None:
        self.query_one("#disko-summary", Static).update(msg)

    def _eval_disko_summary(self) -> None:
        summary = self._svc.get_disko_summary(self._state.host_name)
        self.call_from_thread(self._update_disko_summary, summary)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        addr_input = self.query_one("#addr-input", Input)
        self._state.ssh_target = addr_input.value or self._state.host_name
        self._state.ssh_key = self._svc.resolve_ssh_key()
        extra_input = self.query_one("#extra-args-input", Input)
        self._state.extra_args = extra_input.value or None
        mode_select = self.query_one("#mode-select", RadioSet)
        pressed_id = mode_select.pressed_button.id if mode_select.pressed_button else "mode-auto"
        mode_map = {
            "mode-auto": "auto",
            "mode-mount": "mount",
            "mode-create": "create",
            "mode-skip": "skip",
        }
        self._state.disko_mode = mode_map.get(pressed_id, "auto")

        if event.button.id == "validate-deploy":
            self._validate_and_deploy()
        elif event.button.id == "deploy-skip":
            self._go_to_deploy()

    def _validate_and_deploy(self) -> None:
        self.query_one("#status", Static).update("Starting validation...")
        self.query_one("#validate-deploy", Button).disabled = True
        self.query_one("#deploy-skip", Button).disabled = True
        thread = threading.Thread(target=self._validation_thread, daemon=True)
        thread.start()

    def _set_status(self, msg: str) -> None:
        self.query_one("#status", Static).update(msg)

    def _validation_thread(self) -> None:
        missing: list[str] = []
        try:
            if self._state.disko_mode in ("mount", "auto"):
                self.call_from_thread(self._set_status, "Evaluating disko config...")
                try:
                    devices = self._svc.get_disko_devices(self._state.host_name)
                except Exception:
                    self.call_from_thread(
                        self._set_status, "No disko devices found — skipping validation"
                    )
                    self.call_from_thread(self._go_to_deploy)
                    return

                from nixos_deploy_tool.core.ssh import SshClient

                ssh = SshClient(self._state.ssh_target, self._state.ssh_key)
                expected: list[str] = []
                for disk_name, disk in devices.get("disk", {}).items():
                    partitions = disk.get("content", {}).get("partitions", []) or []
                    for part in partitions:
                        part_name = part.get("name", "")
                        if part_name:
                            expected.append(f"disk-{disk_name}-{part_name}")

                for i, label in enumerate(expected):
                    self.call_from_thread(
                        self._set_status,
                        f"Checking partition {i + 1} of {len(expected)}: {label}...",
                    )
                    if not ssh.partition_exists(label):
                        missing.append(label)

                if missing:
                    self.call_from_thread(
                        self._set_status, f"{len(missing)} partition(s) missing"
                    )
                else:
                    self.call_from_thread(
                        self._set_status, f"All {len(expected)} partitions found"
                    )
        except Exception as exc:
            self.call_from_thread(self._validation_error, str(exc))
            return

        self._state.missing_partlabels = missing
        if missing:
            self.call_from_thread(self._push_partitions)
        else:
            self.call_from_thread(self._go_to_deploy)

    def _push_partitions(self) -> None:
        self.app.push_screen(WizardPartitionScreen(self._svc, self._state))

    def _validation_error(self, msg: str) -> None:
        self.query_one("#status", Static).update(f"Validation error: {msg}")
        self.query_one("#validate-deploy", Button).disabled = False
        self.query_one("#deploy-skip", Button).disabled = False

    def _go_to_deploy(self) -> None:
        self.app.push_screen(WizardDeployScreen(self._svc, self._state))
