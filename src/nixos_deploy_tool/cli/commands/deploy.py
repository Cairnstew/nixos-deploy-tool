from __future__ import annotations

import typer

from nixos_deploy_tool.cli.commands.base import BaseCommand
from nixos_deploy_tool.cli.context import AppContext
from nixos_deploy_tool.models.result import BaseResult
from nixos_deploy_tool.textual_ui.app import run_tui

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
        svc = self.ctx._get_deploy_service()
        return svc.run(self.host, self.addr, self.extra_args)


class DeployWizardCommand(BaseCommand):
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
        svc = self.ctx._get_deploy_service()
        return svc.wizard(self.host, self.addr, self.extra_args)


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
        svc = self.ctx._get_deploy_service()
        return svc.with_keys(self.host, self.addr, self.extra_args)


class DeployTestCommand(BaseCommand):
    def __init__(self, ctx: AppContext, host: str = "") -> None:
        super().__init__(ctx)
        self.host = host

    def run(self) -> BaseResult:
        svc = self.ctx._get_deploy_service()
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
def wizard(
    ctx: typer.Context,
    host: str | None = typer.Option(
        None, "--host", help="Host to deploy (skip to select from TUI)"
    ),
    addr: str | None = None,
    extra_args: str | None = typer.Option(
        None, "--extra-args", help="Extra arguments forwarded to nixos-anywhere"
    ),
) -> None:
    if host:
        cmd = DeployWizardCommand(ctx.obj, host=host, addr=addr, extra_args=extra_args)
        cmd.execute()
    else:
        run_tui(context=ctx.obj)


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
