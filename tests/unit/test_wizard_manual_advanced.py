from __future__ import annotations

import asyncio

import pytest
from textual.widgets import Button, DataTable, Static

from nixos_deploy_tool.textual_ui.screens.wizard_manual import WizardManualScreen
from nixos_deploy_tool.textual_ui.screens.wizard_partitions import WizardPartitionScreen
from nixos_deploy_tool.textual_ui.screens.wizard_confirm import WizardConfirmScreen
from tests.fixtures.factories import make_wizard_state
from tests.fixtures.mocks import MockDeployService
from tests.unit.conftest import ScreenHarness

pytestmark = pytest.mark.tui

_MOCK_FLAKE_DISKS = {
    "disk": {
        "main": {"device": "/dev/sda", "content": {"partitions": [{"name": "root"}]}},
    },
}
_EMPTY_FLAKE = {"disk": {}}


def _click_button(screen, button_id: str) -> None:
    screen.query_one(f"#{button_id}", Button).press()


# ── Continue without selection (no-op) ────────────────────────────


@pytest.mark.asyncio
async def test_manual_continue_no_selection(mock_deploy_service: MockDeployService) -> None:
    """Continue pressed without selecting a device → no-op, stays on same screen."""
    state = make_wizard_state()
    async with ScreenHarness(
        WizardManualScreen(mock_deploy_service, state, _MOCK_FLAKE_DISKS)
    ).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        await asyncio.wait_for(screen.disks_loaded.wait(), timeout=5)
        await pilot.pause()
        # Continue is disabled until selection
        assert screen.query_one("#continue", Button).disabled
        _click_button(screen, "continue")
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardManualScreen)


# ── _find_parent_disk for unknown device ──────────────────────────


@pytest.mark.asyncio
async def test_manual_find_parent_unknown(mock_deploy_service: MockDeployService) -> None:
    """Unknown device path → returns itself (no crash)."""
    state = make_wizard_state()
    screen = WizardManualScreen(mock_deploy_service, state, _MOCK_FLAKE_DISKS)
    async with ScreenHarness(screen).run_test() as pilot:
        await pilot.pause()
        await asyncio.wait_for(screen.disks_loaded.wait(), timeout=5)
        await pilot.pause()
        # Call _find_parent_disk with unknown path
        result = screen._find_parent_disk("/dev/nonexistent")
        assert result == "/dev/nonexistent"


# ── Empty flake_devices → uses "main" fallback ────────────────────


@pytest.mark.asyncio
async def test_manual_empty_flake_devices(mock_deploy_service: MockDeployService) -> None:
    """No flake disk names → _execute_and_advance uses 'main'."""
    state = make_wizard_state()
    screen = WizardManualScreen(mock_deploy_service, state, _EMPTY_FLAKE)
    async with ScreenHarness(screen).run_test() as pilot:
        await pilot.pause()
        await asyncio.wait_for(screen.disks_loaded.wait(), timeout=5)
        await pilot.pause()
        table = screen.query_one("#target-disks-table", DataTable)
        table.move_cursor(row=0, column=0)
        table.action_select_cursor()
        await pilot.pause()
        assert state.manual_disk_selection == "/dev/sda"
        _click_button(screen, "continue")
        await pilot.pause()
        assert state.disko_disk_overrides == {"main": "/dev/sda"}


# ── config_source=manual routes to partition screen ───────────────


@pytest.mark.asyncio
async def test_manual_config_source_routes_to_partitions(
    mock_deploy_service: MockDeployService,
) -> None:
    """When config_source=manual and missing_partlabels empty → pushes partition screen."""
    state = make_wizard_state(config_source="manual", missing_partlabels=[])
    screen = WizardManualScreen(mock_deploy_service, state, _MOCK_FLAKE_DISKS)
    async with ScreenHarness(screen).run_test() as pilot:
        await pilot.pause()
        await asyncio.wait_for(screen.disks_loaded.wait(), timeout=5)
        await pilot.pause()
        table = screen.query_one("#target-disks-table", DataTable)
        table.move_cursor(row=0, column=0)
        table.action_select_cursor()
        await pilot.pause()
        _click_button(screen, "continue")
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardPartitionScreen)


# ── _flatten_devices with empty list ──────────────────────────────


@pytest.mark.asyncio
async def test_manual_flatten_empty(mock_deploy_service: MockDeployService) -> None:
    """_flatten_devices with empty list returns []."""
    state = make_wizard_state()
    screen = WizardManualScreen(mock_deploy_service, state, _MOCK_FLAKE_DISKS)
    async with ScreenHarness(screen).run_test() as pilot:
        await pilot.pause()
        flat = screen._flatten_devices([])
        assert flat == []


# ── Back button ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_manual_back_button(mock_deploy_service: MockDeployService) -> None:
    state = make_wizard_state()
    async with ScreenHarness(
        WizardManualScreen(mock_deploy_service, state, _MOCK_FLAKE_DISKS)
    ).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        await asyncio.wait_for(screen.disks_loaded.wait(), timeout=5)
        await pilot.pause()
        _click_button(screen, "back")
        await pilot.pause()
        assert pilot.app.screen is not None


# ── Partition selection resolves to parent disk on continue ───────


@pytest.mark.asyncio
async def test_manual_partition_selection_resolves_parent(
    mock_deploy_service: MockDeployService,
) -> None:
    """Selecting a partition stores parent disk in disko_disk_overrides."""
    state = make_wizard_state()
    screen = WizardManualScreen(mock_deploy_service, state, _MOCK_FLAKE_DISKS)
    async with ScreenHarness(screen).run_test() as pilot:
        await pilot.pause()
        await asyncio.wait_for(screen.disks_loaded.wait(), timeout=5)
        await pilot.pause()
        # Click first partition row (row 1 = sda1)
        table = screen.query_one("#target-disks-table", DataTable)
        table.move_cursor(row=1, column=0)
        table.action_select_cursor()
        await pilot.pause()
        assert state.manual_disk_selection == "/dev/sda1"
        _click_button(screen, "continue")
        await pilot.pause()
        # Should resolve /dev/sda1 to parent /dev/sda
        assert state.disko_disk_overrides
        assert list(state.disko_disk_overrides.values())[0] == "/dev/sda"
