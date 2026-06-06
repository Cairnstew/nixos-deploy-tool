from __future__ import annotations

import typer

from nixos_deploy_tool.cli.commands.base import BaseCommand
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
    name: str = ""

    def run(self) -> BaseResult:
        cfg = self.ctx.config or DeployConfig()
        svc = SecretService(cfg)
        return svc.decrypt(self.name)


class SecretsInjectCommand(BaseCommand):
    iso_name: str = ""

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
    cmd.handle_result(cmd.run())


@app.command()
def decrypt(ctx: typer.Context, name: str) -> None:
    cmd = SecretsDecryptCommand(ctx.obj)
    cmd.name = name
    cmd.handle_result(cmd.run())


@app.command()
def inject(ctx: typer.Context, iso_name: str) -> None:
    cmd = SecretsInjectCommand(ctx.obj)
    cmd.iso_name = iso_name
    cmd.handle_result(cmd.run())


@app.command()
def rekey(ctx: typer.Context) -> None:
    cmd = SecretsRekeyCommand(ctx.obj)
    cmd.handle_result(cmd.run())


@app.callback(invoke_without_command=True)
def secrets(ctx: typer.Context) -> None:
    typer.echo("Secrets commands. Use: nixos-deploy secrets [list|decrypt|inject|rekey]")
