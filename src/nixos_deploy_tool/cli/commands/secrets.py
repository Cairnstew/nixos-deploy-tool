from __future__ import annotations

import typer

from nixos_deploy_tool.cli.commands.base import BaseCommand
from nixos_deploy_tool.cli.context import AppContext
from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.models.result import BaseResult, SuccessResult
from nixos_deploy_tool.services.secrets import SecretService

app = typer.Typer()


class SecretsListCommand(BaseCommand):
    def run(self) -> BaseResult:
        cfg = self.ctx.config or DeployConfig()
        svc = SecretService(cfg)
        secrets = svc.list_secrets()
        for s in secrets:
            typer.echo(f"  {s}")
        return SuccessResult(message=f"Found {len(secrets)} secret(s).")


class SecretsDecryptCommand(BaseCommand):
    def __init__(self, ctx: AppContext, name: str = "") -> None:
        super().__init__(ctx)
        self.name = name

    def run(self) -> BaseResult:
        cfg = self.ctx.config or DeployConfig()
        svc = SecretService(cfg)
        return svc.decrypt(self.name)


class SecretsInjectCommand(BaseCommand):
    def __init__(self, ctx: AppContext, iso_name: str = "") -> None:
        super().__init__(ctx)
        self.iso_name = iso_name

    def run(self) -> BaseResult:
        from nixos_deploy_tool.services.iso import ISOService

        cfg = self.ctx.config or DeployConfig()
        svc = ISOService(cfg)
        return svc.inject_secrets(self.iso_name, [])


class SecretsRekeyCommand(BaseCommand):
    def run(self) -> BaseResult:
        cfg = self.ctx.config or DeployConfig()
        svc = SecretService(cfg)
        return svc.rekey()


@app.command()
def list(ctx: typer.Context) -> None:  # noqa: A001
    cmd = SecretsListCommand(ctx.obj)
    cmd.execute()


@app.command()
def decrypt(ctx: typer.Context, name: str) -> None:
    cmd = SecretsDecryptCommand(ctx.obj, name=name)
    cmd.execute()


@app.command()
def inject(ctx: typer.Context, iso_name: str) -> None:
    cmd = SecretsInjectCommand(ctx.obj, iso_name=iso_name)
    cmd.execute()


@app.command()
def rekey(ctx: typer.Context) -> None:
    cmd = SecretsRekeyCommand(ctx.obj)
    cmd.execute()


@app.callback()
def secrets(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo("Secrets commands. Use: nixos-deploy secrets [list|decrypt|inject|rekey]")
