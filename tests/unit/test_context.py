from __future__ import annotations

from nixos_deploy_tool.cli.context import AppContext
from nixos_deploy_tool.models.config import DeployConfig


def test_appcontext_defaults() -> None:
    ctx = AppContext()
    assert ctx.verbose is False
    assert ctx.config is None


def test_appcontext_with_config() -> None:
    cfg = DeployConfig(log_level="debug")
    ctx = AppContext(verbose=True, config=cfg)
    assert ctx.verbose is True
    assert ctx.config is cfg
