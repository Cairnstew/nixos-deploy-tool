from __future__ import annotations

import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from nixos_deploy_tool.cli.context import AppContext
from nixos_deploy_tool.models.config import DeployConfig
from fixtures.factories import make_deploy_config
from fixtures.mocks import MockDeployService, MockFlakeIntrospector, MockNixRunner

_tests_dir = str(Path(__file__).resolve().parent)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, _tests_dir)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def cli():
    from nixos_deploy_tool.cli.main import app

    return app


@pytest.fixture
def default_config() -> DeployConfig:
    return make_deploy_config()


@pytest.fixture
def default_ctx(default_config: DeployConfig) -> AppContext:
    return AppContext(verbose=False, config=default_config)


@pytest.fixture
def mock_nix_runner() -> MockNixRunner:
    return MockNixRunner()


@pytest.fixture
def mock_flake() -> MockFlakeIntrospector:
    return MockFlakeIntrospector()


@pytest.fixture
def mock_deploy_service() -> MockDeployService:
    """DeployService with all mocks injected.  Safe for TUI / CLI tests."""
    return MockDeployService(config=make_deploy_config())


@pytest.fixture
def tui_app(mock_deploy_service: MockDeployService):
    """DeployToolApp wired with a MockDeployService via AppContext.

    No private-attr assignment — services flow through the
    constructor as designed.
    """
    from nixos_deploy_tool.textual_ui.app import DeployToolApp

    ctx = AppContext(
        config=make_deploy_config(),
    )
    ctx._services["deploy"] = mock_deploy_service
    app = DeployToolApp(context=ctx)
    app._svc = mock_deploy_service
    return app
