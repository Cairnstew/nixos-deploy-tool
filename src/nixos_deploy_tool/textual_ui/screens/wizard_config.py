from __future__ import annotations

import json
import threading
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, RadioSet, RadioButton, Static

from nixos_deploy_tool.exceptions import NixEvalError
from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.services.deploy import DeployService
from nixos_deploy_tool.core.ssh import SshClient
from nixos_deploy_tool.textual_ui.screens.wizard_partitions import WizardPartitionScreen
from nixos_deploy_tool.textual_ui.wizard_state import WizardState


class WizardConfigScreen(Screen[None]):
    CSS_PATH = "../styles/wizard.tcss"
    state: WizardState

    def __init__(self, state: WizardState) -> None:
        super().__init__()
        self.state = state

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static(f"Host: {self.state.host_name}", id="host-display"),
            Static("", id="disko-summary"),
            Label("SSH target address (user@host or IP):"),
            Input(
                placeholder=self.state.host_name,
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
        yield Footer()

    def on_mount(self) -> None:
        self._eval_disko_summary()
        self.query_one("#addr-input", Input).focus()

    def _eval_disko_summary(self) -> None:
        app = self.app
        ctx = getattr(app, "context", None)
        cfg = ctx.config if ctx else DeployConfig()
        flake_root = Path(cfg.flake_root) if cfg.flake_root else Path.cwd()
        nix = DeployService(cfg)._nix
        try:
            raw = nix.eval_flake_json(
                f'nixosConfigurations."{self.state.host_name}".config.disko.devices',
                flake_root,
            )
            devices = json.loads(raw)
            disk_count = len(devices.get("disk", {}))
            summary = f"Disko devices: {disk_count} disk(s) configured"
            self.query_one("#disko-summary", Static).update(summary)
            self.state.disko_mode = "auto"
        except (NixEvalError, json.JSONDecodeError):
            self.query_one("#disko-summary", Static).update(
                "No disko devices found — partitions may be configured manually"
            )
            self.state.disko_mode = "skip"

    def _get_ssh_key(self) -> str | None:
        app = self.app
        ctx = getattr(app, "context", None)
        cfg = ctx.config if ctx else DeployConfig()
        svc = DeployService(cfg)
        return svc._resolve_ssh_key()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        addr_input = self.query_one("#addr-input", Input)
        self.state.ssh_target = addr_input.value or self.state.host_name
        self.state.ssh_key = self._get_ssh_key()
        extra_input = self.query_one("#extra-args-input", Input)
        self.state.extra_args = extra_input.value or None
        mode_select = self.query_one("#mode-select", RadioSet)
        pressed_id = mode_select.pressed_button.id if mode_select.pressed_button else "mode-auto"
        mode_map = {
            "mode-auto": "auto",
            "mode-mount": "mount",
            "mode-create": "create",
            "mode-skip": "skip",
        }
        self.state.disko_mode = mode_map.get(pressed_id, "auto")

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
        app = self.app
        ctx = getattr(app, "context", None)
        cfg = ctx.config if ctx else DeployConfig()
        missing: list[str] = []
        try:
            if self.state.disko_mode in ("mount", "auto"):
                svc = DeployService(cfg)
                self.call_from_thread(self._set_status, "Evaluating disko config...")
                try:
                    devices = svc._eval_disko_devices(self.state.host_name)
                except Exception:
                    self.call_from_thread(
                        self._set_status, "No disko devices found — skipping validation"
                    )
                    self.call_from_thread(self._go_to_deploy)
                    return

                ssh = SshClient(self.state.ssh_target, self.state.ssh_key)
                expected: list[str] = []
                for disk_name, disk in devices.get("disk", {}).items():
                    partitions = (
                        disk.get("content", {}).get("partitions", []) or []
                    )
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
                        self._set_status,
                        f"{len(missing)} partition(s) missing",
                    )
                else:
                    self.call_from_thread(
                        self._set_status,
                        f"All {len(expected)} partitions found",
                    )
        except Exception as exc:
            self.call_from_thread(self._validation_error, str(exc))
            return

        self.state.missing_partlabels = missing
        if missing:
            self.call_from_thread(self._push_partitions)
        else:
            self.call_from_thread(self._go_to_deploy)

    def _push_partitions(self) -> None:
        self.app.push_screen(WizardPartitionScreen(self.state))

    def _validation_error(self, msg: str) -> None:
        self.query_one("#status", Static).update(f"Validation error: {msg}")
        self.query_one("#validate-deploy", Button).disabled = False
        self.query_one("#deploy-skip", Button).disabled = False

    def _go_to_deploy(self) -> None:
        from nixos_deploy_tool.textual_ui.screens.wizard_deploy import WizardDeployScreen
        self.app.push_screen(WizardDeployScreen(self.state))
