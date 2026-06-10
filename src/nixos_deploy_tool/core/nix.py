from __future__ import annotations

import subprocess
from pathlib import Path

from nixos_deploy_tool.core.nix_tool import NixTool
from nixos_deploy_tool.exceptions import NixEvalError, SubprocessError

_STRIP_EXPR_TEMPLATE = (
    "let\n"
    '  fl = builtins.getFlake "{}";\n'
    "  stripInternal = v:\n"
    "    if builtins.isAttrs v then\n"
    "      let\n"
    "        names = builtins.attrNames v;\n"
    '        kv = map (n: {{ name = n; value = stripInternal v.${{n}}; }}) names;\n'
    '        safe = builtins.filter (x: builtins.substring 0 1 x.name != "_") kv;\n'
    "      in\n"
    "        builtins.listToAttrs safe\n"
    "    else if builtins.isList v then map stripInternal v\n"
    "    else v;\n"
    "in\n"
    "  stripInternal (fl.{})\n"
)


class NixRunner(NixTool):
    def __init__(self) -> None:
        super().__init__("nix")

    def _wrap_error(self, exc: subprocess.CalledProcessError) -> Exception:
        return SubprocessError(f"nix command failed (exit {exc.returncode}): {exc.stderr.strip()}")

    def build(self, attr: str, flake_root: Path) -> str:
        return self._run_cmd(
            "build",
            flake=f"{flake_root}#{attr}",
            print_out_paths=True,
            no_link=True,
        )

    def eval_json(self, expr: str, flake_root: Path | None = None) -> str:
        args = self._build_command("eval", json=True, expr=expr)
        if flake_root:
            args.extend(["--option", "flake", str(flake_root)])
        return self._run(args[1:], timeout=120)

    def eval_flake_json(self, attr: str, flake_root: Path) -> str:
        exp = self._build_strip_expr(attr, flake_root)
        args = self._build_command(
            "eval",
            json=True,
            impure=True,
            expr=exp,
        )
        try:
            return self._run(args[1:], timeout=120)
        except SubprocessError as exc:
            raise NixEvalError(str(exc)) from exc

    @staticmethod
    def _build_strip_expr(attr: str, flake_root: Path) -> str:
        return _STRIP_EXPR_TEMPLATE.format(flake_root, attr)
