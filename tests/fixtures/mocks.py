from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from nixos_deploy_tool.core._base import SubprocessRunner
from nixos_deploy_tool.core.flake import FlakeIntrospector
from nixos_deploy_tool.core.nix import NixRunner
from nixos_deploy_tool.services.deploy import DeployService
from fixtures.factories import make_deploy_config


class MockNixRunner(NixRunner):
    """NixRunner that returns canned data instead of shelling out to nix.

    Register results by attribute path::

        runner = MockNixRunner()
        runner._results['nixosConfigurations."test".config.disko.devices'] = '{"disk": {}}'
    """

    def __init__(self) -> None:
        super().__init__()
        self._results: dict[str, str] = {}

    def eval_flake_json(self, attr: str, flake_root: Path) -> str:
        return self._results.get(attr, "{}")


class MockFlakeIntrospector(FlakeIntrospector):
    """FlakeIntrospector with configurable host/ISO lists — no real nix call."""

    def __init__(self, hosts: list[dict[str, str]] | None = None) -> None:
        self._hosts = hosts or [{"name": "test-host", "attr": "test-host"}]
        self.flake_root = Path("/fake/project")

    def show_json(self) -> dict:
        return {
            "nixosConfigurations": {h["name"]: {"type": "nixosConfiguration"} for h in self._hosts},
            "packages": {"iso-test": {"type": "package"}},
        }

    def list_host_configs(self) -> list[dict[str, str]]:
        return self._hosts

    def list_iso_configs(self) -> list[dict[str, object]]:
        return [{"name": "iso-test", "attr": "iso-test"}]

    def discover_hosts(self) -> list[str]:
        return [h["name"] for h in self._hosts]


class MockSubprocessRunner(SubprocessRunner):
    """Concrete SubprocessRunner for testing the base infrastructure.

    Usage::

        runner = MockSubprocessRunner()
        output = runner._run(["--version"])
    """

    def __init__(self, binary: str = "mock-tool") -> None:
        super().__init__(binary)

    def _wrap_error(self, exc: subprocess.CalledProcessError) -> Exception:  # type: ignore[name-defined]
        import subprocess

        return RuntimeError(f"mock tool failed: {exc.stderr}")


class MockDeployService(DeployService):
    """DeployService with all core dependencies replaced by mocks.

    Useful in TUI tests where the screen needs a real DeployService
    but must never actually run nix, ssh, or nixos-anywhere.
    """

    def __init__(self, config=None) -> None:
        cfg = config or make_deploy_config()
        super().__init__(
            config=cfg,
            nixos_anywhere=MagicMock(),
            flake=MockFlakeIntrospector(),
            nix_runner=MockNixRunner(),
            key_store=MagicMock(),
        )
