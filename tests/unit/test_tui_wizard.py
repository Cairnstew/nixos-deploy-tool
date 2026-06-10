from __future__ import annotations

import asyncio
import json

import pytest
from textual.widgets import Button, DataTable, Select, Static

from nixos_deploy_tool.textual_ui.screens.wizard_config import WizardConfigScreen
from nixos_deploy_tool.textual_ui.screens.wizard_confirm import WizardConfirmScreen
from nixos_deploy_tool.textual_ui.screens.wizard_deploy import WizardDeployScreen
from nixos_deploy_tool.textual_ui.screens.wizard_disks import WizardDiskScreen
from nixos_deploy_tool.textual_ui.screens.wizard_manual import WizardManualScreen
from nixos_deploy_tool.textual_ui.screens.wizard_partitions import (
    WizardPartitionScreen,
)

pytestmark = pytest.mark.tui


def _click_button(screen, button_id: str) -> None:
    screen.query_one(f"#{button_id}", Button).press()


def _select_host(screen) -> None:
    table = screen.query_one("#hosts-table", DataTable)
    table.move_cursor(row=0, column=0)
    table.action_select_cursor()


def _select_first_disk(screen) -> None:
    select = screen.query_one("#disk-map-main", Select)
    select.value = "/dev/sda"
    _click_button(screen, "continue")


@pytest.mark.asyncio
async def test_full_wizard_skip_validation(tui_app_async) -> None:
    """Host screen → config screen → skip → deploy screen → back clears stack."""
    async with tui_app_async.run_test(size=(100, 50)) as pilot:
        await pilot.pause()
        assert pilot.app.screen.query_one("#hosts-table", DataTable).row_count >= 1

        _select_host(pilot.app.screen)
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardConfigScreen)

        _click_button(pilot.app.screen, "deploy-skip")
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardDeployScreen)

        deploy_screen = pilot.app.screen
        await asyncio.wait_for(deploy_screen.deploy_done.wait(), timeout=5)
        await pilot.pause()

        back = pilot.app.screen.query_one("#back", Button)
        assert not back.disabled

        _click_button(pilot.app.screen, "back")
        await pilot.pause()
        assert len(pilot.app.screen_stack) == 1


@pytest.mark.asyncio
async def test_full_wizard_validation_missing_partitions(tui_app_async) -> None:
    """Host → config → validate → disk screen → partition screen → create → deploy."""
    async with tui_app_async.run_test(size=(100, 50)) as pilot:
        await pilot.pause()
        _select_host(pilot.app.screen)
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardConfigScreen)

        svc = pilot.app._svc
        svc.ssh_client.partition_exists_results = {
            "disk-main-root": False,
            "disk-main-boot": True,
        }
        svc._nix._results[
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

        _click_button(pilot.app.screen, "validate-deploy")
        config_screen = pilot.app.screen
        await asyncio.wait_for(config_screen.validation_done.wait(), timeout=5)
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardDiskScreen)

        # Select target disk and continue
        disk_screen = pilot.app.screen
        await asyncio.wait_for(disk_screen.disks_loaded.wait(), timeout=5)
        await pilot.pause()
        _select_first_disk(pilot.app.screen)
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardPartitionScreen)

        # Preview → confirm → create partitions
        _click_button(pilot.app.screen, "create-deploy")
        await asyncio.sleep(0.5)
        await pilot.pause()
        _click_button(pilot.app.screen, "confirm-preview")
        part_screen = pilot.app.screen
        await asyncio.wait_for(part_screen.creation_done.wait(), timeout=5)
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardDeployScreen)
        assert len(svc.ssh_client.created_partitions) == 1
        assert svc.ssh_client.created_partitions[0] == (
            "/dev/sda",
            "disk-main-root",
        )


@pytest.mark.asyncio
async def test_full_wizard_validation_all_present(tui_app_async) -> None:
    """Host → config → validate → disk screen → confirm screen → deploy."""
    async with tui_app_async.run_test(size=(100, 50)) as pilot:
        await pilot.pause()
        _select_host(pilot.app.screen)
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardConfigScreen)

        svc = pilot.app._svc
        svc.ssh_client.partition_exists_results = {
            "disk-main-root": True,
            "disk-main-boot": True,
        }
        svc._nix._results[
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

        _click_button(pilot.app.screen, "validate-deploy")
        config_screen = pilot.app.screen
        await asyncio.wait_for(config_screen.validation_done.wait(), timeout=5)
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardDiskScreen)

        # Select target disk and continue
        disk_screen = pilot.app.screen
        await asyncio.wait_for(disk_screen.disks_loaded.wait(), timeout=5)
        await pilot.pause()
        _select_first_disk(pilot.app.screen)
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardConfirmScreen)


@pytest.mark.asyncio
async def test_wizard_cli_host_prefilled(tui_app_async) -> None:
    """Pre-filled host_name should auto-advance past WizardHostScreen."""
    tui_app_async._state.host_name = "test-host"
    async with tui_app_async.run_test(size=(100, 50)) as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardConfigScreen)
        assert pilot.app._state.host_name == "test-host"


@pytest.mark.asyncio
async def test_wizard_cli_full_auto_flow_all_present(tui_app_async) -> None:
    """Pre-filled host + disko_mode + all partitions present → auto to disk screen → confirm."""
    app = tui_app_async
    app._state.host_name = "test-host"
    app._state.ssh_target = "nixos@10.0.0.1"
    app._state.disko_mode = "create"
    svc = app._svc
    svc.ssh_client.partition_exists_results = {
        "disk-main-root": True,
        "disk-main-boot": True,
    }
    svc._nix._results[
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

    async with app.run_test(size=(100, 50)) as pilot:
        await pilot.pause()
        # Auto-advance: host → config → disk screen
        for _ in range(20):
            if isinstance(pilot.app.screen, WizardDiskScreen):
                break
            await pilot.pause()
        assert isinstance(pilot.app.screen, WizardDiskScreen)
        # The disk screen doesn't auto-advance — select a disk and continue
        disk_screen = pilot.app.screen
        await asyncio.wait_for(disk_screen.disks_loaded.wait(), timeout=5)
        await pilot.pause()
        _select_first_disk(pilot.app.screen)
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardConfirmScreen)


@pytest.mark.asyncio
async def test_wizard_cli_full_auto_create_partitions(tui_app_async) -> None:
    """Pre-filled host + disko_mode + create_partitions → auto create + deploy."""
    app = tui_app_async
    app._state.host_name = "test-host"
    app._state.ssh_target = "nixos@10.0.0.1"
    app._state.disko_mode = "create"
    app._state.create_partitions = True
    svc = app._svc
    svc.ssh_client.partition_exists_results = {
        "disk-main-root": False,
        "disk-main-boot": True,
    }
    svc._nix._results[
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

    async with app.run_test(size=(100, 50)) as pilot:
        await pilot.pause()
        # Auto-advance: host → config → disk screen
        for _ in range(20):
            if isinstance(pilot.app.screen, WizardDiskScreen):
                break
            await pilot.pause()
        assert isinstance(pilot.app.screen, WizardDiskScreen)
        # Select a disk and continue → partitions auto-create → deploy
        disk_screen = pilot.app.screen
        await asyncio.wait_for(disk_screen.disks_loaded.wait(), timeout=5)
        await pilot.pause()
        _select_first_disk(pilot.app.screen)
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardDeployScreen)
        # The missing partition should have been created
        assert len(svc.ssh_client.created_partitions) == 1
        assert svc.ssh_client.created_partitions[0] == (
            "/dev/sda",
            "disk-main-root",
        )


@pytest.mark.asyncio
async def test_full_wizard_manual_route_create_partitions(tui_app_async) -> None:
    """Manual route: host → config (manual) → manual screen → select disk → partition screen → create → deploy."""
    app = tui_app_async
    svc = app._svc
    svc.ssh_client.partition_exists_results = {
        "disk-main-root": False,
    }
    svc._nix._results[
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

    async with app.run_test(size=(100, 50)) as pilot:
        await pilot.pause()
        _select_host(pilot.app.screen)
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardConfigScreen)

        # Switch to manual source
        config_screen = pilot.app.screen
        sel = config_screen.query_one("#config-source-select", Select)
        sel.value = "manual"
        await pilot.pause()

        # Validate → manual screen
        _click_button(pilot.app.screen, "validate-deploy")
        await asyncio.wait_for(config_screen.validation_done.wait(), timeout=5)
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardManualScreen)

        # Select a disk
        manual_screen = pilot.app.screen
        await asyncio.wait_for(manual_screen.disks_loaded.wait(), timeout=5)
        await pilot.pause()
        table = manual_screen.query_one("#target-disks-table", DataTable)
        table.move_cursor(row=0, column=0)
        table.action_select_cursor()
        await pilot.pause()
        assert pilot.app._state.manual_disk_selection == "/dev/sda"

        # Continue → partition screen (manual always routes here)
        _click_button(pilot.app.screen, "continue")
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardPartitionScreen)

        # Preview → confirm → create
        _click_button(pilot.app.screen, "create-deploy")
        await asyncio.sleep(0.5)
        await pilot.pause()
        _click_button(pilot.app.screen, "confirm-preview")
        part_screen = pilot.app.screen
        await asyncio.wait_for(part_screen.creation_done.wait(), timeout=5)
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardDeployScreen)
        assert len(svc.ssh_client.created_partitions) == 1


@pytest.mark.asyncio
async def test_full_wizard_deploy_failure(tui_app_async) -> None:
    """Full wizard where deploy returns failure → error message shown."""
    app = tui_app_async
    svc = app._svc

    # Make run_streaming return a failure
    from unittest.mock import MagicMock
    from nixos_deploy_tool.models.result import ErrorResult

    def failing_stream(*args, **kwargs):
        on_done = kwargs.get("on_done")
        if on_done:
            on_done(ErrorResult(message="Deploy failed: kaboom"))
        return ErrorResult(message="Deploy failed: kaboom")

    svc.run_streaming = MagicMock(side_effect=failing_stream)

    async with app.run_test(size=(100, 50)) as pilot:
        await pilot.pause()
        _select_host(pilot.app.screen)
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardConfigScreen)

        # Skip validation and go straight to deploy
        _click_button(pilot.app.screen, "deploy-skip")
        await pilot.pause()
        assert isinstance(pilot.app.screen, WizardDeployScreen)

        # Wait for deploy to complete
        deploy_screen = pilot.app.screen
        await asyncio.wait_for(deploy_screen.deploy_done.wait(), timeout=5)
        await pilot.pause()

        # Error should be shown
        status = pilot.app.screen.query_one("#deploy-status", Static)
        assert "fail" in status._Static__content.lower()
        # Back button should be enabled
        assert not pilot.app.screen.query_one("#back", Button).disabled
