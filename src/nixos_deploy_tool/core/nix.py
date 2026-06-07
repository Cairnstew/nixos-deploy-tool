from __future__ import annotations

import logging
import subprocess
from pathlib import Path


class NixRunner:
    def __init__(self) -> None:
        self._logger = logging.getLogger(self.__class__.__name__)

    def build(self, attr: str, flake_root: Path, **kwargs: str) -> subprocess.CompletedProcess[str]:
        cmd = ["nix", "build", f"{flake_root}#{attr}"]
        for key, val in kwargs.items():
            cmd.extend([f"--{key.replace('_', '-')}", val])
        self._logger.info("Running: %s", " ".join(cmd))
        result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"`{' '.join(cmd)}` failed (exit {result.returncode})"
            )
        return result

    def eval_json(self, expr: str, flake_root: Path | None = None) -> str:
        cmd = ["nix", "eval", "--json", "--expr", expr]
        if flake_root:
            cmd.extend(["--option", "flake", str(flake_root)])
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"`{' '.join(cmd)}` failed (exit {result.returncode}):\n{result.stderr}"
            )
        return result.stdout.strip()
