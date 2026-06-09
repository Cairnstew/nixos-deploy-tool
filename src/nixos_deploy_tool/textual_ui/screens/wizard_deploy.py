from __future__ import annotations

import subprocess
import threading
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, RichLog, Static

from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.services.deploy import DeployService
from nixos_deploy_tool.textual_ui.wizard_state import WizardState


class WizardDeployScreen(Screen[None]):
    CSS_PATH = "../styles/wizard.tcss"
    state: WizardState
    _log: RichLog

    def __init__(self, state: WizardState) -> None:
        super().__init__()
        self.state = state
        self._deploy_done = threading.Event()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Label(f"Deploying {self.state.host_name}...", id="deploy-title"),
            RichLog(id="deploy-log", highlight=True, max_lines=200),
            Static("", id="deploy-status"),
            Button("Back to Dashboard", id="back", variant="primary", disabled=True),
        )
        yield Footer()

    def on_mount(self) -> None:
        self._log = self.query_one("#deploy-log", RichLog)
        self._run_deploy()

    def _run_deploy(self) -> None:
        thread = threading.Thread(target=self._deploy_thread, daemon=True)
        thread.start()

    def _deploy_thread(self) -> None:
        app = self.app
        ctx = getattr(app, "context", None)
        cfg = ctx.config if ctx else DeployConfig()
        svc = DeployService(cfg)

        flake_root = Path(cfg.flake_root) if cfg.flake_root else Path.cwd()
        attr = svc._resolve_host_attr(self.state.host_name)
        extra_args = self._build_extra_args(svc)

        cmd = ["nixos-anywhere", "--flake", f"{flake_root}#{attr}", self.state.ssh_target]
        if self.state.ssh_key:
            cmd.extend(["-i", self.state.ssh_key])
        if extra_args:
            cmd.extend(extra_args)

        self._log.write(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            for line in result.stdout.splitlines():
                self.call_from_thread(self._log.write, line)
            if result.returncode == 0:
                self.call_from_thread(self._on_success)
            else:
                self.call_from_thread(
                    self._on_failure, f"Deploy failed (exit {result.returncode})"
                )
        except Exception as exc:
            self.call_from_thread(self._on_failure, str(exc))
        finally:
            self._deploy_done.set()

    def _build_extra_args(self, svc: DeployService) -> list[str]:
        ctx = getattr(self.app, "context", None)
        cfg = ctx.config if ctx else DeployConfig()
        args = list(cfg.default_extra_args)
        if self.state.disko_mode == "mount":
            args.extend(["--disko-mode", "mount"])
        elif self.state.disko_mode == "skip":
            args.extend(["--phases", "kexec,install,reboot"])
        if self.state.extra_args:
            import shlex
            args.extend(shlex.split(self.state.extra_args))
        return args

    def _on_success(self) -> None:
        self.query_one("#deploy-status", Static).update("Deploy successful!")
        self.query_one("#back", Button).disabled = False

    def _on_failure(self, msg: str) -> None:
        self.query_one("#deploy-status", Static).update(msg)
        self.query_one("#back", Button).disabled = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            app = self.app
            while app.screen_stack:
                app.pop_screen()
