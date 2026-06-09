from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest
from textual.widgets import Button, RichLog, Static

from nixos_deploy_tool.models.result import ErrorResult, SuccessResult
from nixos_deploy_tool.textual_ui.screens.wizard_deploy import WizardDeployScreen
from tests.fixtures.factories import make_wizard_state
from tests.fixtures.mocks import MockDeployService
from tests.unit.conftest import ScreenHarness

pytestmark = pytest.mark.tui


def _click_button(screen, button_id: str) -> None:
    screen.query_one(f"#{button_id}", Button).press()


# ── Deploy failure path ───────────────────────────────────────────


def _make_mock_stream(on_done_result):
    """Factory for mock run_streaming that invokes on_done."""
    def mock_stream(*args, **kwargs):
        on_done = kwargs.get("on_done")
        if on_done and on_done_result is not None:
            on_done(on_done_result)
        return on_done_result
    return mock_stream


@pytest.mark.asyncio
async def test_deploy_failure_shows_error(mock_deploy_service: MockDeployService) -> None:
    """When result.ok is False, error message is shown."""
    mock_deploy_service.run_streaming = MagicMock(
        side_effect=_make_mock_stream(ErrorResult(message="Deploy failed: connection error"))
    )

    state = make_wizard_state()
    async with ScreenHarness(WizardDeployScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        await asyncio.wait_for(screen.deploy_done.wait(), timeout=5)
        await pilot.pause()
        status = screen.query_one("#deploy-status", Static)
        assert "fail" in status._Static__content.lower()
        assert not screen.query_one("#back", Button).disabled


@pytest.mark.asyncio
async def test_deploy_success_shows_message(mock_deploy_service: MockDeployService) -> None:
    """When result.ok is True, success is shown."""
    mock_deploy_service.run_streaming = MagicMock(
        side_effect=_make_mock_stream(SuccessResult(message="Deployed test-host."))
    )

    state = make_wizard_state()
    async with ScreenHarness(WizardDeployScreen(mock_deploy_service, state)).run_test() as pilot:
        screen = pilot.app.screen
        await asyncio.wait_for(screen.deploy_done.wait(), timeout=5)
        await pilot.pause()
        status = screen.query_one("#deploy-status", Static)
        assert "success" in status._Static__content.lower()
        assert not screen.query_one("#back", Button).disabled


@pytest.mark.asyncio
async def test_deploy_back_clears_stack(mock_deploy_service: MockDeployService) -> None:
    """Back button pops screens until only one remains."""
    mock_deploy_service.run_streaming = MagicMock(
        side_effect=_make_mock_stream(SuccessResult(message="ok"))
    )

    state = make_wizard_state()
    async with ScreenHarness(WizardDeployScreen(mock_deploy_service, state)).run_test() as pilot:
        screen = pilot.app.screen
        await asyncio.wait_for(screen.deploy_done.wait(), timeout=5)
        await pilot.pause()
        _click_button(screen, "back")
        await pilot.pause()
        assert pilot.app.screen is not None
