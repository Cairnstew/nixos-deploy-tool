from __future__ import annotations

from pathlib import Path
from typing import Any

from nixos_deploy_tool.core._base import SubprocessRunner
from nixos_deploy_tool.exceptions import NixEvalError, SubprocessError


class NixRunner(SubprocessRunner):
    def __init__(self) -> None:
        super().__init__("nix")

    def _wrap_error(self, exc: subprocess.CalledProcessError) -> Exception:  # type: ignore[name-defined]
        import subprocess

        return SubprocessError(
            f"nix command failed (exit {exc.returncode}): {exc.stderr.strip()}"
        )

    def build(
        self, attr: str, flake_root: Path, **kwargs: str
    ) -> subprocess.CompletedProcess[str]:  # type: ignore[name-defined]
        import subprocess

        args = ["build", f"{flake_root}#{attr}"]
        for key, val in kwargs.items():
            args.extend([f"--{key.replace('_', '-')}", val])
        self.logger.info("Running: nix %s", " ".join(args[1:]))
        cmd = [self.binary, *args]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, timeout=300)
        if result.returncode != 0:
            raise SubprocessError(
                f"`{' '.join(cmd)}` failed (exit {result.returncode})"
            )
        return result

    def eval_json(self, expr: str, flake_root: Path | None = None) -> str:
        args = ["eval", "--json", "--expr", expr]
        if flake_root:
            args.extend(["--option", "flake", str(flake_root)])
        return self._run(args, timeout=120)

    def eval_flake_json(self, attr: str, flake_root: Path) -> str:
        exp = self._build_strip_expr(attr, flake_root)
        args = ["eval", "--json", "--impure", "--expr", exp]
        try:
            return self._run(args, timeout=120)
        except SubprocessError as exc:
            raise NixEvalError(str(exc)) from exc

    @staticmethod
    def _build_strip_expr(attr: str, flake_root: Path) -> str:
        """Build a Nix expression that evaluates *attr* on *flake_root*,
        stripping internal (underscore-prefixed) attributes that cannot
        be serialised to JSON (e.g. disko's ``_packages``, ``_scripts``).
        """
        return f'''
let
  fl = builtins.getFlake "{flake_root}";
  stripInternal = v:
    if builtins.isAttrs v then
      let
        names = builtins.attrNames v;
        kv = map (n: {{ name = n; value = stripInternal v.${{n}}; }}) names;
        safe = builtins.filter (x: builtins.substring 0 1 x.name != "_") kv;
      in
        builtins.listToAttrs safe
    else if builtins.isList v then map stripInternal v
    else v;
in
  stripInternal (fl.{attr})
'''
