from __future__ import annotations

import asyncio
import json

import pytest
from textual.containers import Vertical
from textual.widgets import Button, DataTable, Input, RadioSet, RichLog, Select, Static

from nixos_deploy_tool.textual_ui.screens.main import MainScreen
from nixos_deploy_tool.textual_ui.screens.wizard_config import WizardConfigScreen
from nixos_deploy_tool.textual_ui.screens.wizard_confirm import WizardConfirmScreen
from nixos_deploy_tool.textual_ui.screens.wizard_deploy import WizardDeployScreen
from nixos_deploy_tool.textual_ui.screens.wizard_disks import WizardDiskScreen
from nixos_deploy_tool.textual_ui.screens.wizard_host import WizardHostScreen
from nixos_deploy_tool.textual_ui.screens.wizard_manual import WizardManualScreen
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
        assert isinstance(pilot.app.screen, WizardDiskScreen)


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
        assert isinstance(pilot.app.screen, WizardDiskScreen)


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


@pytest.mark.asyncio
async def test_wizard_config_manual_route(
    mock_deploy_service: MockDeployService,
) -> None:
    """Selecting 'Configure manually' + validate → pushes manual screen."""
    state = make_wizard_state()
    async with ScreenHarness(
        WizardConfigScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        sel = screen.query_one("#config-source-select", Select)
        sel.value = "manual"
        await pilot.pause()
        assert state.config_source == "manual"
        # Flake-specific widgets hidden
        assert screen.query_one("#disko-flake-group", Vertical).display is False
        assert screen.query_one("#extra-args-input", Input).display is False
        # "coming-soon" no longer shown — manual is now functional
        msg = screen.query_one("#manual-coming-soon", Static)
        assert msg.display is False
        # Click validate → routes to manual screen
        _click_button(screen, "validate-deploy")
        config_screen = pilot.app.screen
        await asyncio.wait_for(config_screen.validation_done.wait(), timeout=5)
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardManualScreen)


@pytest.mark.asyncio
async def test_wizard_config_skip_source(
    mock_deploy_service: MockDeployService,
) -> None:
    """Selecting 'Skip disko' + validate goes straight to deploy."""
    state = make_wizard_state()
    async with ScreenHarness(
        WizardConfigScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        sel = screen.query_one("#config-source-select", Select)
        sel.value = "skip"
        await pilot.pause()
        assert state.config_source == "skip"
        _click_button(screen, "validate-deploy")
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardDeployScreen)


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


# ── WizardDiskScreen ──────────────────────────────────────────────

_MOCK_FLAKE_DISKS = {
    "disk": {
        "main": {
            "device": "/dev/sda",
            "content": {
                "partitions": [{"name": "root"}, {"name": "boot"}],
            },
        },
    },
}


@pytest.mark.asyncio
async def test_wizard_disk_composition(
    mock_deploy_service: MockDeployService,
) -> None:
    """Disk screen renders flake table, target table, and selectors."""
    state = make_wizard_state()
    async with ScreenHarness(
        WizardDiskScreen(mock_deploy_service, state, _MOCK_FLAKE_DISKS)
    ).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        await asyncio.wait_for(screen.disks_loaded.wait(), timeout=5)
        await pilot.pause()
        # Flake disk table populated
        flake_table = screen.query_one("#flake-disks-table", DataTable)
        assert flake_table.row_count == 1
        # Target disk table populated
        target_table = screen.query_one("#target-disks-table", DataTable)
        assert target_table.row_count == 2
        # Selector rendered
        assert screen.query_one("#disk-map-main", Select)
        assert not screen.query_one("#continue", Button).disabled


@pytest.mark.asyncio
async def test_wizard_disk_ssh_failure(
    mock_deploy_service: MockDeployService,
) -> None:
    """When list_disks raises, show error and disable continue."""
    state = make_wizard_state()
    original_list_disks = mock_deploy_service.ssh_client.list_disks

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
        assert "Error probing disks" in status._Static__content
        assert screen.query_one("#continue", Button).disabled
    mock_deploy_service.ssh_client.list_disks = original_list_disks


@pytest.mark.asyncio
async def test_wizard_disk_continue_to_confirm(
    mock_deploy_service: MockDeployService,
) -> None:
    """Select disk + all partitions present → pushes confirm screen."""
    state = make_wizard_state()
    async with ScreenHarness(
        WizardDiskScreen(mock_deploy_service, state, _MOCK_FLAKE_DISKS)
    ).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        await asyncio.wait_for(screen.disks_loaded.wait(), timeout=5)
        await pilot.pause()
        sel = screen.query_one("#disk-map-main", Select)
        sel.value = "/dev/sda"
        await pilot.pause()
        _click_button(screen, "continue")
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardConfirmScreen)
        assert state.disko_disk_overrides == {"main": "/dev/sda"}


@pytest.mark.asyncio
async def test_wizard_disk_continue_to_partitions(
    mock_deploy_service: MockDeployService,
) -> None:
    """Select disk + missing partitions → pushes partition screen."""
    state = make_wizard_state()
    state.missing_partlabels = ["disk-main-root"]
    async with ScreenHarness(
        WizardDiskScreen(mock_deploy_service, state, _MOCK_FLAKE_DISKS)
    ).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        await asyncio.wait_for(screen.disks_loaded.wait(), timeout=5)
        await pilot.pause()
        sel = screen.query_one("#disk-map-main", Select)
        sel.value = "/dev/sda"
        await pilot.pause()
        _click_button(screen, "continue")
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardPartitionScreen)
        assert state.disko_disk_overrides == {"main": "/dev/sda"}


# ── WizardManualScreen ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_wizard_manual_composition(
    mock_deploy_service: MockDeployService,
) -> None:
    """Manual screen renders target disk table with lsblk data."""
    state = make_wizard_state()
    async with ScreenHarness(
        WizardManualScreen(mock_deploy_service, state, _MOCK_FLAKE_DISKS)
    ).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        await asyncio.wait_for(screen.disks_loaded.wait(), timeout=5)
        await pilot.pause()
        assert screen.query_one("#target-disks-table", DataTable).row_count == 2
        assert screen.query_one("#continue", Button).disabled is True


@pytest.mark.asyncio
async def test_wizard_manual_select_disk(
    mock_deploy_service: MockDeployService,
) -> None:
    """Selecting a disk shows planned layout and enables continue."""
    state = make_wizard_state()
    async with ScreenHarness(
        WizardManualScreen(mock_deploy_service, state, _MOCK_FLAKE_DISKS)
    ).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        await asyncio.wait_for(screen.disks_loaded.wait(), timeout=5)
        await pilot.pause()
        # Click a row
        table = screen.query_one("#target-disks-table", DataTable)
        table.move_cursor(row=0, column=0)
        table.action_select_cursor()
        await pilot.pause()
        assert state.manual_disk_selection == "/dev/sda"
        assert not screen.query_one("#continue", Button).disabled
        # Planned layout should show flake partitions
        layout = screen.query_one("#planned-layout", Static)
        assert "root" in layout._Static__content


@pytest.mark.asyncio
async def test_wizard_manual_ssh_failure(
    mock_deploy_service: MockDeployService,
) -> None:
    """When SSH fails, show error and disable continue."""
    state = make_wizard_state()
    original = mock_deploy_service.ssh_client.list_disks

    def raise_error() -> list[dict]:
        raise RuntimeError("Connection refused")

    mock_deploy_service.ssh_client.list_disks = raise_error
    async with ScreenHarness(
        WizardManualScreen(mock_deploy_service, state, _MOCK_FLAKE_DISKS)
    ).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        await asyncio.wait_for(screen.disks_loaded.wait(), timeout=5)
        await pilot.pause()
        assert "Error probing disks" in screen.query_one("#disk-status", Static)._Static__content
        assert screen.query_one("#continue", Button).disabled
    mock_deploy_service.ssh_client.list_disks = original
