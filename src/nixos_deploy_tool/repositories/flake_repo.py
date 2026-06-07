from __future__ import annotations

from pathlib import Path

from nixos_deploy_tool.core.flake import FlakeIntrospector


class FlakeRepo:
    def __init__(self, flake_root: Path) -> None:
        self.flake_root = flake_root
        self._flake = FlakeIntrospector(flake_root)

    def discover_hosts(self) -> list[str]:
        hosts = self._flake.list_host_configs()
        return [h["name"] for h in hosts]

    def discover_outputs(self) -> dict[str, list[str]]:
        data = self._flake.show_json()
        result: dict[str, list[str]] = {}
        for section, contents in data.items():
            if isinstance(contents, dict):
                result[section] = list(contents.keys())
            else:
                result[section] = [str(contents)]
        return result

    def discover_hardware_configs(self) -> list[str]:
        data = self._flake.show_json()
        configs: list[str] = []
        for key in data.get("nixosConfigurations", {}):
            configs.append(key)
        return configs
