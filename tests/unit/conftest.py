from __future__ import annotations

import pytest
from textual.app import App
from textual.screen import Screen

from nixos_deploy_tool.cli.context import AppContext
from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.textual_ui.app import DeployToolApp
from tests.fixtures.factories import make_deploy_config
from tests.fixtures.mocks import MockDeployService


class ScreenHarness(App[None]):
    """Minimal Textual App for testing a single screen in isolation.

    Usage::

        async with ScreenHarness(MyScreen(svc, state)).run_test() as pilot:
            ...
    """

    def __init__(self, screen: Screen) -> None:
        super().__init__()
        self._test_screen = screen

    def on_mount(self) -> None:
        self.push_screen(self._test_screen)


@pytest.fixture
def tui_app_async(mock_deploy_service: MockDeployService) -> DeployToolApp:
    """DeployToolApp wired with MockDeployService, ready for ``run_test()``.

    Access the mock service from tests via ``pilot.app._svc``.
    """
    ctx = AppContext(config=make_deploy_config())
    ctx._services["deploy"] = mock_deploy_service
    app = DeployToolApp(context=ctx)
    app._svc = mock_deploy_service
    return app
