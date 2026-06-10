from __future__ import annotations

import typer

from nixos_deploy_tool.cli.commands.base import BaseCommand
from nixos_deploy_tool.cli.context import AppContext
from nixos_deploy_tool.models.result import BaseResult
from nixos_deploy_tool.services.deploy import DeployService
from nixos_deploy_tool.textual_ui.app import run_tui

app = typer.Typer()


def _parse_disk_overrides(disk_args: list[str]) -> dict[str, str]:
    """Parse --disk name=dev pairs into a dict."""
    overrides: dict[str, str] = {}
    for item in disk_args:
        if "=" not in item:
            typer.echo(f"Warning: --disk '{item}' missing '=', expected name=device", err=True)
            continue
        name, _, device = item.partition("=")
        overrides[name.strip()] = device.strip()
    return overrides


def _confirm_disks(svc: DeployService, host_name: str, addr: str | None,
                   disk_overrides: dict[str, str] | None, yes: bool) -> None:
    """Show disko summary + partition preview and prompt for confirmation."""
    target = addr or host_name
    try:
        summary = svc.get_disko_summary(host_name)
        if summary and "No disko devices" not in summary:
            typer.echo(f"\nDisko configuration for {host_name}:")
            typer.echo(f"  {summary}")
    except Exception:
        typer.echo("(could not evaluate disko config to display target devices)")
    try:
        preview = svc.preview_partitions(
            host_name, target, svc.resolve_ssh_key(), disk_overrides,
        )
        if preview:
            typer.echo(f"\n{preview}")
    except Exception:
        pass
    if not yes:
        typer.echo("")
        typer.confirm("This may DESTROY DATA on the target device(s). Proceed?", abort=True)


class _BaseDeployCommand(BaseCommand):
    """Base for deploy commands that share host/addr/extra_args/disko_mode constructor params."""

    def __init__(
        self,
        ctx: AppContext,
        host: str = "",
        addr: str | None = None,
        extra_args: str | None = None,
        disk_overrides: dict[str, str] | None = None,
        disko_mode: str = "auto",
        yes: bool = False,
    ) -> None:
        super().__init__(ctx)
        self.host = host
        self.addr = addr
        self.extra_args = extra_args
        self.disk_overrides = disk_overrides
        self.disko_mode = disko_mode
        self.yes = yes


class DeployRunCommand(_BaseDeployCommand):
    def run(self) -> BaseResult:
        svc = self.ctx._get_deploy_service()
        _confirm_disks(svc, self.host, self.addr, self.disk_overrides, self.yes)
        return svc.run(self.host, self.addr, self.extra_args,
                        disk_overrides=self.disk_overrides, disko_mode=self.disko_mode)


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


class DeployWithKeysCommand(_BaseDeployCommand):
    def run(self) -> BaseResult:
        svc = self.ctx._get_deploy_service()
        _confirm_disks(svc, self.host, self.addr, self.disk_overrides, self.yes)
        return svc.with_keys(self.host, self.addr, self.extra_args,
                             disk_overrides=self.disk_overrides, disko_mode=self.disko_mode)


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
    disk: list[str] = typer.Option(
        [], "--disk", help="Map flake disk to device: --disk main=/dev/sda (repeatable)"
    ),
    disko_mode: str | None = typer.Option(
        None, "--disko-mode", help="Disko mode: auto, mount, create, skip"
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Skip confirmation prompt"
    ),
) -> None:
    disk_overrides = _parse_disk_overrides(disk)
    dm = disko_mode or "auto"
    cmd = DeployRunCommand(ctx.obj, host=host, addr=addr, extra_args=extra_args,
                           disk_overrides=disk_overrides, disko_mode=dm, yes=yes)
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
    disko_mode: str | None = typer.Option(
        None, "--disko-mode", help="Disko mode: auto, mount, create, skip"
    ),
    skip_disko: bool = typer.Option(
        False, "--skip-disko", help="Skip disko entirely (--disko-mode skip shorthand)"
    ),
    create_partitions: bool = typer.Option(
        False, "--create-partitions", help="Auto-create missing partitions without prompt"
    ),
) -> None:
    state_overrides: dict[str, object] = {}
    if host:
        state_overrides["host_name"] = host
    if addr:
        state_overrides["ssh_target"] = addr
    if extra_args:
        state_overrides["extra_args"] = extra_args
    if skip_disko:
        state_overrides["disko_mode"] = "skip"
        state_overrides["config_source"] = "skip"
    elif disko_mode is not None:
        state_overrides["disko_mode"] = disko_mode
        if disko_mode == "skip":
            state_overrides["config_source"] = "skip"
    if create_partitions:
        state_overrides["create_partitions"] = True
    run_tui(context=ctx.obj, state_overrides=state_overrides)


@app.command(name="with-keys")
def with_keys(
    ctx: typer.Context,
    host: str,
    addr: str | None = None,
    extra_args: str | None = typer.Option(
        None, "--extra-args", help="Extra arguments forwarded to nixos-anywhere"
    ),
    disk: list[str] = typer.Option(
        [], "--disk", help="Map flake disk to device: --disk main=/dev/sda (repeatable)"
    ),
    disko_mode: str | None = typer.Option(
        None, "--disko-mode", help="Disko mode: auto, mount, create, skip"
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Skip confirmation prompt"
    ),
) -> None:
    disk_overrides = _parse_disk_overrides(disk)
    dm = disko_mode or "auto"
    cmd = DeployWithKeysCommand(ctx.obj, host=host, addr=addr, extra_args=extra_args,
                                disk_overrides=disk_overrides, disko_mode=dm, yes=yes)
    cmd.execute()


@app.command()
def test(ctx: typer.Context, host: str) -> None:
    cmd = DeployTestCommand(ctx.obj, host=host)
    cmd.execute()


@app.callback()
def deploy(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo("Deploy commands. Use: nixos-deploy deploy [run|wizard|with-keys|test]")
