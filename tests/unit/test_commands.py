from __future__ import annotations

import pytest
import typer

from nixos_deploy_tool.cli.commands.base import BaseCommand
from nixos_deploy_tool.models.result import SuccessResult, ErrorResult
from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.cli.context import AppContext


def test_handle_result_success_does_not_exit(capsys: pytest.CaptureFixture[str]) -> None:
    ctx = AppContext(config=DeployConfig())
    cmd = BaseCommand(ctx)
    cmd.handle_result(SuccessResult(message="all good"))
    captured = capsys.readouterr()
    assert "all good" in captured.out


def test_handle_result_error_raises_exit() -> None:
    ctx = AppContext(config=DeployConfig())
    cmd = BaseCommand(ctx)
    with pytest.raises(typer.Exit):
        cmd.handle_result(ErrorResult(message="something broke"))


def test_subclass_overrides_run() -> None:
    class MyCommand(BaseCommand):
        def run(self) -> SuccessResult:
            return SuccessResult(message="overridden")

    ctx = AppContext(config=DeployConfig())
    cmd = MyCommand(ctx)
    result = cmd.run()
    assert result.message == "overridden"


def test_base_command_run_raises() -> None:
    ctx = AppContext(config=DeployConfig())
    cmd = BaseCommand(ctx)
    with pytest.raises(NotImplementedError):
        cmd.run()


def test_abort_raises_exit(capsys: pytest.CaptureFixture[str]) -> None:
    ctx = AppContext(config=DeployConfig())
    cmd = BaseCommand(ctx)
    with pytest.raises(typer.Exit):
        cmd.abort("something went wrong")
    captured = capsys.readouterr()
    assert "Aborted" in captured.err
