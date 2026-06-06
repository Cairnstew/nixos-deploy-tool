from __future__ import annotations

import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.cli.context import AppContext

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def cli():
    from nixos_deploy_tool.cli.main import app

    return app


@pytest.fixture
def default_config() -> DeployConfig:
    return DeployConfig()


@pytest.fixture
def default_ctx(default_config: DeployConfig) -> AppContext:
    return AppContext(verbose=False, config=default_config)
