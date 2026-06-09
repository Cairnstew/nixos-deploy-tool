from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Any, cast


class FlakeIntrospector:
    def __init__(self, flake_root: Path) -> None:
        self.flake_root = flake_root
        self._logger = logging.getLogger(self.__class__.__name__)

    def show_json(self) -> dict[str, Any]:
        cmd = ["nix", "flake", "show", "--json", str(self.flake_root)]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"`{' '.join(cmd)}` failed (exit {result.returncode})"
            )
        return cast("dict[str, Any]", json.loads(result.stdout))

    def list_iso_configs(self) -> list[dict[str, object]]:
        data = self.show_json()
        outputs: list[dict[str, object]] = []
        for key, val in data.get("packages", {}).items():
            if "iso" in key.lower():
                outputs.append({"name": key, "attr": key})
        return outputs

    def list_host_configs(self) -> list[dict[str, str]]:
        data = self.show_json()
        hosts: list[dict[str, str]] = []
        for key in data.get("nixosConfigurations", {}):
            hosts.append({"name": key, "attr": key})
        return hosts

    def discover_hosts(self) -> list[str]:
        """Return flat list of host names (convenience wrapper)."""
        return [h["name"] for h in self.list_host_configs()]
