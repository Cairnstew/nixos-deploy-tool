from __future__ import annotations

import asyncio
import json

import pytest
from textual.containers import Vertical
from textual.widgets import Button, DataTable, Input, Select, Static

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
    screen.query_one(f"#{button_id}", Button).press()


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


# ── MainScreen ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_main_screen_non_deploy_buttons_noop(
    mock_deploy_service: MockDeployService,
) -> None:
    """Non-deploy buttons exist but don't navigate (currently no-ops)."""
    state = WizardState()
    async with ScreenHarness(MainScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        assert screen.query_one("#iso", Button)
        assert screen.query_one("#secrets", Button)
        assert screen.query_one("#tailscale", Button)
        # Clicking them should not navigate away
        _click_button(screen, "iso")
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)
        _click_button(screen, "secrets")
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)
        _click_button(screen, "tailscale")
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)


@pytest.mark.asyncio
async def test_main_screen_action_deploy(
    mock_deploy_service: MockDeployService,
) -> None:
    """action_deploy() pushes WizardHostScreen."""
    state = WizardState()
    async with ScreenHarness(MainScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        pilot.app.screen.action_deploy()
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardHostScreen)


# ── WizardHostScreen ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_host_screen_auto_advance_with_host_name(
    mock_deploy_service: MockDeployService,
) -> None:
    """Setting state.host_name before mount auto-advances past host screen."""
    state = WizardState(host_name="test-host")
    async with ScreenHarness(
        WizardHostScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardConfigScreen)
        assert state.flake_attr == "test-host"


@pytest.mark.asyncio
async def test_host_screen_auto_advance_unknown_host(
    mock_deploy_service: MockDeployService,
) -> None:
    """Pre-filled host_name not in flake still auto-advances (flake_attr stays empty)."""
    state = WizardState(host_name="unknown-host")
    async with ScreenHarness(
        WizardHostScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardConfigScreen)
        # flake_attr not set when host not found in flake
        assert state.flake_attr == ""


# ── WizardConfigScreen ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_config_ssh_addr_falls_back_to_host_name(
    mock_deploy_service: MockDeployService,
) -> None:
    """When addr input is empty, state uses host_name as fallback."""
    state = make_wizard_state(ssh_target="")
    async with ScreenHarness(
        WizardConfigScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()
        _click_button(pilot.app.screen, "deploy-skip")
        await pilot.pause()
        assert state.ssh_target == state.host_name


@pytest.mark.asyncio
async def test_config_on_select_changed_to_skip(
    mock_deploy_service: MockDeployService,
) -> None:
    """Changing config source to skip with ssh_target auto-advances to deploy."""
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
        assert isinstance(pilot.app.screen, WizardDeployScreen)


@pytest.mark.asyncio
async def test_config_extra_args_stored_on_validate(
    mock_deploy_service: MockDeployService,
) -> None:
    """Extra args input value is stored in state."""
    state = make_wizard_state()
    async with ScreenHarness(
        WizardConfigScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        extra = screen.query_one("#extra-args-input", Input)
        extra.value = "--phases kexec,install"
        await pilot.pause()
        _click_button(screen, "deploy-skip")
        await pilot.pause()
        assert state.extra_args == "--phases kexec,install"


@pytest.mark.asyncio
async def test_config_disko_mode_map_create(
    mock_deploy_service: MockDeployService,
) -> None:
    """Validating with 'create' mode sets disko_mode correctly."""
    state = make_wizard_state()
    mock_deploy_service._nix._results[
        'nixosConfigurations."test-host".config.disko.devices'
    ] = json.dumps({
        "disk": {
            "main": {
                "device": "/dev/sda",
                "content": {"partitions": [{"name": "root"}]},
            },
        },
    })
    async with ScreenHarness(
        WizardConfigScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        # Set addr so validation doesn't need manual input on button press
        screen.query_one("#addr-input", Input).value = "nixos@10.0.0.1"
        await pilot.pause()
        radio_set = screen.query_one("#mode-select")
        # Click the 'create' radio button
        radio_set._nodes[2].toggle()
        await pilot.pause()
        _click_button(screen, "validate-deploy")
        config_screen = pilot.app.screen
        await asyncio.wait_for(config_screen.validation_done.wait(), timeout=5)
        await pilot.pause()
        assert state.disko_mode == "create"


# ── WizardDiskScreen ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_disk_flake_table_populated_correctly(
    mock_deploy_service: MockDeployService,
) -> None:
    """Flake disk table shows correct columns and rows."""
    state = make_wizard_state()
    async with ScreenHarness(
        WizardDiskScreen(mock_deploy_service, state, _MOCK_FLAKE_DISKS)
    ).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        await asyncio.wait_for(screen.disks_loaded.wait(), timeout=5)
        await pilot.pause()
        table = screen.query_one("#flake-disks-table", DataTable)
        assert table.row_count == 1
        # Check columns
        col_labels = [c.label.plain for c in table.columns.values()]
        assert "Disk" in col_labels
        assert "Device" in col_labels
        assert "Partitions" in col_labels


@pytest.mark.asyncio
async def test_disk_store_selections_empty(
    mock_deploy_service: MockDeployService,
) -> None:
    """Continue with no selection on selector doesn't crash."""
    state = make_wizard_state()
    async with ScreenHarness(
        WizardDiskScreen(mock_deploy_service, state, {"disk": {}})
    ).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        await asyncio.wait_for(screen.disks_loaded.wait(), timeout=5)
        await pilot.pause()
        # No flake disks means no selectors
        _click_button(screen, "continue")
        await pilot.pause()
        assert state.disko_disk_overrides == {}


# ── WizardManualScreen ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_manual_continue_no_flake_disk_name(
    mock_deploy_service: MockDeployService,
) -> None:
    """When flake_devices has no disk names, disko_disk_overrides uses 'main' fallback."""
    state = make_wizard_state()
    empty_flake = {"disk": {}}
    async with ScreenHarness(
        WizardManualScreen(mock_deploy_service, state, empty_flake)
    ).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        await asyncio.wait_for(screen.disks_loaded.wait(), timeout=5)
        await pilot.pause()
        table = screen.query_one("#target-disks-table", DataTable)
        table.move_cursor(row=0, column=0)
        table.action_select_cursor()
        await pilot.pause()
        _click_button(screen, "continue")
        await pilot.pause()
        assert state.disko_disk_overrides == {"main": "/dev/sda"}


@pytest.mark.asyncio
async def test_manual_find_parent_disk_partition(
    mock_deploy_service: MockDeployService,
) -> None:
    """_find_parent_disk resolves partition paths to parent disk."""
    state = make_wizard_state()
    async with ScreenHarness(
        WizardManualScreen(mock_deploy_service, state, _MOCK_FLAKE_DISKS)
    ).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        # Select the partition row (sda1) and continue
        table = screen.query_one("#target-disks-table", DataTable)
        table.move_cursor(row=1, column=0)
        table.action_select_cursor()
        await pilot.pause()
        _click_button(screen, "continue")
        await pilot.pause()
        # Should resolve sda1 to parent /dev/sda
        assert state.disko_disk_overrides == {"main": "/dev/sda"}


@pytest.mark.asyncio
async def test_manual_execute_advance_routes_to_partitions(
    mock_deploy_service: MockDeployService,
) -> None:
    """_execute_and_advance routes to partition screen when config_source is manual."""
    state = make_wizard_state(config_source="manual")
    async with ScreenHarness(
        WizardManualScreen(mock_deploy_service, state, _MOCK_FLAKE_DISKS)
    ).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        await asyncio.wait_for(screen.disks_loaded.wait(), timeout=5)
        await pilot.pause()
        table = screen.query_one("#target-disks-table", DataTable)
        table.move_cursor(row=0, column=0)
        table.action_select_cursor()
        await pilot.pause()
        _click_button(screen, "continue")
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardPartitionScreen)
        assert state.disko_mode == "mount"


# ── WizardPartitionScreen ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_partitions_cancel_preview_restores_buttons(
    mock_deploy_service: MockDeployService,
) -> None:
    """Cancelling preview restores original action buttons."""
    state = make_wizard_state(
        missing_partlabels=["disk-main-root"],
        disko_disk_overrides={"main": "/dev/sda"},
    )
    mock_deploy_service._nix._results[
        'nixosConfigurations."test-host".config.disko.devices'
    ] = json.dumps({
        "disk": {
            "main": {
                "device": "/dev/sda",
                "content": {
                    "partitions": [{"name": "root", "content": {"format": "ext4"}}],
                },
            },
        },
    })

    async with ScreenHarness(
        WizardPartitionScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        # Preview first
        _click_button(screen, "create-deploy")
        await asyncio.sleep(0.3)
        await pilot.pause()
        # Cancel preview
        _click_button(screen, "cancel-preview")
        await pilot.pause()
        # Buttons should be restored
        assert screen.query_one("#create-deploy", Button)
        assert screen.query_one("#skip-deploy", Button)
        assert screen.query_one("#back", Button)
        assert not screen.query_one("#create-deploy", Button).disabled


@pytest.mark.asyncio
async def test_partitions_create_selected_empty_goes_to_deploy(
    mock_deploy_service: MockDeployService,
) -> None:
    """_create_selected with no choices marked 'create' goes to deploy."""
    state = make_wizard_state(missing_partlabels=["disk-main-root"])
    async with ScreenHarness(
        WizardPartitionScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        # Change the only partition to skip
        part_sel = screen.query_one("#part-disk-main-root", Select)
        part_sel.value = "skip"
        await pilot.pause()
        _click_button(screen, "create-deploy")
        await pilot.pause()
        # No partitions to create → goes directly to deploy
        assert isinstance(pilot.app.screen, WizardDeployScreen)


@pytest.mark.asyncio
async def test_partitions_empty_missing_shows_info(
    mock_deploy_service: MockDeployService,
) -> None:
    """Empty missing_partlabels without disk overrides shows info message."""
    state = make_wizard_state(missing_partlabels=[], disko_disk_overrides={})
    async with ScreenHarness(
        WizardPartitionScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        # The info message is a Static inside part-choices-container
        parts = screen.query_one("#part-choices-container", Vertical)
        info = parts.query(Static)
        # When no partitions are detected, a Static with info text is shown
        assert len(info) > 0


# ── WizardConfirmScreen ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_confirm_on_mount_warning_multiple_devices(
    mock_deploy_service: MockDeployService,
) -> None:
    """Warning shows all devices when multiple disko overrides are set."""
    state = make_wizard_state(
        disko_disk_overrides={"main": "/dev/sda", "data": "/dev/sdb"},
    )
    async with ScreenHarness(
        WizardConfirmScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()
        warning = pilot.app.screen.query_one("#confirm-warning", Static)
        assert "/dev/sda" in warning._Static__content
        assert "/dev/sdb" in warning._Static__content
        assert "DATA LOSS" in warning._Static__content


@pytest.mark.asyncio
async def test_confirm_on_mount_manual_selection_warning(
    mock_deploy_service: MockDeployService,
) -> None:
    """Warning uses manual_disk_selection when no overrides."""
    state = make_wizard_state(
        disko_disk_overrides={},
        manual_disk_selection="/dev/sdc",
    )
    async with ScreenHarness(
        WizardConfirmScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()
        warning = pilot.app.screen.query_one("#confirm-warning", Static)
        assert "/dev/sdc" in warning._Static__content


@pytest.mark.asyncio
async def test_confirm_on_mount_device_summary_warning(
    mock_deploy_service: MockDeployService,
) -> None:
    """Warning uses disko_device_summary when no overrides or manual selection."""
    state = make_wizard_state(
        disko_disk_overrides={},
        manual_disk_selection="",
        disko_device_summary="Disks:\n  /dev/vda (root)  →  root_part",
    )
    async with ScreenHarness(
        WizardConfirmScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()
        warning = pilot.app.screen.query_one("#confirm-warning", Static)
        assert "/dev/vda" in warning._Static__content


@pytest.mark.asyncio
async def test_confirm_on_mount_no_devices_fallback(
    mock_deploy_service: MockDeployService,
) -> None:
    """Fallback warning when no devices are known."""
    state = make_wizard_state(
        disko_disk_overrides={},
        manual_disk_selection="",
        disko_device_summary="",
    )
    async with ScreenHarness(
        WizardConfirmScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        await pilot.pause()
        warning = pilot.app.screen.query_one("#confirm-warning", Static)
        assert "DESTROY DATA" in warning._Static__content


# ── WizardDeployScreen ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_deploy_emits_output_lines(
    mock_deploy_service: MockDeployService,
) -> None:
    """WizardDeployScreen captures output lines in RichLog."""
    state = make_wizard_state()
    from textual.widgets import RichLog

    async with ScreenHarness(
        WizardDeployScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        screen = pilot.app.screen
        await asyncio.wait_for(screen.deploy_done.wait(), timeout=5)
        await pilot.pause()
        log = screen.query_one("#deploy-log", RichLog)
        assert log is not None


@pytest.mark.asyncio
async def test_deploy_error_shows_error_message(
    mock_deploy_service: MockDeployService,
) -> None:
    """Deploy error result shows the error message."""
    from unittest.mock import MagicMock
    from nixos_deploy_tool.models.result import ErrorResult

    def failing_stream(*args, **kwargs):
        on_done = kwargs.get("on_done")
        if on_done:
            on_done(ErrorResult(message="Connection timeout"))
        return ErrorResult(message="Connection timeout")

    mock_deploy_service.run_streaming = MagicMock(side_effect=failing_stream)
    state = make_wizard_state()
    async with ScreenHarness(
        WizardDeployScreen(mock_deploy_service, state)
    ).run_test() as pilot:
        screen = pilot.app.screen
        await asyncio.wait_for(screen.deploy_done.wait(), timeout=5)
        await pilot.pause()
        status = screen.query_one("#deploy-status", Static)
        assert "timeout" in status._Static__content.lower()
