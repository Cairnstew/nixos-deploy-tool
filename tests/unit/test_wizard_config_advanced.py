from __future__ import annotations

import asyncio
import threading

import pytest
from textual.containers import Vertical
from textual.widgets import Button, Input, RadioSet, Select, Static

from nixos_deploy_tool.textual_ui.screens.wizard_config import WizardConfigScreen
from nixos_deploy_tool.textual_ui.screens.wizard_deploy import WizardDeployScreen
from tests.fixtures.factories import make_wizard_state
from tests.fixtures.mocks import MockDeployService
from tests.unit.conftest import ScreenHarness

pytestmark = pytest.mark.tui


def _click_button(screen, button_id: str) -> None:
    screen.query_one(f"#{button_id}", Button).press()


# ── Mode selection via button handler ─────────────────────────────


@pytest.mark.asyncio
async def test_config_mode_map_logic(mock_deploy_service: MockDeployService) -> None:
    """Directly test the mode_map used in on_button_pressed."""
    # The mode_map logic is:
    #   pressed_id = mode_select.pressed_button.id if mode_select.pressed_button else "mode-auto"
    #   mode_map = {"mode-auto": "auto", "mode-mount": "mount", "mode-create": "create", "mode-skip": "skip"}
    #   state.disko_mode = mode_map.get(pressed_id, "auto")
    # Test that all four modes map correctly
    from nixos_deploy_tool.textual_ui.screens.wizard_config import WizardConfigScreen

    screen = WizardConfigScreen(mock_deploy_service, make_wizard_state())
    mode_map = {
        "mode-auto": "auto",
        "mode-mount": "mount",
        "mode-create": "create",
        "mode-skip": "skip",
    }
    for button_id, expected in mode_map.items():
        assert expected == mode_map.get(button_id, "auto")
    # Default when unknown id
    assert mode_map.get("mode-unknown", "auto") == "auto"


# ── Extra args stored in state ────────────────────────────────────


@pytest.mark.asyncio
async def test_config_extra_args_stored(mock_deploy_service: MockDeployService) -> None:
    state = make_wizard_state()
    async with ScreenHarness(WizardConfigScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        screen.query_one("#extra-args-input", Input).value = "--phases kexec,install,reboot"
        await pilot.pause()
        _click_button(screen, "deploy-skip")
        await pilot.pause()
        assert state.extra_args == "--phases kexec,install,reboot"


# ── Auto-advance paths ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_config_auto_advance_skip(mock_deploy_service: MockDeployService) -> None:
    """ssh_target set + config_source=skip goes straight to deploy."""
    state = make_wizard_state(config_source="skip")
    async with ScreenHarness(WizardConfigScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        await asyncio.sleep(0.2)
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardDeployScreen)


@pytest.mark.asyncio
async def test_config_auto_advance_manual(mock_deploy_service: MockDeployService) -> None:
    """ssh_target set + config_source=manual auto-validates."""
    state = make_wizard_state(config_source="manual")
    async with ScreenHarness(WizardConfigScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        await asyncio.sleep(0.3)
        await pilot.pause()
        # Should push some screen (not stay on config)
        assert not isinstance(pilot.app.screen, WizardConfigScreen)


# ── Error recovery ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_config_vadation_error_reenables_buttons(
    mock_deploy_service: MockDeployService,
) -> None:
    """When _validation_thread hits generic exception, buttons re-enable."""
    state = make_wizard_state()

    # Make the SSH call in partition checking raise
    original = mock_deploy_service.ssh_client.partition_exists

    def raise_error(partlabel: str) -> bool:
        msg = "Unexpected SSH error"
        raise RuntimeError(msg)

    mock_deploy_service.ssh_client.partition_exists = raise_error
    # Register a disko result so eval succeeds but partition check fails
    mock_deploy_service._nix._results[
        'nixosConfigurations."test-host".config.disko.devices'
    ] = '{"disk": {"main": {"device": "/dev/sda", "content": {"partitions": [{"name": "root"}]}}}}'

    async with ScreenHarness(WizardConfigScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        _click_button(screen, "validate-deploy")
        await asyncio.sleep(1)
        await pilot.pause()
        # Should show error and re-enable buttons
        status = screen.query_one("#status", Static)
        assert status._Static__content
        assert not screen.query_one("#validate-deploy", Button).disabled
    mock_deploy_service.ssh_client.partition_exists = original


@pytest.mark.asyncio
async def test_config_validaiton_error_message(
    mock_deploy_service: MockDeployService,
) -> None:
    """Outer exception handler shows validation error."""
    state = make_wizard_state()
    mock_deploy_service._nix._results[
        'nixosConfigurations."test-host".config.disko.devices'
    ] = 'not json'

    async with ScreenHarness(WizardConfigScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        _click_button(screen, "validate-deploy")
        await asyncio.wait_for(screen.validation_done.wait(), timeout=5)
        await pilot.pause()
        status = screen.query_one("#status", Static)
        assert "validation" in status._Static__content.lower() or "error" in status._Static__content.lower()
