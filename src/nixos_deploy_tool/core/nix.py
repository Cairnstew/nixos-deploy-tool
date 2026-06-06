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
        return subprocess.run(cmd, text=True, check=True)

    def eval_json(self, expr: str, flake_root: Path | None = None) -> str:
        cmd = ["nix", "eval", "--json", "--expr", expr]
        if flake_root:
            cmd.extend(["--option", "flake", str(flake_root)])
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
