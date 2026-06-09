from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from nixos_deploy_tool.core._base import SubprocessRunner
from nixos_deploy_tool.exceptions import DeployRuntimeError


class NixosAnywhere(SubprocessRunner):
    def __init__(self, binary: str = "nixos-anywhere") -> None:
        super().__init__(binary)

    def _wrap_error(self, exc: subprocess.CalledProcessError) -> Exception:
        return DeployRuntimeError(
            f"nixos-anywhere failed (exit {exc.returncode}): {exc.stderr.strip()}"
        )

    @staticmethod
    def _extract_host(target: str) -> str:
        if "@" in target:
            return target.rsplit("@", 1)[1]
        return target

    def _clear_known_hosts(self, target: str) -> None:
        host = self._extract_host(target)
        self.logger.info("Removing stale known_hosts entry for '%s'", host)
        subprocess.run(
            ["ssh-keygen", "-R", host],
            capture_output=True,
            text=True,
        )

    def _build_args(
        self,
        target: str,
        flake_attr: str,
        flake_root: Path,
        ssh_key: str | None = None,
        extra_args: Sequence[str] | None = None,
        extra_files: Path | None = None,
    ) -> list[str]:
        args = ["--flake", f"{flake_root}#{flake_attr}", target]
        if ssh_key:
            args.extend(["-i", ssh_key])
        if extra_files:
            args.extend(["--extra-files", str(extra_files)])
        if extra_args:
            args.extend(extra_args)
        return args

    def deploy(
        self,
        target: str,
        flake_attr: str,
        flake_root: Path,
        ssh_key: str | None = None,
        extra_args: Sequence[str] | None = None,
        extra_files: Path | None = None,
        on_output: Callable[[str], None] | None = None,
        on_done: Callable[[int], None] | None = None,
    ) -> subprocess.CompletedProcess[str] | int:
        self._clear_known_hosts(target)

        args = self._build_args(target, flake_attr, flake_root, ssh_key, extra_args, extra_files)

        if on_output or on_done:
            return self._run_streaming(args, on_output=on_output, on_done=on_done)

        try:
            stdout = self._run(args)
            return subprocess.CompletedProcess(
                args=[self.binary, *args],
                returncode=0,
                stdout=stdout.encode() if stdout else b"",
                stderr=b"",
            )
        except DeployRuntimeError:
            raise
