from __future__ import annotations

from typer.testing import CliRunner


def test_cli_help(runner: CliRunner, cli) -> None:
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.stdout


def test_cli_verbose_flag(runner: CliRunner, cli) -> None:
    result = runner.invoke(cli, ["--verbose", "iso", "list"])
    assert result.exit_code == 0


def test_cli_iso_list(runner: CliRunner, cli) -> None:
    result = runner.invoke(cli, ["iso", "list"])
    assert result.exit_code == 0


def test_cli_deploy_run_help(runner: CliRunner, cli) -> None:
    result = runner.invoke(cli, ["deploy", "--help"])
    assert result.exit_code == 0


def test_cli_tailscale_status(runner: CliRunner, cli) -> None:
    result = runner.invoke(cli, ["tailscale", "status"])
    assert result.exit_code == 0


def test_cli_secrets_list(runner: CliRunner, cli) -> None:
    result = runner.invoke(cli, ["secrets", "list"])
    assert result.exit_code == 0
