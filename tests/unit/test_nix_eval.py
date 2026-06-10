from __future__ import annotations

import json
from pathlib import Path

import pytest

from nixos_deploy_tool.core.nix import NixRunner
from nixos_deploy_tool.exceptions import NixEvalError

pytestmark = pytest.mark.nix

_FIXTURE_DIR = (
    Path(__file__).resolve().parent.parent / "fixtures" / "test-flakes"
)


@pytest.fixture
def runner() -> NixRunner:
    return NixRunner()


@pytest.fixture
def flake_path() -> Path:
    return _FIXTURE_DIR


# ── basic (list-style partitions) ─────────────────────────────────────────


class TestBasicFlake:
    """Flake: nixosConfigurations.test-host with list-style disko partitions."""

    FLAKE_DIR = _FIXTURE_DIR / "basic"

    def test_eval_returns_disko_devices(self, runner: NixRunner) -> None:
        result = runner.eval_flake_json(
            'nixosConfigurations."test-host".config.disko.devices',
            flake_root=self.FLAKE_DIR,
        )
        data = json.loads(result)
        assert "disk" in data

    def test_disk_main_device(self, runner: NixRunner) -> None:
        result = runner.eval_flake_json(
            'nixosConfigurations."test-host".config.disko.devices',
            flake_root=self.FLAKE_DIR,
        )
        data = json.loads(result)
        assert data["disk"]["main"]["device"] == "/dev/sda"

    def test_disk_main_has_partitions(self, runner: NixRunner) -> None:
        result = runner.eval_flake_json(
            'nixosConfigurations."test-host".config.disko.devices',
            flake_root=self.FLAKE_DIR,
        )
        data = json.loads(result)
        content = data["disk"]["main"]["content"]
        assert content["type"] == "gpt"
        assert len(content["partitions"]) == 1
        assert content["partitions"][0]["name"] == "root"


# ── dict-partitions (attrset-keyed partitions) ─────────────────────────────


class TestDictPartitionsFlake:
    """Flake: nixosConfigurations.test-host with attrset-keyed partitions."""

    FLAKE_DIR = _FIXTURE_DIR / "dict-partitions"

    def test_eval_returns_disko_devices(self, runner: NixRunner) -> None:
        result = runner.eval_flake_json(
            'nixosConfigurations."test-host".config.disko.devices',
            flake_root=self.FLAKE_DIR,
        )
        data = json.loads(result)
        assert "disk" in data

    def test_dict_partitions_convert_to_list(self, runner: NixRunner) -> None:
        """Dict-keyed partitions should be returned by nix as an attrset,
        which Python sees as a dict.  The stripInternal does NOT convert
        dicts to lists — that is done by normalise_partitions() in config.py."""
        result = runner.eval_flake_json(
            'nixosConfigurations."test-host".config.disko.devices',
            flake_root=self.FLAKE_DIR,
        )
        data = json.loads(result)
        # Nix evaluates the attrset — partitions are still an attrset
        partitions = data["disk"]["main"]["content"]["partitions"]
        assert isinstance(partitions, dict)
        assert "root" in partitions
        assert "home" in partitions


# ── no-disko ────────────────────────────────────────────────────────────────


class TestNoDiskoFlake:
    """Flake: nixosConfigurations.no-disko-host without disko.devices."""

    FLAKE_DIR = _FIXTURE_DIR / "no-disko"

    def test_eval_raises_nix_eval_error(self, runner: NixRunner) -> None:
        with pytest.raises(NixEvalError, match="attribute 'disko' missing"):
            runner.eval_flake_json(
                'nixosConfigurations."no-disko-host".config.disko.devices',
                flake_root=self.FLAKE_DIR,
            )


# ── internal-attrs (underscore-prefixed attrs) ────────────────────────────


class TestInternalAttrsFlake:
    """Flake: nixosConfigurations.test-host with _underscore internal attrs."""

    FLAKE_DIR = _FIXTURE_DIR / "internal-attrs"

    def test_eval_returns_disko_devices(self, runner: NixRunner) -> None:
        result = runner.eval_flake_json(
            'nixosConfigurations."test-host".config.disko.devices',
            flake_root=self.FLAKE_DIR,
        )
        data = json.loads(result)
        assert "disk" in data

    def test_internal_attrs_stripped_from_disk(self, runner: NixRunner) -> None:
        """_packages and _config should be removed by stripInternal."""
        result = runner.eval_flake_json(
            'nixosConfigurations."test-host".config.disko.devices',
            flake_root=self.FLAKE_DIR,
        )
        data = json.loads(result)
        disk = data["disk"]["main"]
        assert "_packages" not in disk
        assert "_config" not in disk

    def test_internal_attrs_stripped_from_content(self, runner: NixRunner) -> None:
        """_meta in content should be removed."""
        result = runner.eval_flake_json(
            'nixosConfigurations."test-host".config.disko.devices',
            flake_root=self.FLAKE_DIR,
        )
        data = json.loads(result)
        content = data["disk"]["main"]["content"]
        assert "_meta" not in content

    def test_hidden_attrs_stripped_from_partitions(self, runner: NixRunner) -> None:
        """_hidden on a partition should be removed; non-_ attrs preserved."""
        result = runner.eval_flake_json(
            'nixosConfigurations."test-host".config.disko.devices',
            flake_root=self.FLAKE_DIR,
        )
        data = json.loads(result)
        partitions = data["disk"]["main"]["content"]["partitions"]
        for part in partitions:
            assert "_hidden" not in part
        swap_part = next(p for p in partitions if p["name"] == "swap")
        assert "content" in swap_part

    def test_public_attrs_preserved(self, runner: NixRunner) -> None:
        """Non-underscore attrs like type, device, name, format are kept."""
        result = runner.eval_flake_json(
            'nixosConfigurations."test-host".config.disko.devices',
            flake_root=self.FLAKE_DIR,
        )
        data = json.loads(result)
        disk = data["disk"]["main"]
        assert disk["type"] == "disk"
        assert disk["device"] == "/dev/sda"


# ── empty (no nixosConfigurations) ─────────────────────────────────────────


class TestEmptyFlake:
    """Flake with no nixosConfigurations at all."""

    FLAKE_DIR = _FIXTURE_DIR / "empty"

    def test_eval_raises_nix_eval_error(self, runner: NixRunner) -> None:
        with pytest.raises(NixEvalError, match="attribute 'nixosConfigurations' missing"):
            runner.eval_flake_json(
                'nixosConfigurations."test-host".config.disko.devices',
                flake_root=self.FLAKE_DIR,
            )


# ── wrong host name ────────────────────────────────────────────────────────


class TestWrongHost:
    """Flake with nixosConfigurations but wrong host name."""

    FLAKE_DIR = _FIXTURE_DIR / "basic"

    def test_eval_raises_nix_eval_error(self, runner: NixRunner) -> None:
        with pytest.raises(NixEvalError, match="attribute 'nonexistent' missing"):
            runner.eval_flake_json(
                'nixosConfigurations."nonexistent".config.disko.devices',
                flake_root=self.FLAKE_DIR,
            )
