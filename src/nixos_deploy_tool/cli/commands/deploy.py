from __future__ import annotations

import typer

from nixos_deploy_tool.cli.commands.base import BaseCommand
from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.models.result import BaseResult
from nixos_deploy_tool.services.deploy import DeployService

app = typer.Typer()


class DeployRunCommand(BaseCommand):
    host: str = ""
    addr: str | None = None

    def run(self) -> BaseResult:
        cfg = self.ctx.config or DeployConfig()
        svc = DeployService(cfg)
        return svc.run(self.host, self.addr)


class DeployWizardCommand(BaseCommand):
    host: str = ""

    def run(self) -> BaseResult:
        cfg = self.ctx.config or DeployConfig()
        svc = DeployService(cfg)
        return svc.wizard(self.host)


class DeployWithKeysCommand(BaseCommand):
    host: str = ""

    def run(self) -> BaseResult:
        cfg = self.ctx.config or DeployConfig()
        svc = DeployService(cfg)
        return svc.with_keys(self.host)


class DeployTestCommand(BaseCommand):
    host: str = ""

    def run(self) -> BaseResult:
        cfg = self.ctx.config or DeployConfig()
        svc = DeployService(cfg)
        return svc.test(self.host)


@app.command()
def run(ctx: typer.Context, host: str, addr: str | None = None) -> None:
    cmd = DeployRunCommand(ctx.obj)
    cmd.host = host
    cmd.addr = addr
    cmd.handle_result(cmd.run())


@app.command()
def wizard(ctx: typer.Context, host: str) -> None:
    cmd = DeployWizardCommand(ctx.obj)
    cmd.host = host
    cmd.handle_result(cmd.run())


@app.command(name="with-keys")
def with_keys(ctx: typer.Context, host: str) -> None:
    cmd = DeployWithKeysCommand(ctx.obj)
    cmd.host = host
    cmd.handle_result(cmd.run())


@app.command()
def test(ctx: typer.Context, host: str) -> None:
    cmd = DeployTestCommand(ctx.obj)
    cmd.host = host
    cmd.handle_result(cmd.run())


@app.callback(invoke_without_command=True)
def deploy(ctx: typer.Context) -> None:
    typer.echo("Deploy commands. Use: nixos-deploy deploy [run|wizard|with-keys|test]")
