from __future__ import annotations

from pathlib import Path

import typer

from nixos_deploy_tool.cli.commands import (
    deploy_app,
    iso_app,
    secrets_app,
    tailscale_app,
)
from nixos_deploy_tool.cli.context import AppContext
from nixos_deploy_tool.models.config import DeployConfig

app = typer.Typer(no_args_is_help=True)
app.add_typer(iso_app, name="iso")
app.add_typer(deploy_app, name="deploy")
app.add_typer(tailscale_app, name="tailscale")
app.add_typer(secrets_app, name="secrets")


def _default_flake_root() -> Path | None:
    cwd = Path.cwd()
    if (cwd / "flake.nix").exists():
        return cwd
    return None


@app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = False,
    flake_root: Path | None = None,
) -> None:
    ctx.ensure_object(dict)
    resolved_root = flake_root or _default_flake_root()
    config = DeployConfig()
    if resolved_root:
        config.flake_root = str(resolved_root)
    ctx.obj = AppContext(
        verbose=verbose,
        flake_root=resolved_root,
        config=config,
    )
