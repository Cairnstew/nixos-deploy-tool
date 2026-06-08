from __future__ import annotations

import typer

from nixos_deploy_tool.cli.commands.base import BaseCommand
from nixos_deploy_tool.cli.context import AppContext
from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.models.result import BaseResult
from nixos_deploy_tool.services.deploy import DeployService

app = typer.Typer()


class DeployRunCommand(BaseCommand):
    def __init__(
        self,
        ctx: AppContext,
        host: str = "",
        addr: str | None = None,
        extra_args: str | None = None,
    ) -> None:
        super().__init__(ctx)
        self.host = host
        self.addr = addr
        self.extra_args = extra_args

    def run(self) -> BaseResult:
        cfg = self.ctx.config or DeployConfig()
        svc = DeployService(cfg)
        return svc.run(self.host, self.addr, self.extra_args)


class DeployWizardCommand(BaseCommand):
    def __init__(self, ctx: AppContext, host: str = "") -> None:
        super().__init__(ctx)
        self.host = host

    def run(self) -> BaseResult:
        cfg = self.ctx.config or DeployConfig()
        svc = DeployService(cfg)
        return svc.wizard(self.host)


class DeployWithKeysCommand(BaseCommand):
    def __init__(
        self,
        ctx: AppContext,
        host: str = "",
        addr: str | None = None,
        extra_args: str | None = None,
    ) -> None:
        super().__init__(ctx)
        self.host = host
        self.addr = addr
        self.extra_args = extra_args

    def run(self) -> BaseResult:
        cfg = self.ctx.config or DeployConfig()
        svc = DeployService(cfg)
        return svc.with_keys(self.host, self.addr, self.extra_args)


class DeployTestCommand(BaseCommand):
    def __init__(self, ctx: AppContext, host: str = "") -> None:
        super().__init__(ctx)
        self.host = host

    def run(self) -> BaseResult:
        cfg = self.ctx.config or DeployConfig()
        svc = DeployService(cfg)
        return svc.test(self.host)


@app.command()
def run(
    ctx: typer.Context,
    host: str,
    addr: str | None = None,
    extra_args: str | None = typer.Option(
        None, "--extra-args", help="Extra arguments forwarded to nixos-anywhere"
    ),
) -> None:
    cmd = DeployRunCommand(ctx.obj, host=host, addr=addr, extra_args=extra_args)
    cmd.execute()


@app.command()
def wizard(ctx: typer.Context, host: str) -> None:
    cmd = DeployWizardCommand(ctx.obj, host=host)
    cmd.execute()


@app.command(name="with-keys")
def with_keys(
    ctx: typer.Context,
    host: str,
    addr: str | None = None,
    extra_args: str | None = typer.Option(
        None, "--extra-args", help="Extra arguments forwarded to nixos-anywhere"
    ),
) -> None:
    cmd = DeployWithKeysCommand(ctx.obj, host=host, addr=addr, extra_args=extra_args)
    cmd.execute()


@app.command()
def test(ctx: typer.Context, host: str) -> None:
    cmd = DeployTestCommand(ctx.obj, host=host)
    cmd.execute()


@app.callback()
def deploy(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo("Deploy commands. Use: nixos-deploy deploy [run|wizard|with-keys|test]")
