from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from nixos_deploy_tool.exceptions import ISOBuildError


class ISOBuilder:
    def __init__(self, nix_bin: str = "nix") -> None:
        self._nix_bin = nix_bin
        self._logger = logging.getLogger(self.__class__.__name__)

    def build(
        self,
        flake_root: Path,
        iso_attr: str,
        extra_nixos_module: str | None = None,
    ) -> Path:
        cmd = [
            self._nix_bin,
            "build",
            f"{flake_root}#{iso_attr}",
            "--print-out-paths",
            "--no-link",
        ]
        if extra_nixos_module:
            cmd.extend(["--extra-nixos-module", extra_nixos_module])
        self._logger.info("Running: %s", " ".join(cmd))
        result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
        if result.returncode != 0:
            msg = f"ISO build failed: `{' '.join(cmd)}` (exit {result.returncode})"
            raise ISOBuildError(msg)
        return Path(result.stdout.strip())
