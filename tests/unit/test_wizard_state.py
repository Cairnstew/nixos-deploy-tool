from __future__ import annotations

import pytest

from nixos_deploy_tool.textual_ui.wizard_state import WizardState


class TestWizardState:
    def test_default_host_name(self) -> None:
        assert WizardState().host_name == ""

    def test_default_flake_attr(self) -> None:
        assert WizardState().flake_attr == ""

    def test_default_ssh_target(self) -> None:
        assert WizardState().ssh_target == ""

    def test_default_ssh_key(self) -> None:
        assert WizardState().ssh_key is None

    def test_default_config_source(self) -> None:
        assert WizardState().config_source == "flake"

    def test_default_disko_mode(self) -> None:
        assert WizardState().disko_mode == "mount"

    def test_default_extra_args(self) -> None:
        assert WizardState().extra_args is None

    def test_default_missing_partlabels(self) -> None:
        assert WizardState().missing_partlabels == []

    def test_default_disko_device_summary(self) -> None:
        assert WizardState().disko_device_summary == ""

    def test_default_create_partitions(self) -> None:
        assert WizardState().create_partitions is False

    def test_default_disko_disk_overrides(self) -> None:
        assert WizardState().disko_disk_overrides == {}

    def test_default_manual_disk_selection(self) -> None:
        assert WizardState().manual_disk_selection == ""

    def test_fields_are_independent(self) -> None:
        s1 = WizardState(host_name="a", missing_partlabels=["x"])
        s2 = WizardState(host_name="b")
        assert s1.host_name == "a"
        assert s1.missing_partlabels == ["x"]
        assert s2.host_name == "b"
        assert s2.missing_partlabels == []

    def test_missing_partlabels_mutable(self) -> None:
        s = WizardState()
        s.missing_partlabels.append("disk-main-root")
        assert s.missing_partlabels == ["disk-main-root"]

    def test_disko_disk_overrides_mutable(self) -> None:
        s = WizardState()
        s.disko_disk_overrides["main"] = "/dev/sda"
        assert s.disko_disk_overrides == {"main": "/dev/sda"}
