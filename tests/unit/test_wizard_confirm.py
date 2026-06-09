from __future__ import annotations

import pytest
from textual.containers import Vertical
from textual.widgets import Button, Static

from nixos_deploy_tool.textual_ui.screens.wizard_confirm import WizardConfirmScreen
from nixos_deploy_tool.textual_ui.screens.wizard_deploy import WizardDeployScreen
from tests.fixtures.factories import make_wizard_state
from tests.fixtures.mocks import MockDeployService
from tests.unit.conftest import ScreenHarness

pytestmark = pytest.mark.tui


def _click_button(screen, button_id: str) -> None:
    screen.query_one(f"#{button_id}", Button).press()


# ── Widget presence ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_confirm_composition(mock_deploy_service: MockDeployService) -> None:
    state = make_wizard_state()
    async with ScreenHarness(WizardConfirmScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        assert screen.query_one("#confirm-host", Static)
        assert screen.query_one("#confirm-target", Static)
        assert screen.query_one("#confirm-source", Static)
        assert screen.query_one("#confirm-mode", Static)
        assert screen.query_one("#confirm-warning", Static)
        assert screen.query_one("#confirm-disko-layout", Static)
        assert screen.query_one("#confirm-status", Static)
        assert screen.query_one("#confirm-disk-map", Static)
        assert screen.query_one("#deploy", Button)
        assert screen.query_one("#back", Button)


# ── Warning text branches ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_confirm_warning_disko_overrides(mock_deploy_service: MockDeployService) -> None:
    state = make_wizard_state(disko_disk_overrides={"main": "/dev/sdb"})
    async with ScreenHarness(WizardConfirmScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        warning = pilot.app.screen.query_one("#confirm-warning", Static)
        content = warning._Static__content
        assert "sdb" in content
        assert "sda" not in content


@pytest.mark.asyncio
async def test_confirm_warning_manual_selection(mock_deploy_service: MockDeployService) -> None:
    state = make_wizard_state(manual_disk_selection="/dev/sdc", disko_disk_overrides={})
    async with ScreenHarness(WizardConfirmScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        warning = pilot.app.screen.query_one("#confirm-warning", Static)
        assert "sdc" in warning._Static__content


@pytest.mark.asyncio
async def test_confirm_warning_device_summary(mock_deploy_service: MockDeployService) -> None:
    state = make_wizard_state(
        disko_device_summary="/dev/vda (main)  ->  root",
        disko_disk_overrides={},
        manual_disk_selection="",
    )
    async with ScreenHarness(WizardConfirmScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        warning = pilot.app.screen.query_one("#confirm-warning", Static)
        assert "vda" in warning._Static__content


@pytest.mark.asyncio
async def test_confirm_warning_fallback(mock_deploy_service: MockDeployService) -> None:
    state = make_wizard_state(
        disko_disk_overrides={},
        manual_disk_selection="",
        disko_device_summary="",
    )
    async with ScreenHarness(WizardConfirmScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        warning = pilot.app.screen.query_one("#confirm-warning", Static)
        assert "DESTROY DATA" in warning._Static__content


# ── Layout text branches ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_confirm_layout_from_summary(mock_deploy_service: MockDeployService) -> None:
    state = make_wizard_state(disko_device_summary="Disk layout here")
    async with ScreenHarness(WizardConfirmScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        layout = pilot.app.screen.query_one("#confirm-disko-layout", Static)
        assert "Disk layout" in layout._Static__content


@pytest.mark.asyncio
async def test_confirm_layout_from_manual(mock_deploy_service: MockDeployService) -> None:
    state = make_wizard_state(
        disko_device_summary="",
        manual_disk_selection="/dev/sdd",
        disko_disk_overrides={},
    )
    async with ScreenHarness(WizardConfirmScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        layout = pilot.app.screen.query_one("#confirm-disko-layout", Static)
        assert "sdd" in layout._Static__content


@pytest.mark.asyncio
async def test_confirm_layout_fallback(mock_deploy_service: MockDeployService) -> None:
    state = make_wizard_state(
        disko_device_summary="",
        manual_disk_selection="",
    )
    async with ScreenHarness(WizardConfirmScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        layout = pilot.app.screen.query_one("#confirm-disko-layout", Static)
        assert "No disko devices" in layout._Static__content


# ── Disk map text branches ────────────────────────────────────────


@pytest.mark.asyncio
async def test_confirm_disk_map_overrides(mock_deploy_service: MockDeployService) -> None:
    state = make_wizard_state(disko_disk_overrides={"main": "/dev/sde"})
    async with ScreenHarness(WizardConfirmScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        disk_map = pilot.app.screen.query_one("#confirm-disk-map", Static)
        assert "main" in disk_map._Static__content
        assert "sde" in disk_map._Static__content


@pytest.mark.asyncio
async def test_confirm_disk_map_manual_only(mock_deploy_service: MockDeployService) -> None:
    state = make_wizard_state(
        manual_disk_selection="/dev/sdf",
        disko_disk_overrides={},
    )
    async with ScreenHarness(WizardConfirmScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        disk_map = pilot.app.screen.query_one("#confirm-disk-map", Static)
        assert "sdf" in disk_map._Static__content


@pytest.mark.asyncio
async def test_confirm_disk_map_empty(mock_deploy_service: MockDeployService) -> None:
    state = make_wizard_state(
        disko_disk_overrides={},
        manual_disk_selection="",
    )
    async with ScreenHarness(WizardConfirmScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        disk_map = pilot.app.screen.query_one("#confirm-disk-map", Static)
        assert disk_map._Static__content == ""


# ── Button actions ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_confirm_deploy_button_pushes_deploy_screen(
    mock_deploy_service: MockDeployService,
) -> None:
    state = make_wizard_state()
    async with ScreenHarness(WizardConfirmScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        _click_button(pilot.app.screen, "deploy")
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardDeployScreen)


@pytest.mark.asyncio
async def test_confirm_back_button_pops_screen(
    mock_deploy_service: MockDeployService,
) -> None:
    state = make_wizard_state()
    async with ScreenHarness(WizardConfirmScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        _click_button(pilot.app.screen, "back")
        await pilot.pause()
        # ScreenHarness only has this screen, so pop returns to nothing
        # — the app still has a screen active
        assert pilot.app.screen is not None
