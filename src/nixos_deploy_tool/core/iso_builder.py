from __future__ import annotations

import subprocess
from pathlib import Path

from nixos_deploy_tool.core.nix_tool import NixTool
from nixos_deploy_tool.exceptions import ISOBuildError


class ISOBuilder(NixTool):
    def __init__(self, nix_bin: str = "nix") -> None:
        super().__init__(nix_bin)

    def _wrap_error(self, exc: subprocess.CalledProcessError) -> Exception:
        return ISOBuildError(
            f"ISO build failed (exit {exc.returncode}): {exc.stderr.strip()}"
        )

    def build(
        self,
        flake_root: Path,
        iso_attr: str,
        extra_nixos_module: str | None = None,
    ) -> Path:
        stdout = self._run_cmd(
            "build",
            flake=f"{flake_root}#{iso_attr}",
            print_out_paths=True,
            no_link=True,
            extra_nixos_module=extra_nixos_module,
        )
        return self._resolve_store_path(stdout)
