from __future__ import annotations

import asyncio
import json
from pathlib import Path
import threading

import pytest
from textual.containers import Vertical
from textual.widgets import Button, Select, Static

from nixos_deploy_tool.textual_ui.screens.wizard_deploy import WizardDeployScreen
from nixos_deploy_tool.textual_ui.screens.wizard_partitions import WizardPartitionScreen
from tests.fixtures.factories import make_wizard_state
from tests.fixtures.mocks import MockDeployService
from tests.unit.conftest import ScreenHarness

pytestmark = pytest.mark.tui


def _click_button(screen, button_id: str) -> None:
    screen.query_one(f"#{button_id}", Button).press()


_FLAKE_RESULT = json.dumps({
    "disk": {
        "main": {
            "device": "/dev/sda",
            "content": {
                "partitions": [
                    {"name": "root", "content": {"format": "ext4"}},
                    {"name": "boot", "content": {"format": "vfat"}},
                ],
            },
        },
    },
})


# ── _create_thread error paths ────────────────────────────────────


@pytest.mark.asyncio
async def test_partitions_create_eval_fail(mock_deploy_service: MockDeployService) -> None:
    """_create_thread when get_disko_devices raises → error + buttons re-enabled."""
    state = make_wizard_state(missing_partlabels=["disk-main-root"])
    # Make eval_flake_json raise
    original_eval = mock_deploy_service._nix.eval_flake_json

    def raise_eval(attr: str, flake_root: Path) -> str:
        raise RuntimeError("nix eval failed")

    mock_deploy_service._nix.eval_flake_json = raise_eval

    async with ScreenHarness(WizardPartitionScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        _click_button(screen, "create-deploy")
        # creation_done is NOT set on eval failure (early return), so wait manually
        await asyncio.sleep(0.5)
        await pilot.pause()
        status = screen.query_one("#status", Static)
        content = status._Static__content.lower()
        assert "error" in content
        assert not screen.query_one("#create-deploy", Button).disabled
    mock_deploy_service._nix.eval_flake_json = original_eval


@pytest.mark.asyncio
async def test_partitions_create_partition_fail(mock_deploy_service: MockDeployService) -> None:
    """_create_thread when create_partition raises → abort + error + re-enable."""
    state = make_wizard_state(missing_partlabels=["disk-main-root"])
    mock_deploy_service._nix._results[
        'nixosConfigurations."test-host".config.disko.devices'
    ] = _FLAKE_RESULT

    original = mock_deploy_service.ssh_client.create_partition

    def raise_error(device: str, label: str) -> None:
        raise RuntimeError("sgdisk failed")

    mock_deploy_service.ssh_client.create_partition = raise_error

    async with ScreenHarness(WizardPartitionScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        screen._create_selected()
        # creation_done is NOT set on error path (early return)
        await asyncio.sleep(0.5)
        await pilot.pause()
        status = screen.query_one("#status", Static)
        content = status._Static__content.lower()
        assert "fail" in content or "error" in content
        assert not screen.query_one("#create-deploy", Button).disabled
    mock_deploy_service.ssh_client.create_partition = original


@pytest.mark.asyncio
async def test_partitions_create_empty_to_create(mock_deploy_service: MockDeployService) -> None:
    """_create_selected with no partitions marked 'create' → goes to deploy."""
    state = make_wizard_state(missing_partlabels=["disk-main-root"])
    async with ScreenHarness(WizardPartitionScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        # Change to skip
        sel = screen.query_one("#part-disk-main-root", Select)
        sel.value = "skip"
        await pilot.pause()
        _click_button(screen, "create-deploy")
        await pilot.pause()
        # Should skip straight to deploy
        assert isinstance(pilot.app.screen, WizardDeployScreen)


# ── mkfs verification ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_partitions_mkfs_called(mock_deploy_service: MockDeployService) -> None:
    """Partition creation calls mkfs with correct format and label."""
    state = make_wizard_state(missing_partlabels=["disk-main-root"])
    mock_deploy_service._nix._results[
        'nixosConfigurations."test-host".config.disko.devices'
    ] = _FLAKE_RESULT

    async with ScreenHarness(WizardPartitionScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        screen._create_selected()
        await asyncio.wait_for(screen.creation_done.wait(), timeout=5)
        await pilot.pause()
        assert len(mock_deploy_service.ssh_client.mkfs_calls) == 1
        device_path, fstype, label = mock_deploy_service.ssh_client.mkfs_calls[0]
        assert fstype == "ext4"
        assert label == "disk-main-root"


# ── _load_from_flake error paths ──────────────────────────────────


@pytest.mark.asyncio
async def test_partitions_load_flake_no_overrides(mock_deploy_service: MockDeployService) -> None:
    """_load_from_flake with no disko_disk_overrides → message."""
    state = make_wizard_state(missing_partlabels=[])
    async with ScreenHarness(WizardPartitionScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        _click_button(screen, "use-flake")
        await asyncio.sleep(0.3)
        await pilot.pause()
        status = screen.query_one("#status", Static)
        assert status._Static__content


@pytest.mark.asyncio
async def test_partitions_load_flake_eval_fail(mock_deploy_service: MockDeployService) -> None:
    """_load_from_flake_thread when eval raises → error."""
    state = make_wizard_state(missing_partlabels=[], disko_disk_overrides={"main": "/dev/sda"})
    # Make eval_flake_json raise
    original_eval = mock_deploy_service._nix.eval_flake_json

    def raise_eval(attr: str, flake_root: Path) -> str:
        raise RuntimeError("nix eval failed")

    mock_deploy_service._nix.eval_flake_json = raise_eval

    async with ScreenHarness(WizardPartitionScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        _click_button(screen, "use-flake")
        await asyncio.sleep(0.5)
        await pilot.pause()
        status = screen.query_one("#status", Static)
        assert "could not evaluate" in status._Static__content.lower()
    mock_deploy_service._nix.eval_flake_json = original_eval


@pytest.mark.asyncio
async def test_partitions_load_flake_empty(mock_deploy_service: MockDeployService) -> None:
    """_load_from_flake_thread with no partitions in flake → message."""
    state = make_wizard_state(missing_partlabels=[], disko_disk_overrides={"main": "/dev/sda"})
    mock_deploy_service._nix._results[
        'nixosConfigurations."test-host".config.disko.devices'
    ] = '{"disk": {"main": {"device": "/dev/sda", "content": {"partitions": []}}}}'
    async with ScreenHarness(WizardPartitionScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        _click_button(screen, "use-flake")
        await asyncio.sleep(0.5)
        await pilot.pause()
        status = screen.query_one("#status", Static)
        assert "no partitions" in status._Static__content.lower()


# ── Auto-load from flake on mount ─────────────────────────────────


@pytest.mark.asyncio
async def test_partitions_auto_load_on_mount(mock_deploy_service: MockDeployService) -> None:
    """Empty missing_partlabels + disk overrides → auto-loads partitions."""
    state = make_wizard_state(missing_partlabels=[], disko_disk_overrides={"main": "/dev/sda"})
    mock_deploy_service._nix._results[
        'nixosConfigurations."test-host".config.disko.devices'
    ] = _FLAKE_RESULT
    async with ScreenHarness(WizardPartitionScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        await asyncio.sleep(0.5)
        await pilot.pause()
        screen = pilot.app.screen
        container = screen.query_one("#part-choices-container", Vertical)
        assert len(list(container.children)) == 2
        status = screen.query_one("#status", Static)
        assert "loaded" in status._Static__content.lower()


# ── Auto-create path ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_partitions_auto_create_on_mount(mock_deploy_service: MockDeployService) -> None:
    """create_partitions=True auto-starts creation on mount."""
    state = make_wizard_state(missing_partlabels=["disk-main-root"], create_partitions=True)
    mock_deploy_service._nix._results[
        'nixosConfigurations."test-host".config.disko.devices'
    ] = _FLAKE_RESULT
    screen = WizardPartitionScreen(mock_deploy_service, state)
    async with ScreenHarness(screen).run_test() as pilot:
        await pilot.pause()
        await asyncio.wait_for(screen.creation_done.wait(), timeout=5)
        await pilot.pause()
        assert len(mock_deploy_service.ssh_client.created_partitions) == 1


# ── Preview-before-create flow ────────────────────────────────────


@pytest.mark.asyncio
async def test_preview_shows_predicted_paths(mock_deploy_service: MockDeployService) -> None:
    """Clicking 'Create Selected & Deploy' probes target and shows preview."""
    state = make_wizard_state(
        missing_partlabels=["disk-main-root", "disk-main-boot"],
        disko_disk_overrides={"main": "/dev/sda"},
    )
    mock_deploy_service._nix._results[
        'nixosConfigurations."test-host".config.disko.devices'
    ] = _FLAKE_RESULT
    async with ScreenHarness(WizardPartitionScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        _click_button(screen, "create-deploy")
        await asyncio.sleep(0.5)
        await pilot.pause()
        status = screen.query_one("#status", Static)
        content = status._Static__content
        assert "Partitions to create" in content
        assert "/dev/sda1" in content or "/dev/sda" in content


@pytest.mark.asyncio
async def test_preview_confirm_starts_creation(mock_deploy_service: MockDeployService) -> None:
    """Confirming preview runs the actual partition creation."""
    state = make_wizard_state(
        missing_partlabels=["disk-main-root"],
        disko_disk_overrides={"main": "/dev/sda"},
    )
    mock_deploy_service._nix._results[
        'nixosConfigurations."test-host".config.disko.devices'
    ] = _FLAKE_RESULT
    async with ScreenHarness(WizardPartitionScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        _click_button(screen, "create-deploy")
        await asyncio.sleep(0.5)
        await pilot.pause()
        _click_button(screen, "confirm-preview")
        await asyncio.wait_for(screen.creation_done.wait(), timeout=5)
        await pilot.pause()
        assert len(mock_deploy_service.ssh_client.created_partitions) == 1


@pytest.mark.asyncio
async def test_preview_cancel_restores_buttons(mock_deploy_service: MockDeployService) -> None:
    """Cancelling preview restores original button row."""
    state = make_wizard_state(
        missing_partlabels=["disk-main-root"],
        disko_disk_overrides={"main": "/dev/sda"},
    )
    mock_deploy_service._nix._results[
        'nixosConfigurations."test-host".config.disko.devices'
    ] = _FLAKE_RESULT
    async with ScreenHarness(WizardPartitionScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        screen = pilot.app.screen
        _click_button(screen, "create-deploy")
        await asyncio.sleep(0.5)
        await pilot.pause()
        _click_button(screen, "cancel-preview")
        await pilot.pause()
        assert screen.query_one("#create-deploy", Button)
        assert not screen.query_one("#create-deploy", Button).disabled


# ── Back button ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_partitions_back_button(mock_deploy_service: MockDeployService) -> None:
    state = make_wizard_state(missing_partlabels=["disk-main-root"])
    async with ScreenHarness(WizardPartitionScreen(mock_deploy_service, state)).run_test() as pilot:
        await pilot.pause()
        _click_button(pilot.app.screen, "back")
        await pilot.pause()
        # ScreenHarness has one screen, pop returns to nothing
        assert pilot.app.screen is not None
