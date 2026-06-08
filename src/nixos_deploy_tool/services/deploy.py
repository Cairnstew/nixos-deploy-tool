from __future__ import annotations

import os
import shlex
from pathlib import Path

from nixos_deploy_tool.core.flake import FlakeIntrospector
from nixos_deploy_tool.core.key_store import KeyStore
from nixos_deploy_tool.core.nix import NixRunner
from nixos_deploy_tool.core.nixos_anywhere import NixosAnywhere
from nixos_deploy_tool.exceptions import NixEvalError
from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.models.result import BaseResult, ErrorResult, SuccessResult
from nixos_deploy_tool.services.base import BaseService


class DeployService(BaseService):
    def __init__(self, config: DeployConfig) -> None:
        super().__init__(config)
        flake_root = Path(config.flake_root) if config.flake_root else Path.cwd()
        self._flake_root = flake_root
        self._nixos_anywhere = NixosAnywhere(
            binary=config.paths.nixos_anywhere_bin or "nixos-anywhere",
        )
        self._flake = FlakeIntrospector(flake_root)
        self._nix = NixRunner()

    def _resolve_host_attr(self, host: str) -> str:
        hosts = self._flake.list_host_configs()
        for h in hosts:
            if h["name"] == host:
                return h["attr"]
        return host

    def _resolve_ssh_key(self) -> str | None:
        cfg_key = self.config.ssh_key_path
        if cfg_key:
            p = Path(cfg_key).expanduser()
            if p.exists():
                return str(p)
            self.logger.warning("Configured ssh_key_path '%s' not found, trying defaults", cfg_key)

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

        self.logger.warning("No SSH identity key found — password prompt will be required for live ISO auth")
        return None

    def _resolve_extra_files(self, host: str) -> Path | None:
        keystore = KeyStore()
        if keystore.exists(host):
            self.logger.info("Using stored host keypair for '%s'", host)
            return keystore.extra_files_dir(host)
        self.logger.info("No stored keypair found for '%s', host key will be random", host)
        return None

    def _build_extra_args(
        self,
        host_name: str,
        cli_extra_args: str | None,
        flake_root: Path,
    ) -> list[str]:
        args: list[str] = list(self.config.default_extra_args)

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
                    flake_root,
                )
                self.logger.debug("diskoScript found — disko phase will run")
            except NixEvalError:
                self.logger.info("diskoScript not found — skipping disko phase")
                args.extend(["--phases", "kexec,install,reboot"])

        if cli_extra_args:
            args.extend(shlex.split(cli_extra_args))

        return args

    def run(self, host: str, addr: str | None = None, extra_args: str | None = None) -> BaseResult:
        self.logger.info("Deploying to %s (addr=%s)", host, addr or "auto")
        try:
            target = addr or host
            attr = self._resolve_host_attr(host)
            self._nixos_anywhere.deploy(
                target=target,
                flake_attr=attr,
                flake_root=self._flake_root,
                extra_args=self._build_extra_args(host, extra_args, self._flake_root),
                extra_files=self._resolve_extra_files(host),
            )
            return SuccessResult(message=f"Deployed {host}.")
        except Exception as exc:
            return ErrorResult(message=f"Deploy failed: {exc}")

    def wizard(self, host: str, addr: str | None = None, extra_args: str | None = None) -> BaseResult:
        self.logger.info("Running deploy wizard for %s (addr=%s)", host, addr or "auto")
        try:
            target = addr or host
            attr = self._resolve_host_attr(host)
            self._nixos_anywhere.deploy(
                target=target,
                flake_attr=attr,
                flake_root=self._flake_root,
                extra_args=self._build_extra_args(host, extra_args, self._flake_root),
            )
            return SuccessResult(message=f"Wizard completed for {host}.")
        except Exception as exc:
            return ErrorResult(message=f"Wizard failed: {exc}")

    def with_keys(self, host: str, addr: str | None = None, extra_args: str | None = None) -> BaseResult:
        self.logger.info("Deploying with keys to %s (addr=%s)", host, addr or "auto")
        try:
            attr = self._resolve_host_attr(host)
            target = addr or host
            ssh_key = self._resolve_ssh_key()
            self._nixos_anywhere.deploy(
                target=target,
                flake_attr=attr,
                flake_root=self._flake_root,
                ssh_key=ssh_key,
                extra_args=self._build_extra_args(host, extra_args, self._flake_root),
                extra_files=self._resolve_extra_files(host),
            )
            return SuccessResult(message=f"Deployed {host} with keys.")
        except Exception as exc:
            return ErrorResult(message=f"Deploy with keys failed: {exc}")

    def test(self, host: str) -> BaseResult:
        self.logger.info("VM-testing host config: %s", host)
        try:
            attr = self._resolve_host_attr(host)
            self._nix.build(attr=attr, flake_root=self._flake_root)
            return SuccessResult(message=f"Test passed for {host}.")
        except Exception as exc:
            return ErrorResult(message=f"Test failed: {exc}")
