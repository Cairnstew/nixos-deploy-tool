from __future__ import annotations

import asyncio
import json

import pytest
from textual.widgets import Button, DataTable

from nixos_deploy_tool.textual_ui.screens.wizard_config import WizardConfigScreen
from nixos_deploy_tool.textual_ui.screens.wizard_confirm import WizardConfirmScreen
from nixos_deploy_tool.textual_ui.screens.wizard_deploy import WizardDeployScreen
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
    """Host → config → validate (missing found) → partition screen → create → deploy."""
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
        assert isinstance(pilot.app.screen, WizardPartitionScreen)

        # Create partitions then deploy
        _click_button(pilot.app.screen, "create-deploy")
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
    """Host → config → validate (all found) → confirm screen → deploy."""
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
    """Pre-filled host + disko_mode + all partitions present → auto to confirm."""
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
        # Auto-advance: host → config → confirm (all partitions present)
        for _ in range(20):
            if isinstance(pilot.app.screen, WizardConfirmScreen):
                break
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
        # Auto-advance: host → config → partitions (missing found)
        # create_partitions=True auto-creates immediately, so we land on deploy
        for _ in range(20):
            if isinstance(pilot.app.screen, WizardDeployScreen):
                break
            await pilot.pause()
        assert isinstance(pilot.app.screen, WizardDeployScreen)
        # The missing partition should have been created
        assert len(svc.ssh_client.created_partitions) == 1
        assert svc.ssh_client.created_partitions[0] == (
            "/dev/sda",
            "disk-main-root",
        )
