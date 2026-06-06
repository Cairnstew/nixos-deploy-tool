from __future__ import annotations

import typer

from nixos_deploy_tool.cli.commands.base import BaseCommand
from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.models.result import BaseResult, SuccessResult
from nixos_deploy_tool.services.tailscale import TailscaleService

app = typer.Typer()


class AuthKeyCreateCommand(BaseCommand):
    description: str = ""
    ephemeral: bool = True

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
    key_id: str = ""

    def run(self) -> BaseResult:
        cfg = self.ctx.config or DeployConfig()
        svc = TailscaleService(cfg)
        return svc.revoke_auth_key(self.key_id)


class StatusCommand(BaseCommand):
    def run(self) -> BaseResult:
        cfg = self.ctx.config or DeployConfig()
        svc = TailscaleService(cfg)
        return svc.status()


@app.command(name="auth-key")
def auth_key(ctx: typer.Context) -> None:
    typer.echo("Use: nixos-deploy tailscale auth-key [create|list|revoke]")


@app.command(name="auth-key-create")
def auth_key_create(
    ctx: typer.Context,
    description: str = "",
    ephemeral: bool = True,
) -> None:
    cmd = AuthKeyCreateCommand(ctx.obj)
    cmd.description = description
    cmd.ephemeral = ephemeral
    cmd.handle_result(cmd.run())


@app.command(name="auth-key-list")
def auth_key_list(ctx: typer.Context) -> None:
    cmd = AuthKeyListCommand(ctx.obj)
    cmd.handle_result(cmd.run())


@app.command(name="auth-key-revoke")
def auth_key_revoke(ctx: typer.Context, key_id: str) -> None:
    cmd = AuthKeyRevokeCommand(ctx.obj)
    cmd.key_id = key_id
    cmd.handle_result(cmd.run())


@app.command()
def status(ctx: typer.Context) -> None:
    cmd = StatusCommand(ctx.obj)
    cmd.handle_result(cmd.run())


@app.callback(invoke_without_command=True)
def tailscale(ctx: typer.Context) -> None:
    typer.echo("Tailscale commands: [auth-key-create|auth-key-list|auth-key-revoke|status]")
