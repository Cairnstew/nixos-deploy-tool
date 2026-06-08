from __future__ import annotations

import logging
import subprocess
from collections.abc import Sequence
from pathlib import Path


class NixosAnywhere:
    def __init__(self, binary: str = "nixos-anywhere") -> None:
        self._binary = binary
        self._logger = logging.getLogger(self.__class__.__name__)

    def deploy(
        self,
        target: str,
        flake_attr: str,
        flake_root: Path,
        ssh_key: str | None = None,
        extra_args: Sequence[str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        cmd = [
            self._binary,
            "--flake",
            f"{flake_root}#{flake_attr}",
            target,
        ]
        if ssh_key:
            cmd.extend(["-i", ssh_key])
        if extra_args:
            cmd.extend(extra_args)
        self._logger.info("Running: %s", " ".join(cmd))
        result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"`{' '.join(cmd)}` failed (exit {result.returncode})"
            )
        return result
