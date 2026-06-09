from __future__ import annotations

import json
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, RadioSet, RadioButton, Static

from nixos_deploy_tool.exceptions import NixEvalError
from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.services.deploy import DeployService
from nixos_deploy_tool.textual_ui.screens.wizard_deploy import WizardDeployScreen
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
        app = self.app
        ctx = getattr(app, "context", None)
        cfg = ctx.config if ctx else DeployConfig()
        if self.state.disko_mode in ("mount", "auto"):
            svc = DeployService(cfg)
            missing = svc.validate_mount_partitions(
                self.state.host_name,
                self.state.ssh_target,
                self.state.ssh_key,
            )
            self.state.missing_partlabels = missing
            if missing:
                self.app.push_screen("wizard_partitions", self.state)
                return
        self._go_to_deploy()

    def _go_to_deploy(self) -> None:
        self.app.push_screen("wizard_deploy", self.state)
