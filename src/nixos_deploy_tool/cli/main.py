from __future__ import annotations

from pathlib import Path

import typer

from nixos_deploy_tool.cli.commands import (
    deploy_app,
    iso_app,
    prepare_app,
    secrets_app,
    tailscale_app,
)
from nixos_deploy_tool.cli.config_loader import load_config
from nixos_deploy_tool.cli.context import AppContext
from nixos_deploy_tool.cli.logging import setup_logging

app = typer.Typer(no_args_is_help=True)
app.add_typer(iso_app, name="iso")
app.add_typer(deploy_app, name="deploy")
app.add_typer(prepare_app, name="prepare")
app.add_typer(tailscale_app, name="tailscale")
app.add_typer(secrets_app, name="secrets")


def _resolve_flake_root(flake_arg: Path | None, config: str) -> Path | None:
    if flake_arg:
        return flake_arg.expanduser().resolve()
    if config:
        return Path(config).expanduser()
    cwd = Path.cwd()
    if (cwd / "flake.nix").exists():
        return cwd
    return None


@app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = False,
    log_file: Path | None = None,
    flake_root: Path | None = None,
) -> None:
    ctx.ensure_object(dict)
    config = load_config()
    if log_file:
        config.log_file = str(log_file)
    resolved_root = _resolve_flake_root(flake_root, config.flake_root)
    if resolved_root:
        config.flake_root = str(resolved_root)
    ctx.obj = AppContext(
        verbose=verbose,
        flake_root=resolved_root,
        config=config,
    )
    setup_logging(config, verbose=verbose)
