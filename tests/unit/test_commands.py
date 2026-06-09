from __future__ import annotations

import pytest
import typer

from nixos_deploy_tool.cli.commands.base import BaseCommand
from nixos_deploy_tool.models.result import BaseResult, SuccessResult, ErrorResult
from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.cli.context import AppContext


class _ConcreteCommand(BaseCommand):
    """Minimal concrete command for testing base class behavior."""

    def run(self) -> BaseResult:
        return SuccessResult(message="test")


def test_handle_result_success_does_not_exit(capsys: pytest.CaptureFixture[str]) -> None:
    ctx = AppContext(config=DeployConfig())
    cmd = _ConcreteCommand(ctx)
    cmd.handle_result(SuccessResult(message="all good"))
    captured = capsys.readouterr()
    assert "all good" in captured.out


def test_handle_result_error_raises_exit() -> None:
    ctx = AppContext(config=DeployConfig())
    cmd = _ConcreteCommand(ctx)
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


def test_base_command_run_must_be_implemented() -> None:
    with pytest.raises(TypeError, match="abstract"):
        BaseCommand(AppContext(config=DeployConfig()))  # type: ignore[abstract]


def test_abort_raises_exit(capsys: pytest.CaptureFixture[str]) -> None:
    ctx = AppContext(config=DeployConfig())
    cmd = _ConcreteCommand(ctx)
    with pytest.raises(typer.Exit):
        cmd.abort("something went wrong")
    captured = capsys.readouterr()
    assert "Aborted" in captured.err


def test_execute_calls_run_and_handle_result(capsys: pytest.CaptureFixture[str]) -> None:
    ctx = AppContext(config=DeployConfig())
    cmd = _ConcreteCommand(ctx)
    cmd.execute()
    captured = capsys.readouterr()
    assert "test" in captured.out


def test_execute_catches_nixos_deploy_error_and_aborts(capsys: pytest.CaptureFixture[str]) -> None:
    from nixos_deploy_tool.exceptions import DeployRuntimeError

    class FailingCommand(BaseCommand):
        def run(self) -> BaseResult:
            raise DeployRuntimeError("deploy kaboom")

    ctx = AppContext(config=DeployConfig())
    cmd = FailingCommand(ctx)
    with pytest.raises(typer.Exit):
        cmd.execute()
    captured = capsys.readouterr()
    assert "deploy kaboom" in captured.err
