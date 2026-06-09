from __future__ import annotations

import json
import os
import shlex
from collections.abc import Callable
from pathlib import Path

from collections.abc import Callable

from nixos_deploy_tool.core._base import SubprocessRunner
from nixos_deploy_tool.core.flake import FlakeIntrospector
from nixos_deploy_tool.core.key_store import KeyStore
from nixos_deploy_tool.core.nix import NixRunner
from nixos_deploy_tool.core.nixos_anywhere import NixosAnywhere
from nixos_deploy_tool.core.ssh import SshClient
from nixos_deploy_tool.exceptions import NixEvalError
from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.models.result import BaseResult, ErrorResult, SuccessResult
from nixos_deploy_tool.services.base import BaseService


class DeployService(BaseService):
    def __init__(
        self,
        config: DeployConfig,
        nixos_anywhere: NixosAnywhere | None = None,
        flake: FlakeIntrospector | None = None,
        nix_runner: NixRunner | None = None,
        key_store: KeyStore | None = None,
        ssh_factory: Callable[[str, str | None], SubprocessRunner] | None = None,
    ) -> None:
        super().__init__(config)
        if not config.flake_root:
            raise RuntimeError("DeployConfig.flake_root must be set")
        flake_root = Path(config.flake_root)
        self._flake_root = flake_root
        self._nixos_anywhere = nixos_anywhere or NixosAnywhere(
            binary=config.paths.nixos_anywhere_bin or "nixos-anywhere",
        )
        self._flake = flake or FlakeIntrospector(flake_root)
        self._nix = nix_runner or NixRunner()
        self._key_store = key_store or KeyStore()
        self._ssh_factory = ssh_factory or (lambda target, key: SshClient(target, key))

    # ── Public API ──────────────────────────────────────────────────

    def create_ssh(self, target: str, ssh_key: str | None = None) -> SubprocessRunner:
        return self._ssh_factory(target, ssh_key)

    def list_hosts(self) -> list[dict[str, str]]:
        """List available host configurations from the flake."""
        return self._flake.list_host_configs()

    def get_disko_devices(self, host_name: str) -> dict:
        """Evaluate and return the disko devices config for a host."""
        raw = self._nix.eval_flake_json(
            f'nixosConfigurations."{host_name}".config.disko.devices',
            self._flake_root,
        )
        return json.loads(raw)

    def get_disko_summary(self, host_name: str) -> str:
        """Return a human-readable summary of the disko config."""
        try:
            devices = self.get_disko_devices(host_name)
            count = len(devices.get("disk", {}))
            return f"Disko devices: {count} disk(s) configured"
        except (NixEvalError, json.JSONDecodeError):
            return "No disko devices found — partitions may be configured manually"

    def resolve_host_attr(self, host: str) -> str:
        """Resolve a host name to its flake attribute path."""
        hosts = self._flake.list_host_configs()
        for h in hosts:
            if h["name"] == host:
                return h["attr"]
        return host

    def resolve_ssh_key(self) -> str | None:
        """Resolve SSH identity key path from config or defaults."""
        cfg_key = self.config.ssh_key_path
        if cfg_key:
            p = Path(cfg_key).expanduser()
            if p.exists():
                return str(p)
            self.logger.warning(
                "Configured ssh_key_path '%s' not found, trying defaults", cfg_key
            )

        sudo_user = os.environ.get("SUDO_USER")
        candidates = ["~/.ssh/id_ed25519", "~/.ssh/id_rsa", "~/.ssh/id_ecdsa"]
        if sudo_user:
            candidates = [
                f"~{sudo_user}/.ssh/id_ed25519",
                f"~{sudo_user}/.ssh/id_rsa",
                f"~{sudo_user}/.ssh/id_ecdsa",
            ] + candidates

        for candidate in candidates:
            p = Path(candidate).expanduser()
            if p.exists():
                self.logger.info("Using SSH identity key: %s", p)
                return str(p)

        self.logger.warning(
            "No SSH identity key found — password prompt will be required for live ISO auth"
        )
        return None

    def resolve_extra_files(self, host: str) -> Path | None:
        """Return extra-files directory path if a host keypair exists."""
        if self._key_store.exists(host):
            self.logger.info("Using stored host keypair for '%s'", host)
            return self._key_store.extra_files_dir(host)
        self.logger.info("No stored keypair found for '%s', host key will be random", host)
        return None

    def build_extra_args(
        self,
        host_name: str,
        cli_extra_args: str | None,
        disko_mode: str = "auto",
    ) -> list[str]:
        """Build the extra_args list for nixos-anywhere, respecting config flags.

        The disko_mode parameter (auto / mount / create / skip) determines
        which --disko-mode or --phases flag is appended.
        """
        args: list[str] = list(self.config.default_extra_args)

        if self.config.skip_disko or self.config.disko_mode or self.config.auto_detect_disko:
            for flag in ("--phases", "--disko-mode"):
                if flag in args:
                    self.logger.warning(
                        "default_extra_args contains %s which will be overridden by "
                        "skip_disko/disko_mode/auto_detect_disko settings",
                        flag,
                    )

        if self.config.skip_disko:
            if self.config.disko_mode:
                self.logger.debug(
                    "skip_disko=true overrides disko_mode=%s", self.config.disko_mode
                )
            if self.config.auto_detect_disko:
                self.logger.debug("skip_disko=true overrides auto_detect_disko=true")
            args.extend(["--phases", "kexec,install,reboot"])

        elif self.config.disko_mode:
            if self.config.auto_detect_disko:
                self.logger.debug(
                    "disko_mode=%s overrides auto_detect_disko=true",
                    self.config.disko_mode,
                )
            args.extend(["--disko-mode", self.config.disko_mode])

        elif self.config.auto_detect_disko:
            try:
                self._nix.eval_flake_json(
                    f'nixosConfigurations."{host_name}".config.system.build.diskoScript',
                    self._flake_root,
                )
                self.logger.debug("diskoScript found — disko phase will run")
            except NixEvalError:
                self.logger.info("diskoScript not found — skipping disko phase")
                args.extend(["--phases", "kexec,install,reboot"])

        if cli_extra_args:
            cli_flags = shlex.split(cli_extra_args)
            if self.config.skip_disko and "--disko-mode" in cli_flags:
                self.logger.warning(
                    "skip_disko=true but --extra-args contains --disko-mode; "
                    "last flag wins for nixos-anywhere"
                )
            if self.config.disko_mode and "--phases" in cli_flags:
                self.logger.warning(
                    "disko_mode=%s but --extra-args contains --phases; "
                    "last flag wins for nixos-anywhere",
                    self.config.disko_mode,
                )
            args.extend(cli_flags)

        if args:
            self.logger.info("nixos-anywhere extra args: %s", " ".join(args))

        return args

    def validate_mount_partitions(
        self,
        host_name: str,
        target: str,
        ssh_key: str | None = None,
    ) -> list[str]:
        """Check which expected disko partitions are missing on the target."""
        try:
            devices = self.get_disko_devices(host_name)
        except (NixEvalError, json.JSONDecodeError):
            self.logger.warning(
                "Cannot evaluate disko devices config for '%s' — skipping partition validation",
                host_name,
            )
            return []
        ssh = SshClient(target, ssh_key)
        expected: list[str] = []
        for disk_name, disk in devices.get("disk", {}).items():
            partitions = disk.get("content", {}).get("partitions", []) or []
            for part in partitions:
                part_name = part.get("name", "")
                if part_name:
                    expected.append(f"disk-{disk_name}-{part_name}")
        if not expected:
            self.logger.info("No expected partitions found in disko config for '%s'", host_name)
            return []
        missing: list[str] = []
        for label in expected:
            if not ssh.partition_exists(label):
                missing.append(label)
        if missing:
            self.logger.warning(
                "Missing partitions on '%s': %s", target, ", ".join(missing)
            )
        else:
            self.logger.info(
                "All %d expected partitions found on '%s'", len(expected), target
            )
        return missing

    def run_streaming(
        self,
        host: str,
        addr: str | None = None,
        extra_args: str | None = None,
        *,
        on_output: Callable[[str], None] | None = None,
        on_done: Callable[[BaseResult], None] | None = None,
    ) -> BaseResult:
        """Deploy with streaming output. Calls on_output(line) per line
        and on_done(result) when finished.  Returns the final result."""
        try:
            target = addr or host
            attr = self.resolve_host_attr(host)
            self._nixos_anywhere.deploy(
                target=target,
                flake_attr=attr,
                flake_root=self._flake_root,
                ssh_key=self.resolve_ssh_key(),
                extra_files=self.resolve_extra_files(host),
                extra_args=self.build_extra_args(host, extra_args),
                on_output=on_output,
            )
            result: BaseResult = SuccessResult(message=f"Deployed {host}.")
        except Exception as exc:
            result = ErrorResult(message=f"Deploy failed: {exc}")
        if on_done:
            on_done(result)
        return result

    # ── High-level operations ──────────────────────────────────────

    def run(self, host: str, addr: str | None = None, extra_args: str | None = None) -> BaseResult:
        self.logger.info("Deploying to %s (addr=%s)", host, addr or "auto")
        try:
            target = addr or host
            attr = self.resolve_host_attr(host)
            self._nixos_anywhere.deploy(
                target=target,
                flake_attr=attr,
                flake_root=self._flake_root,
                extra_args=self.build_extra_args(host, extra_args),
                extra_files=self.resolve_extra_files(host),
            )
            return SuccessResult(message=f"Deployed {host}.")
        except Exception as exc:
            return ErrorResult(message=f"Deploy failed: {exc}")

    def wizard(self, host: str, addr: str | None = None, extra_args: str | None = None) -> BaseResult:
        self.logger.info("Running deploy wizard for %s (addr=%s)", host, addr or "auto")
        try:
            target = addr or host
            attr = self.resolve_host_attr(host)
            self._nixos_anywhere.deploy(
                target=target,
                flake_attr=attr,
                flake_root=self._flake_root,
                extra_args=self.build_extra_args(host, extra_args),
            )
            return SuccessResult(message=f"Wizard completed for {host}.")
        except Exception as exc:
            return ErrorResult(message=f"Wizard failed: {exc}")

    def with_keys(self, host: str, addr: str | None = None, extra_args: str | None = None) -> BaseResult:
        self.logger.info("Deploying with keys to %s (addr=%s)", host, addr or "auto")
        try:
            attr = self.resolve_host_attr(host)
            target = addr or host
            ssh_key = self.resolve_ssh_key()
            self._nixos_anywhere.deploy(
                target=target,
                flake_attr=attr,
                flake_root=self._flake_root,
                ssh_key=ssh_key,
                extra_args=self.build_extra_args(host, extra_args),
                extra_files=self.resolve_extra_files(host),
            )
            return SuccessResult(message=f"Deployed {host} with keys.")
        except Exception as exc:
            return ErrorResult(message=f"Deploy with keys failed: {exc}")

    def test(self, host: str) -> BaseResult:
        self.logger.info("VM-testing host config: %s", host)
        try:
            attr = self.resolve_host_attr(host)
            self._nix.build(attr=attr, flake_root=self._flake_root)
            return SuccessResult(message=f"Test passed for {host}.")
        except Exception as exc:
            return ErrorResult(message=f"Test failed: {exc}")
