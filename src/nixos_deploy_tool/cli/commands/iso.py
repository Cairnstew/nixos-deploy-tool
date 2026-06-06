from __future__ import annotations

import typer

from nixos_deploy_tool.cli.commands.base import BaseCommand
from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.models.result import BaseResult
from nixos_deploy_tool.services.iso import ISOService

app = typer.Typer()


class ISOBuildCommand(BaseCommand):
    name: str = ""

    def run(self) -> BaseResult:
        cfg = self.ctx.config or DeployConfig()
        svc = ISOService(cfg)
        return svc.build(self.name)


class ISOListCommand(BaseCommand):
    def run(self) -> BaseResult:
        cfg = self.ctx.config or DeployConfig()
        svc = ISOService(cfg)
        isos = svc.list_isos()
        for iso in isos:
            typer.echo(f"  {iso.name}")
        from nixos_deploy_tool.models.result import SuccessResult

        return SuccessResult(message=f"Found {len(isos)} ISO(s).")


class ISORotateKeysCommand(BaseCommand):
    name: str = ""

    def run(self) -> BaseResult:
        cfg = self.ctx.config or DeployConfig()
        svc = ISOService(cfg)
        return svc.rotate_keys(self.name)


class ISOInfoCommand(BaseCommand):
    name: str = ""

    def run(self) -> BaseResult:
        cfg = self.ctx.config or DeployConfig()
        svc = ISOService(cfg)
        iso = svc.info(self.name)
        if iso:
            typer.echo(f"Name: {iso.name}")
            typer.echo(f"Flake attr: {iso.flake_attr}")
            typer.echo(f"System: {iso.system}")
        from nixos_deploy_tool.models.result import SuccessResult

        return SuccessResult(message=f"Info for {self.name}.")


@app.callback(invoke_without_command=True)
def iso(ctx: typer.Context) -> None:
    typer.echo("ISO commands. Use: nixos-deploy iso [build|list|rotate-keys|info]")


@app.command()
def build(ctx: typer.Context, name: str) -> None:
    cmd = ISOBuildCommand(ctx.obj)
    cmd.name = name
    cmd.handle_result(cmd.run())


@app.command()
def list(ctx: typer.Context) -> None:  # noqa: A001
    cmd = ISOListCommand(ctx.obj)
    cmd.handle_result(cmd.run())


@app.command(name="rotate-keys")
def rotate_keys(ctx: typer.Context, name: str) -> None:
    cmd = ISORotateKeysCommand(ctx.obj)
    cmd.name = name
    cmd.handle_result(cmd.run())


@app.command()
def info(ctx: typer.Context, name: str) -> None:
    cmd = ISOInfoCommand(ctx.obj)
    cmd.name = name
    cmd.handle_result(cmd.run())
