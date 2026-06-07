from __future__ import annotations

import typer

from nixos_deploy_tool.cli.commands.base import BaseCommand
from nixos_deploy_tool.cli.context import AppContext
from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.models.result import BaseResult, SuccessResult
from nixos_deploy_tool.services.tailscale import TailscaleService

app = typer.Typer()
auth_key_app = typer.Typer()


class AuthKeyCreateCommand(BaseCommand):
    def __init__(self, ctx: AppContext, description: str = "", ephemeral: bool = True) -> None:
        super().__init__(ctx)
        self.description = description
        self.ephemeral = ephemeral

    def run(self) -> BaseResult:
        cfg = self.ctx.config or DeployConfig()
        svc = TailscaleService(cfg)
        return svc.create_auth_key(description=self.description, ephemeral=self.ephemeral)


class AuthKeyListCommand(BaseCommand):
    def run(self) -> BaseResult:
        cfg = self.ctx.config or DeployConfig()
        svc = TailscaleService(cfg)
        keys = svc.list_auth_keys()
        for k in keys:
            typer.echo(f"  {k.id}  {k.description}  expires={k.expires}")
        return SuccessResult(message=f"Found {len(keys)} key(s).")


class AuthKeyRevokeCommand(BaseCommand):
    def __init__(self, ctx: AppContext, key_id: str = "") -> None:
        super().__init__(ctx)
        self.key_id = key_id

    def run(self) -> BaseResult:
        cfg = self.ctx.config or DeployConfig()
        svc = TailscaleService(cfg)
        return svc.revoke_auth_key(self.key_id)


class StatusCommand(BaseCommand):
    def run(self) -> BaseResult:
        cfg = self.ctx.config or DeployConfig()
        svc = TailscaleService(cfg)
        return svc.status()


@auth_key_app.command(name="create")
def auth_key_create(
    ctx: typer.Context,
    description: str = "",
    ephemeral: bool = True,
) -> None:
    cmd = AuthKeyCreateCommand(ctx.obj, description=description, ephemeral=ephemeral)
    cmd.execute()


@auth_key_app.command(name="list")
def auth_key_list(ctx: typer.Context) -> None:
    cmd = AuthKeyListCommand(ctx.obj)
    cmd.execute()


@auth_key_app.command(name="revoke")
def auth_key_revoke(ctx: typer.Context, key_id: str) -> None:
    cmd = AuthKeyRevokeCommand(ctx.obj, key_id=key_id)
    cmd.execute()


@app.command()
def status(ctx: typer.Context) -> None:
    cmd = StatusCommand(ctx.obj)
    cmd.execute()


@auth_key_app.callback()
def auth_key(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo("Auth key commands. Use: nixos-deploy tailscale auth-key [create|list|revoke]")


app.add_typer(auth_key_app, name="auth-key")


@app.callback()
def tailscale(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo("Tailscale commands: [auth-key|status]")
