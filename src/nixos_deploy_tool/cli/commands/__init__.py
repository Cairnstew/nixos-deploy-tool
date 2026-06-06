from nixos_deploy_tool.cli.commands.base import BaseCommand
from nixos_deploy_tool.cli.commands.deploy import app as deploy_app
from nixos_deploy_tool.cli.commands.iso import app as iso_app
from nixos_deploy_tool.cli.commands.secrets import app as secrets_app
from nixos_deploy_tool.cli.commands.tailscale import app as tailscale_app

__all__ = [
    "BaseCommand",
    "iso_app",
    "deploy_app",
    "tailscale_app",
    "secrets_app",
]
