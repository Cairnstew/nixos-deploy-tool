from __future__ import annotations

from pathlib import Path

from nixos_deploy_tool.core._base import SubprocessRunner
from nixos_deploy_tool.exceptions import ISOBuildError, SubprocessError


class ISOBuilder(SubprocessRunner):
    def __init__(self, nix_bin: str = "nix") -> None:
        super().__init__(nix_bin)

    def _wrap_error(self, exc: subprocess.CalledProcessError) -> Exception:  # type: ignore[name-defined]
        import subprocess

        return ISOBuildError(
            f"ISO build failed (exit {exc.returncode}): {exc.stderr.strip()}"
        )

    def build(
        self,
        flake_root: Path,
        iso_attr: str,
        extra_nixos_module: str | None = None,
    ) -> Path:
        args = [
            "build",
            f"{flake_root}#{iso_attr}",
            "--print-out-paths",
            "--no-link",
        ]
        if extra_nixos_module:
            args.extend(["--extra-nixos-module", extra_nixos_module])
        stdout = self._run(args)
        return Path(stdout)
