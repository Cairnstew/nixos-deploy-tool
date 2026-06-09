from __future__ import annotations

import pytest
from textual.widgets import DataTable

from nixos_deploy_tool.textual_ui.screens.wizard_config import WizardConfigScreen
from nixos_deploy_tool.textual_ui.screens.wizard_host import WizardHostScreen
from nixos_deploy_tool.textual_ui.wizard_state import WizardState
from tests.fixtures.factories import make_wizard_state
from tests.fixtures.mocks import MockDeployService, MockFlakeIntrospector
from tests.unit.conftest import ScreenHarness

pytestmark = pytest.mark.tui


def _select_host(screen) -> None:
    table = screen.query_one("#hosts-table", DataTable)
    table.move_cursor(row=0, column=0)
    table.action_select_cursor()


# ── Empty host list ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_host_empty_list(mock_deploy_service: MockDeployService) -> None:
    """Empty host list → no crash, table is empty."""
    mock_deploy_service._flake._hosts = []
    state = WizardState()
    async with ScreenHarness(
        WizardHostScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        table = screen.query_one("#hosts-table", DataTable)
        assert table.row_count == 0


# ── Pre-filled host, not in flake ─────────────────────────────────


@pytest.mark.asyncio
async def test_host_prefilled_not_in_flake(mock_deploy_service: MockDeployService) -> None:
    """Pre-filled host still auto-advances (but flake_attr stays default)."""
    state = make_wizard_state(host_name="nonexistent-host", ssh_target="")
    mock_deploy_service._flake._hosts = [{"name": "real-host", "attr": "real-host"}]
    async with ScreenHarness(
        WizardHostScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardConfigScreen)


# ── Host entry missing 'attr' key → load_rows raises ──────────────


@pytest.mark.asyncio
async def test_host_missing_attr_raises(mock_deploy_service: MockDeployService) -> None:
    """Host entry without 'attr' key → KeyError."""
    state = make_wizard_state(host_name="test-box", ssh_target="")
    mock_deploy_service._flake._hosts = [{"name": "test-box"}]
    with pytest.raises(KeyError):
        WizardHostScreen(mock_deploy_service, state).load_rows()


# ── Selecting a host sets state and pushes config ─────────────────


@pytest.mark.asyncio
async def test_host_selection_mutation(mock_deploy_service: MockDeployService) -> None:
    """Selecting a host updates WizardState and pushes config screen."""
    state = WizardState()
    mock_deploy_service._flake._hosts = [{"name": "my-host", "attr": "my-host"}]
    async with ScreenHarness(
        WizardHostScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()
        _select_host(pilot.app.screen)
        await pilot.pause()
        assert state.host_name == "my-host"
        assert state.flake_attr == "my-host"
        assert isinstance(pilot.app.screen, WizardConfigScreen)
