from __future__ import annotations

import asyncio
import json

import pytest
from textual.widgets import Button, DataTable, Input, RadioSet, RichLog, Static

from nixos_deploy_tool.textual_ui.screens.main import MainScreen
from nixos_deploy_tool.textual_ui.screens.wizard_config import WizardConfigScreen
from nixos_deploy_tool.textual_ui.screens.wizard_confirm import WizardConfirmScreen
from nixos_deploy_tool.textual_ui.screens.wizard_deploy import WizardDeployScreen
from nixos_deploy_tool.textual_ui.screens.wizard_host import WizardHostScreen
from nixos_deploy_tool.textual_ui.screens.wizard_partitions import (
    WizardPartitionScreen,
)
from nixos_deploy_tool.textual_ui.wizard_state import WizardState
from tests.fixtures.factories import make_wizard_state
from tests.fixtures.mocks import MockDeployService
from tests.unit.conftest import ScreenHarness

pytestmark = pytest.mark.tui


def _click_button(screen, button_id: str) -> None:
    """Press a button by ID (bypasses pilot.click which doesn't work in v8)."""
    screen.query_one(f"#{button_id}", Button).press()


def _select_host(screen) -> None:
    """Simulate selecting the first row in the hosts table."""
    table = screen.query_one("#hosts-table", DataTable)
    table.move_cursor(row=0, column=0)
    table.action_select_cursor()


# ── MainScreen ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_main_screen_composition(mock_deploy_service: MockDeployService) -> None:
    state = WizardState()
    async with ScreenHarness(MainScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        assert screen.query_one("#iso", Button).label == "Build ISO"
        assert screen.query_one("#deploy", Button).label == "Deploy Wizard"
        assert screen.query_one("#secrets", Button).label == "Secrets"
        assert screen.query_one("#tailscale", Button).label == "Tailscale"


@pytest.mark.asyncio
async def test_main_screen_deploy_navigation(
    mock_deploy_service: MockDeployService,
) -> None:
    state = WizardState()
    async with ScreenHarness(MainScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        _click_button(pilot.app.screen, "deploy")
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardHostScreen)


# ── WizardHostScreen ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_host_screen_composition(
    mock_deploy_service: MockDeployService,
) -> None:
    state = WizardState()
    async with ScreenHarness(
        WizardHostScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()
        table = pilot.app.screen.query_one("#hosts-table", DataTable)
        columns = [col.label.plain for col in table.columns.values()]
        assert "Host" in columns
        assert "Flake Attribute" in columns
        assert table.row_count >= 1


@pytest.mark.asyncio
async def test_host_screen_row_selected(
    mock_deploy_service: MockDeployService,
) -> None:
    state = WizardState()
    async with ScreenHarness(
        WizardHostScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()
        _select_host(pilot.app.screen)
        await pilot.pause()
        assert state.host_name == "test-host"
        assert state.flake_attr == "test-host"
        assert isinstance(pilot.app.screen, WizardConfigScreen)


# ── WizardConfigScreen ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_wizard_config_composition(
    mock_deploy_service: MockDeployService,
) -> None:
    state = make_wizard_state()
    async with ScreenHarness(
        WizardConfigScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        assert screen.query_one("#host-display", Static)
        assert screen.query_one("#addr-input", Input)
        assert screen.query_one("#mode-select", RadioSet)
        assert screen.query_one("#extra-args-input", Input)
        assert screen.query_one("#validate-deploy", Button)
        assert screen.query_one("#deploy-skip", Button)


@pytest.mark.asyncio
async def test_wizard_config_disko_summary(
    mock_deploy_service: MockDeployService,
) -> None:
    state = make_wizard_state()
    async with ScreenHarness(
        WizardConfigScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()
        await asyncio.sleep(0.1)
        label = pilot.app.screen.query_one("#disko-summary", Static)
        text = label._Static__content
        assert isinstance(text, str)
        assert "Disk:" in text or "Disks:" in text or "No disko devices" in text


@pytest.mark.asyncio
async def test_wizard_config_validate_deploy_all_found(
    mock_deploy_service: MockDeployService,
) -> None:
    state = make_wizard_state(disko_mode="auto")
    mock_deploy_service.ssh_client.partition_exists_results = {
        "disk-main-root": True,
        "disk-main-boot": True,
    }
    mock_deploy_service._nix._results[
        'nixosConfigurations."test-host".config.disko.devices'
    ] = json.dumps({
        "disk": {
            "main": {
                "device": "/dev/sda",
                "content": {
                    "partitions": [{"name": "root"}, {"name": "boot"}],
                },
            },
        },
    })

    async with ScreenHarness(
        WizardConfigScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()
        await asyncio.sleep(0.1)
        _click_button(pilot.app.screen, "validate-deploy")
        screen = pilot.app.screen
        await asyncio.wait_for(screen.validation_done.wait(), timeout=5)
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardConfirmScreen)


@pytest.mark.asyncio
async def test_wizard_config_validate_deploy_missing(
    mock_deploy_service: MockDeployService,
) -> None:
    state = make_wizard_state(disko_mode="auto")
    mock_deploy_service.ssh_client.partition_exists_results = {
        "disk-main-root": False,
        "disk-main-boot": True,
    }
    mock_deploy_service._nix._results[
        'nixosConfigurations."test-host".config.disko.devices'
    ] = json.dumps({
        "disk": {
            "main": {
                "device": "/dev/sda",
                "content": {
                    "partitions": [{"name": "root"}, {"name": "boot"}],
                },
            },
        },
    })

    async with ScreenHarness(
        WizardConfigScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()
        await asyncio.sleep(0.1)
        _click_button(pilot.app.screen, "validate-deploy")
        screen = pilot.app.screen
        await asyncio.wait_for(screen.validation_done.wait(), timeout=5)
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardPartitionScreen)


@pytest.mark.asyncio
async def test_wizard_config_validate_error(
    mock_deploy_service: MockDeployService,
) -> None:
    """When disko eval fails, inner try handles it and pushes deploy screen."""
    state = make_wizard_state(disko_mode="mount", ssh_target="")
    mock_deploy_service._nix._results[
        'nixosConfigurations."test-host".config.disko.devices'
    ] = "not valid json"

    async with ScreenHarness(
        WizardConfigScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()
        await asyncio.sleep(0.1)
        # Set SSH target explicitly (not pre-filled, so auto-advance doesn't trigger)
        pilot.app.screen.query_one("#addr-input", Input).value = "nixos@10.0.0.1"
        _click_button(pilot.app.screen, "validate-deploy")
        screen = pilot.app.screen
        await asyncio.wait_for(screen.validation_done.wait(), timeout=5)
        await pilot.pause()
        # The inner exception handler calls _go_to_deploy — verify transition
        assert isinstance(pilot.app.screen, WizardDeployScreen)


@pytest.mark.asyncio
async def test_wizard_config_skip_deploy(
    mock_deploy_service: MockDeployService,
) -> None:
    state = make_wizard_state()
    async with ScreenHarness(
        WizardConfigScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()
        _click_button(pilot.app.screen, "deploy-skip")
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardDeployScreen)


@pytest.mark.asyncio
async def test_wizard_config_state_collection(
    mock_deploy_service: MockDeployService,
) -> None:
    state = make_wizard_state()
    async with ScreenHarness(
        WizardConfigScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()

        addr_input = pilot.app.screen.query_one("#addr-input", Input)
        addr_input.value = "root@10.0.0.5"
        await pilot.pause()

        _click_button(pilot.app.screen, "deploy-skip")
        await pilot.pause()

        assert state.ssh_target == "root@10.0.0.5"
        assert state.disko_mode in ("mount", "auto", "skip", "create")
        assert state.ssh_key is None or isinstance(state.ssh_key, str)


# ── WizardPartitionScreen ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_wizard_partitions_composition(
    mock_deploy_service: MockDeployService,
) -> None:
    state = make_wizard_state(missing_partlabels=["disk-main-root"])
    async with ScreenHarness(
        WizardPartitionScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()
        table = pilot.app.screen.query_one("#partitions-table", DataTable)
        assert table.row_count == 1


@pytest.mark.asyncio
async def test_wizard_partitions_create_deploy(
    mock_deploy_service: MockDeployService,
) -> None:
    state = make_wizard_state(missing_partlabels=["disk-main-root"])
    mock_deploy_service._nix._results[
        'nixosConfigurations."test-host".config.disko.devices'
    ] = json.dumps({
        "disk": {
            "main": {
                "device": "/dev/sda",
                "content": {
                    "partitions": [{"name": "root"}],
                },
            },
        },
    })

    async with ScreenHarness(
        WizardPartitionScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()
        _click_button(pilot.app.screen, "create-deploy")
        screen = pilot.app.screen
        await asyncio.wait_for(screen.creation_done.wait(), timeout=5)
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardDeployScreen)
        assert len(mock_deploy_service.ssh_client.created_partitions) == 1
        assert mock_deploy_service.ssh_client.created_partitions[0] == (
            "/dev/sda",
            "disk-main-root",
        )


@pytest.mark.asyncio
async def test_wizard_partitions_skip(
    mock_deploy_service: MockDeployService,
) -> None:
    state = make_wizard_state(missing_partlabels=["disk-main-root"])
    async with ScreenHarness(
        WizardPartitionScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()
        _click_button(pilot.app.screen, "skip-deploy")
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardDeployScreen)


# ── WizardDeployScreen ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_wizard_deploy_streaming(
    mock_deploy_service: MockDeployService,
) -> None:
    state = make_wizard_state()
    async with ScreenHarness(
        WizardDeployScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        screen = pilot.app.screen
        await asyncio.wait_for(screen.deploy_done.wait(), timeout=5)
        await pilot.pause()

        log = pilot.app.screen.query_one("#deploy-log", RichLog)
        assert log is not None

        status = pilot.app.screen.query_one("#deploy-status", Static)
        text = status._Static__content.lower()
        assert "successful" in text or "fail" in text

        back = pilot.app.screen.query_one("#back", Button)
        assert not back.disabled

        _click_button(pilot.app.screen, "back")
        await pilot.pause()
        assert len(pilot.app.screen_stack) == 1
