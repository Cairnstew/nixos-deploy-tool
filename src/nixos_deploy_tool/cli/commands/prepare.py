from __future__ import annotations

import typer

from nixos_deploy_tool.cli.commands.base import BaseCommand
from nixos_deploy_tool.cli.context import AppContext
from nixos_deploy_tool.models.result import BaseResult

app = typer.Typer()


class PrepareCommand(BaseCommand):
    def __init__(self, ctx: AppContext, host: str = "") -> None:
        super().__init__(ctx)
        self.host = host

    def run(self) -> BaseResult:
        svc = self.ctx._get_prepare_service()
        return svc.prepare(self.host)


@app.callback(invoke_without_command=True)
def prepare(ctx: typer.Context, host: str) -> None:
    cmd = PrepareCommand(ctx.obj, host=host)
    cmd.execute()
