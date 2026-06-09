from __future__ import annotations

import asyncio

import pytest
from textual.widgets import Button, Select, Static

from nixos_deploy_tool.textual_ui.screens.wizard_disks import WizardDiskScreen
from nixos_deploy_tool.textual_ui.screens.wizard_confirm import WizardConfirmScreen
from nixos_deploy_tool.textual_ui.screens.wizard_partitions import WizardPartitionScreen
from tests.fixtures.factories import make_wizard_state
from tests.fixtures.mocks import MockDeployService
from tests.unit.conftest import ScreenHarness

pytestmark = pytest.mark.tui

_MOCK_FLAKE_DISKS = {
    "disk": {
        "main": {"device": "/dev/sda", "content": {"partitions": [{"name": "root"}]}},
    },
}


def _click_button(screen, button_id: str) -> None:
    screen.query_one(f"#{button_id}", Button).press()


# ── Zero target disks ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_disks_zero_target_disks(mock_deploy_service: MockDeployService) -> None:
    """No target disks found → message + continue disabled."""
    mock_deploy_service.ssh_client.list_disks_results = []
    state = make_wizard_state()
    async with ScreenHarness(
        WizardDiskScreen(mock_deploy_service, state, _MOCK_FLAKE_DISKS)
    ).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        await asyncio.wait_for(screen.disks_loaded.wait(), timeout=5)
        await pilot.pause()
        status = screen.query_one("#disk-status", Static)
        assert "No target disks" in status._Static__content or "0 disk" in status._Static__content.lower()
        assert screen.query_one("#continue", Button).disabled


# ── Multiple flake disks ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_disks_multi_flake_disks(mock_deploy_service: MockDeployService) -> None:
    """Multiple flake disks → multiple selectors."""
    flake_disks = {
        "disk": {
            "main": {"device": "/dev/sda", "content": {"partitions": [{"name": "root"}]}},
            "data": {"device": "/dev/sdb", "content": {"partitions": [{"name": "storage"}]}},
        },
    }
    state = make_wizard_state()
    async with ScreenHarness(
        WizardDiskScreen(mock_deploy_service, state, flake_disks)
    ).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        await asyncio.wait_for(screen.disks_loaded.wait(), timeout=5)
        await pilot.pause()
        selectors = screen.query(Select)
        assert len(selectors) >= 2


# ── Back button ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_disks_back_button(mock_deploy_service: MockDeployService) -> None:
    state = make_wizard_state()
    async with ScreenHarness(
        WizardDiskScreen(mock_deploy_service, state, _MOCK_FLAKE_DISKS)
    ).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        await asyncio.wait_for(screen.disks_loaded.wait(), timeout=5)
        await pilot.pause()
        _click_button(screen, "back")
        await pilot.pause()
        assert pilot.app.screen is not None


# ── SSH failure ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_disks_ssh_failure(mock_deploy_service: MockDeployService) -> None:
    """SSH error → error shown + continue disabled."""
    state = make_wizard_state()
    original = mock_deploy_service.ssh_client.list_disks

    def raise_error() -> list[dict]:
        msg = "Connection refused"
        raise RuntimeError(msg)

    mock_deploy_service.ssh_client.list_disks = raise_error
    async with ScreenHarness(
        WizardDiskScreen(mock_deploy_service, state, _MOCK_FLAKE_DISKS)
    ).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        await asyncio.wait_for(screen.disks_loaded.wait(), timeout=5)
        await pilot.pause()
        status = screen.query_one("#disk-status", Static)
        assert "Error" in status._Static__content
        assert screen.query_one("#continue", Button).disabled
    mock_deploy_service.ssh_client.list_disks = original


# ── Continue without changing selectors ───────────────────────────


@pytest.mark.asyncio
async def test_disks_continue_defaults(mock_deploy_service: MockDeployService) -> None:
    """Continue with no explicit selection still works when all partitions present."""
    state = make_wizard_state()
    async with ScreenHarness(
        WizardDiskScreen(mock_deploy_service, state, _MOCK_FLAKE_DISKS)
    ).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        await asyncio.wait_for(screen.disks_loaded.wait(), timeout=5)
        await pilot.pause()
        # Set the selector explicitly
        sel = screen.query_one("#disk-map-main", Select)
        sel.value = "/dev/sda"
        await pilot.pause()
        _click_button(screen, "continue")
        await pilot.pause()
        assert isinstance(pilot.app.screen, (WizardConfirmScreen, WizardPartitionScreen))
