from __future__ import annotations

import typer

from nixos_deploy_tool.cli.commands.base import BaseCommand
from nixos_deploy_tool.cli.context import AppContext
from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.models.result import BaseResult
from nixos_deploy_tool.services.prepare import PrepareService

app = typer.Typer()


class PrepareCommand(BaseCommand):
    def __init__(self, ctx: AppContext, host: str = "") -> None:
        super().__init__(ctx)
        self.host = host

    def run(self) -> BaseResult:
        cfg = self.ctx.config or DeployConfig()
        svc = PrepareService(cfg)
        return svc.prepare(self.host)


@app.callback(invoke_without_command=True)
def prepare(ctx: typer.Context, host: str) -> None:
    cmd = PrepareCommand(ctx.obj, host=host)
    cmd.execute()
