from __future__ import annotations

from pathlib import Path

from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.textual_ui.wizard_state import WizardState


def make_deploy_config(**overrides: object) -> DeployConfig:
    """Create a DeployConfig with sensible test defaults.

    Override any field::

        cfg = make_deploy_config(flake_root="/tmp/test", skip_disko=True)
    """
    defaults: dict[str, object] = dict(flake_root="/fake/project")
    defaults.update(overrides)
    return DeployConfig(**defaults)


def make_wizard_state(**overrides: object) -> WizardState:
    """Create a WizardState with overridable defaults."""
    defaults: dict[str, object] = dict(
        host_name="test-host",
        flake_attr="test-host",
        ssh_target="nixos@10.0.0.1",
        config_source="flake",
    )
    defaults.update(overrides)
    return WizardState(**defaults)
