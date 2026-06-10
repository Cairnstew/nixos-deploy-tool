from __future__ import annotations

import json
import os
import shlex
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from nixos_deploy_tool.core.flake import FlakeIntrospector
from nixos_deploy_tool.core.key_store import KeyStore
from nixos_deploy_tool.core.nix import NixRunner
from nixos_deploy_tool.core.nixos_anywhere import NixosAnywhere
from nixos_deploy_tool.core.ssh import SshClient, SshProtocol
from nixos_deploy_tool.exceptions import NixEvalError

from nixos_deploy_tool.models.config import DeployConfig, normalise_partitions
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
        ssh_factory: Callable[[str, str | None], SshProtocol] | None = None,
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

    def on_start(self) -> None:
        pass

    def on_stop(self) -> None:
        pass

    # ── Public API ──────────────────────────────────────────────────

    def create_ssh(self, target: str, ssh_key: str | None = None) -> SshProtocol:
        return self._ssh_factory(target, ssh_key)

    def list_hosts(self) -> list[dict[str, str]]:
        """List available host configurations from the flake."""
        return self._flake.list_host_configs()

    def get_disko_devices(self, host_name: str) -> dict[str, Any]:
        """Evaluate and return the disko devices config for a host."""
        raw = self._nix.eval_flake_json(
            f'nixosConfigurations."{host_name}".config.disko.devices',
            self._flake_root,
        )
        return cast("dict[str, Any]", json.loads(raw))

    @staticmethod
    def _parse_partition_names(disk_content: dict[str, Any]) -> list[str]:
        """Extract partition names from a disko content block."""
        return [p.get("name", "") for p in normalise_partitions(disk_content) if p.get("name")]

    def get_disko_summary(self, host_name: str) -> str:
        """Return a human-readable summary of the disko config."""
        try:
            devices = self.get_disko_devices(host_name)
            disk_dict = devices.get("disk", {})
            if not disk_dict:
                return "No disko devices found — partitions may be configured manually"
            lines: list[str] = []
            for name, disk in disk_dict.items():
                device = disk.get("device", "?")
                content = disk.get("content", {})
                part_names = self._parse_partition_names(content)
                if part_names:
                    lines.append(f"  {device} ({name})  →  {', '.join(part_names)}")
                else:
                    lines.append(f"  {device} ({name})")
            if len(lines) == 1:
                return f"Disk: {lines[0].strip()}"
            return "Disks:\n" + "\n".join(lines)
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
        disk_overrides: dict[str, str] | None = None,
    ) -> list[str]:
        """Build the extra_args list for nixos-anywhere.

        When *disko_mode* is explicitly set (not ``"auto"``), it takes
        precedence over all config-file fields (``skip_disko``,
        ``disko_mode``, ``auto_detect_disko``).  Use ``"auto"`` (the
        default) to fall back to the config file.
        """
        args: list[str] = list(self.config.default_extra_args)

        explicit = disko_mode != "auto"

        if not explicit:
            has_config_override = (
                self.config.skip_disko or self.config.disko_mode or self.config.auto_detect_disko
            )
            if has_config_override:
                for flag in ("--phases", "--disko-mode"):
                    if flag in args:
                        self.logger.warning(
                            "default_extra_args contains %s which will be overridden by "
                            "skip_disko/disko_mode/auto_detect_disko settings",
                            flag,
                        )

        # --- Resolve disko mode -------------------------------------------------
        if explicit:
            if disko_mode == "skip":
                args.extend(["--phases", "kexec,install,reboot"])
            else:
                args.extend(["--disko-mode", disko_mode])

        elif self.config.skip_disko or self.config.disko_mode:
            if self.config.skip_disko:
                args.extend(["--phases", "kexec,install,reboot"])
            else:
                dm = self.config.disko_mode or ""
                args.extend(["--disko-mode", dm])

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

        # --- Merge CLI extra-args -----------------------------------------------
        if cli_extra_args:
            cli_flags = shlex.split(cli_extra_args)
            if not explicit:
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

        # --- Disk device overrides (reserved for future nixos-anywhere support) --
        # nixos-anywhere currently reads the device from the disko config's `device`
        # attribute per disk.  No CLI flag exists to override it.
        # https://github.com/nix-community/nixos-anywhere/issues/...

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
        disko_mode: str = "auto",
        disk_overrides: dict[str, str] | None = None,
        *,
        on_output: Callable[[str], None] | None = None,
        on_done: Callable[[BaseResult], None] | None = None,
    ) -> BaseResult:
        """Deploy with streaming output. Calls on_output(line) per line
        and on_done(result) when finished.  Returns the final result.

        *disko_mode* is passed through to :meth:`build_extra_args` so the
        TUI radio selection is reflected in the nixos-anywhere flags.
        *disk_overrides* maps flake disk names to target device paths.
        """
        try:
            target = addr or host
            attr = self.resolve_host_attr(host)
            self._nixos_anywhere.deploy(
                target=target,
                flake_attr=attr,
                flake_root=self._flake_root,
                ssh_key=self.resolve_ssh_key(),
                extra_files=self.resolve_extra_files(host),
                extra_args=self.build_extra_args(host, extra_args, disko_mode=disko_mode,
                                                  disk_overrides=disk_overrides),
                on_output=on_output,
            )
            result: BaseResult = SuccessResult(message=f"Deployed {host}.")
        except Exception as exc:
            self.logger.error("Deploy failed: %s", exc, exc_info=True)
            result = ErrorResult(message=f"Deploy failed: {exc}")
        if on_done:
            on_done(result)
        return result

    # ── Partition preview for CLI ──────────────────────────────────

    def preview_partitions(
        self,
        host: str,
        target: str,
        ssh_key: str | None = None,
        disk_overrides: dict[str, str] | None = None,
    ) -> str:
        """Evaluate disko config, probe target disk, predict device paths.

        Returns a human-readable preview string (or empty if no partitions).
        Logs the preview at INFO level.
        """
        try:
            devices = self.get_disko_devices(host)
        except Exception:
            return ""
        overrides = disk_overrides or {}
        try:
            ssh = SshClient(target, ssh_key)
            lines: list[str] = []
            for disk_name, disk in devices.get("disk", {}).items():
                device = overrides.get(disk_name, disk.get("device", ""))
                if not device:
                    continue
                result = ssh.run(f"sgdisk --print {device}")
                existing: set[int] = set()
                for line in result.stdout.split("\n"):
                    stripped = line.strip()
                    if stripped and stripped.split()[0].isdigit():
                        existing.add(int(stripped.split()[0]))
                next_num = 1
                while next_num in existing:
                    next_num += 1
                for part in (disk.get("content", {}).get("partitions", []) or []):
                    part_name = part.get("name", "")
                    predicted = f"{device}p{next_num}" if device[-1].isdigit() else f"{device}{next_num}"
                    fstype = part.get("content", {}).get("format", "ext4")
                    lines.append(f"  {predicted}  →  {part_name} ({fstype})")
                    next_num += 1
            if lines:
                text = "Partitions to create:\n" + "\n".join(lines)
                self.logger.info("\n%s", text)
                return text
        except Exception:
            self.logger.warning("Could not probe target for partition preview", exc_info=True)
        return ""

    # ── High-level operations ──────────────────────────────────────

    def _deploy_nixos_anywhere(
        self,
        host: str,
        target: str,
        extra_args: list[str],
        ssh_key: str | None = None,
        extra_files: Path | None = None,
    ) -> None:
        attr = self.resolve_host_attr(host)
        self._nixos_anywhere.deploy(
            target=target,
            flake_attr=attr,
            flake_root=self._flake_root,
            ssh_key=ssh_key,
            extra_args=extra_args,
            extra_files=extra_files,
        )

    def _run_deploy_op(
        self,
        host: str,
        addr: str | None = None,
        extra_args: str | None = None,
        disk_overrides: dict[str, str] | None = None,
        disko_mode: str = "auto",
        *,
        ssh_key: str | None = None,
        log_label: str = "Deploy",
        success_msg: str | None = None,
    ) -> BaseResult:
        target = addr or host
        self.logger.info("%s to %s (addr=%s)", log_label, host, addr or "auto")
        try:
            self._deploy_nixos_anywhere(
                host=host,
                target=target,
                extra_args=self.build_extra_args(host, extra_args, disko_mode=disko_mode,
                                                  disk_overrides=disk_overrides),
                ssh_key=ssh_key or self.resolve_ssh_key(),
                extra_files=self.resolve_extra_files(host),
            )
            msg = success_msg or f"{log_label} completed for {host}."
            return SuccessResult(message=msg)
        except Exception as exc:
            return ErrorResult(message=f"{log_label} failed: {exc}")

    def run(
        self,
        host: str,
        addr: str | None = None,
        extra_args: str | None = None,
        disk_overrides: dict[str, str] | None = None,
        disko_mode: str = "auto",
    ) -> BaseResult:
        return self._run_deploy_op(
            host, addr=addr, extra_args=extra_args,
            disk_overrides=disk_overrides, disko_mode=disko_mode,
            ssh_key=None, log_label="Deploy",
        )

    def wizard(self, host: str, addr: str | None = None, extra_args: str | None = None) -> BaseResult:
        return self._run_deploy_op(
            host, addr=addr, extra_args=extra_args,
            ssh_key=None, log_label="Wizard",
            success_msg=f"Wizard completed for {host}.",
        )

    def with_keys(
        self,
        host: str,
        addr: str | None = None,
        extra_args: str | None = None,
        disk_overrides: dict[str, str] | None = None,
        disko_mode: str = "auto",
    ) -> BaseResult:
        return self._run_deploy_op(
            host, addr=addr, extra_args=extra_args,
            disk_overrides=disk_overrides, disko_mode=disko_mode,
            ssh_key=self.resolve_ssh_key(), log_label="Deploy with keys",
            success_msg=f"Deployed {host} with keys.",
        )

    def test(self, host: str) -> BaseResult:
        self.logger.info("VM-testing host config: %s", host)
        try:
            attr = self.resolve_host_attr(host)
            self._nix.build(attr=attr, flake_root=self._flake_root)
            return SuccessResult(message=f"Test passed for {host}.")
        except Exception as exc:
            return ErrorResult(message=f"Test failed: {exc}")
