from __future__ import annotations

from abc import ABC, abstractmethod

import typer

from nixos_deploy_tool.cli.context import AppContext
from nixos_deploy_tool.exceptions import NixosDeployError
from nixos_deploy_tool.models.result import BaseResult


class BaseCommand(ABC):
    def __init__(self, ctx: AppContext) -> None:
        self.ctx = ctx

    @abstractmethod
    def run(self) -> BaseResult:
        ...

    def execute(self) -> None:
        try:
            result = self.run()
        except NixosDeployError as exc:
            self.abort(str(exc))
        except Exception as exc:
            self.abort(f"Unexpected error: {exc}")
        else:
            self.handle_result(result)

    def handle_result(self, result: BaseResult) -> None:
        if result.ok:
            typer.echo(result.message or "Done.")
        else:
            typer.secho(f"Error: {result.message}", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)

    def abort(self, msg: str) -> None:
        typer.secho(f"Aborted: {msg}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
