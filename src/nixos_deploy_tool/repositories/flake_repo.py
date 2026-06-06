from __future__ import annotations

from pathlib import Path


class FlakeRepo:
    def __init__(self, flake_root: Path) -> None:
        self.flake_root = flake_root

    def discover_hosts(self) -> list[str]:
        return []

    def discover_outputs(self) -> dict[str, list[str]]:
        return {}

    def discover_hardware_configs(self) -> list[str]:
        return []
