from __future__ import annotations

import typer

from nixos_deploy_tool.cli.commands.base import BaseCommand
from nixos_deploy_tool.cli.context import AppContext
from nixos_deploy_tool.models.result import BaseResult, SuccessResult

app = typer.Typer()


class ISOBuildCommand(BaseCommand):
    def __init__(self, ctx: AppContext, name: str = "") -> None:
        super().__init__(ctx)
        self.name = name

    def run(self) -> BaseResult:
        svc = self.ctx._get_iso_service()
        return svc.build(self.name)


class ISOListCommand(BaseCommand):
    def run(self) -> BaseResult:
        svc = self.ctx._get_iso_service()
        isos = svc.list_isos()
        for iso in isos:
            typer.echo(f"  {iso.name}")
        return SuccessResult(message=f"Found {len(isos)} ISO(s).")


class ISORotateKeysCommand(BaseCommand):
    def __init__(self, ctx: AppContext, name: str = "") -> None:
        super().__init__(ctx)
        self.name = name

    def run(self) -> BaseResult:
        svc = self.ctx._get_iso_service()
        return svc.rotate_keys(self.name)


class ISOInfoCommand(BaseCommand):
    def __init__(self, ctx: AppContext, name: str = "") -> None:
        super().__init__(ctx)
        self.name = name

    def run(self) -> BaseResult:
        svc = self.ctx._get_iso_service()
        iso = svc.info(self.name)
        if iso:
            typer.echo(f"Name: {iso.name}")
            typer.echo(f"Flake attr: {iso.flake_attr}")
            typer.echo(f"System: {iso.system}")
        return SuccessResult(message=f"Info for {self.name}.")


@app.callback()
def iso(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo("ISO commands. Use: nixos-deploy iso [build|list|rotate-keys|info]")


@app.command()
def build(ctx: typer.Context, name: str) -> None:
    cmd = ISOBuildCommand(ctx.obj, name=name)
    cmd.execute()


@app.command()
def list(ctx: typer.Context) -> None:  # noqa: A001
    cmd = ISOListCommand(ctx.obj)
    cmd.execute()


@app.command(name="rotate-keys")
def rotate_keys(ctx: typer.Context, name: str) -> None:
    cmd = ISORotateKeysCommand(ctx.obj, name=name)
    cmd.execute()


@app.command()
def info(ctx: typer.Context, name: str) -> None:
    cmd = ISOInfoCommand(ctx.obj, name=name)
    cmd.execute()
