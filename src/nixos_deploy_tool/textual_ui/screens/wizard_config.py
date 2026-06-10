from __future__ import annotations

import asyncio
import threading

from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input, Label, RadioSet, RadioButton, Select, Static

from nixos_deploy_tool.services.deploy import DeployService
from nixos_deploy_tool.textual_ui.base import BaseScreen
from nixos_deploy_tool.textual_ui.screens.wizard_confirm import WizardConfirmScreen
from nixos_deploy_tool.textual_ui.screens.wizard_deploy import WizardDeployScreen
from nixos_deploy_tool.textual_ui.screens.wizard_disks import WizardDiskScreen
from nixos_deploy_tool.textual_ui.screens.wizard_manual import WizardManualScreen
from nixos_deploy_tool.textual_ui.screens.wizard_partitions import WizardPartitionScreen
from nixos_deploy_tool.textual_ui.wizard_state import WizardState


class WizardConfigScreen(BaseScreen):
    CSS_PATH = "../styles/wizard.tcss"

    def __init__(self, svc: DeployService, state: WizardState) -> None:
        super().__init__()
        self._svc = svc
        self._state = state
        self.validation_done = asyncio.Event()
        self._stashed_devices: dict[str, Any] | None = None

    def compose_content(self) -> ComposeResult:
        yield Vertical(
            Static(f"Host: {self._state.host_name}", id="host-display"),
            Static("", id="disko-summary"),
            Label("SSH target address (user@host or IP):"),
            Input(
                placeholder=self._state.host_name,
                id="addr-input",
            ),
            Label("Disk configuration:"),
            Select(
                options=[
                    ("Use flake config", "flake"),
                    ("Configure manually", "manual"),
                    ("Skip disko", "skip"),
                ],
                value=self._state.config_source,
                id="config-source-select",
            ),
            Static("", id="manual-coming-soon"),
            Vertical(
                Label("Disko mode:"),
                RadioSet(
                    RadioButton("Auto-detect", id="mode-auto"),
                    RadioButton("mount (existing partitions)", id="mode-mount", value=True),
                    RadioButton("create (destructive)", id="mode-create"),
                    RadioButton("skip (no disko)", id="mode-skip"),
                    id="mode-select",
                ),
                Label("Extra arguments for nixos-anywhere:"),
                Input(
                    placeholder="e.g. --phases kexec,install,reboot",
                    id="extra-args-input",
                ),
                id="disko-flake-group",
            ),
            Horizontal(
                Button("Validate Partitions & Deploy", id="validate-deploy", variant="primary"),
                Button("Deploy (skip validation)", id="deploy-skip", variant="default"),
                classes="button-row",
            ),
            Static("", id="status"),
        )

    async def on_mount(self) -> None:
        self._loop = asyncio.get_running_loop()
        self.validation_done.clear()
        threading.Thread(target=self._eval_disko_summary, daemon=True).start()
        # Pre-fill inputs from state (set by CLI flags)
        if self._state.ssh_target:
            self.query_one("#addr-input", Input).value = self._state.ssh_target
        else:
            self.query_one("#addr-input", Input).focus()
        if self._state.extra_args:
            self.query_one("#extra-args-input", Input).value = self._state.extra_args
        self._apply_config_source()
        # Auto-advance when all config is pre-filled via CLI
        if self._state.ssh_target and self._state.config_source == "skip":
            self._go_to_deploy()
            return
        if self._state.ssh_target and self._state.config_source == "flake" and self._state.disko_mode in ("create", "skip"):
            self._auto_validate_and_deploy()
            return
        if self._state.ssh_target and self._state.config_source == "manual":
            self._validate_and_deploy()
            return

    def _update_disko_summary(self, msg: str) -> None:
        self.query_one("#disko-summary", Static).update(msg)

    def _eval_disko_summary(self) -> None:
        summary = self._svc.get_disko_summary(self._state.host_name)
        self.app.call_from_thread(self._update_disko_summary, summary)

    def _apply_config_source(self) -> None:
        source = self._state.config_source
        self.query_one("#disko-flake-group", Vertical).display = source == "flake"
        self.query_one("#extra-args-input", Input).display = source == "flake"
        msg = self.query_one("#manual-coming-soon", Static)
        msg.display = False
        sel = self.query_one("#config-source-select", Select)
        sel.value = source

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "config-source-select":
            self._state.config_source = str(event.value)
            self._apply_config_source()
            # Auto-advance when all config is pre-filled via CLI
            if self._state.ssh_target and self._state.config_source == "skip":
                self._go_to_deploy()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        addr_input = self.query_one("#addr-input", Input)
        self._state.ssh_target = addr_input.value or self._state.host_name
        self._state.ssh_key = self._svc.resolve_ssh_key()
        self._state.config_source = str(self.query_one("#config-source-select", Select).value)

        if self._state.config_source == "skip":
            self._state.disko_mode = "skip"
            self._go_to_deploy()
            return

        if self._state.config_source == "manual":
            self._stashed_devices = None
            self._validate_and_deploy()
            return

        # Flake path — read disko mode from radio set
        extra_input = self.query_one("#extra-args-input", Input)
        self._state.extra_args = extra_input.value or None
        mode_select = self.query_one("#mode-select", RadioSet)
        pressed_id = str(mode_select.pressed_button.id) if mode_select.pressed_button else "mode-auto"
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
            if self._state.disko_mode in ("mount", "auto", "create"):
                self.app.call_from_thread(self._set_status, "Evaluating disko config...")
                try:
                    devices = self._svc.get_disko_devices(self._state.host_name)
                except Exception:
                    if self._state.config_source == "manual":
                        self.app.call_from_thread(
                            self._eval_failed_manual,
                        )
                    else:
                        self.app.call_from_thread(
                            self._validation_error,
                            "Could not evaluate disko devices from flake — check your configuration",
                        )
                    return

                summary_parts: list[str] = []
                expected: list[str] = []
                for disk_name, disk in devices.get("disk", {}).items():
                    device = disk.get("device", "?")
                    content = disk.get("content", {})
                    part_names = DeployService._parse_partition_names(content)
                    if part_names:
                        summary_parts.append(f"  {device} ({disk_name})  →  {', '.join(part_names)}")
                    for part_name in part_names:
                        if part_name:
                            expected.append(f"disk-{disk_name}-{part_name}")
                self._state.disko_device_summary = "\n".join(summary_parts)

                ssh = self._svc.create_ssh(self._state.ssh_target, self._state.ssh_key)
                for i, label in enumerate(expected):
                    self.app.call_from_thread(
                        self._set_status,
                        f"Checking partition {i + 1} of {len(expected)}: {label}...",
                    )
                    if not ssh.partition_exists(label):
                        missing.append(label)

                if missing:
                    self.app.call_from_thread(
                        self._set_status, f"{len(missing)} partition(s) missing"
                    )
                else:
                    self.app.call_from_thread(
                        self._set_status, f"All {len(expected)} partitions found"
                    )

                self._state.missing_partlabels = missing
                self._stashed_devices = devices
                if self._state.config_source == "manual":
                    self.app.call_from_thread(self._push_manual)
                else:
                    self.app.call_from_thread(self._push_disk_selection)
            else:
                self.app.call_from_thread(self._go_to_deploy)
        except Exception as exc:
            self.app.call_from_thread(self._validation_error, str(exc))
        finally:
            self._loop.call_soon_threadsafe(self.validation_done.set)

    def _push_confirm(self) -> None:
        self.app.push_screen(WizardConfirmScreen(self._svc, self._state))

    def _push_partitions(self) -> None:
        self.app.push_screen(WizardPartitionScreen(self._svc, self._state))

    def _push_disk_selection(self) -> None:
        devices = self._stashed_devices or {}
        self.app.push_screen(WizardDiskScreen(self._svc, self._state, devices))

    def _push_manual(self) -> None:
        devices = self._stashed_devices or {}
        self.app.push_screen(WizardManualScreen(self._svc, self._state, devices))

    def _eval_failed_manual(self) -> None:
        self.query_one("#status", Static).update(
            "No disko devices found — selecting target disk manually"
        )
        self._stashed_devices = {}
        self._state.disko_device_summary = ""
        self.app.push_screen(WizardManualScreen(self._svc, self._state, {}))

    def _validation_error(self, msg: str) -> None:
        self.query_one("#status", Static).update(f"Validation error: {msg}")
        self.query_one("#validate-deploy", Button).disabled = False
        self.query_one("#deploy-skip", Button).disabled = False

    def _go_to_deploy(self) -> None:
        self.app.push_screen(WizardDeployScreen(self._svc, self._state))

    def _auto_validate_and_deploy(self) -> None:
        self._state.ssh_key = self._svc.resolve_ssh_key()
        if self._state.disko_mode == "skip":
            self._go_to_deploy()
        else:
            self._validate_and_deploy()
