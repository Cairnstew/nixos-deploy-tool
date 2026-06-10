from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Any

from nixos_deploy_tool.exceptions import SecretError
from nixos_deploy_tool.repositories._base import BaseRepository


class AgenixCatalog(BaseRepository):
    def __init__(self, flake_root: Path, secrets_dir: str = "secrets") -> None:
        self.flake_root = flake_root
        self.secrets_dir = flake_root / secrets_dir
        self._logger = logging.getLogger(__name__)

    def list_age_files(self) -> list[Path]:
        if not self.secrets_dir.is_dir():
            return []
        return sorted(self.secrets_dir.rglob("*.age"))

    def list(self) -> list[dict[str, Any]]:
        return [{"name": f.name, "path": str(f)} for f in self.list_age_files()]

    def get(self, key: str) -> dict[str, Any] | None:
        for f in self.list_age_files():
            if f.name == key:
                return {"name": f.name, "path": str(f)}
        return None

    def parse_secrets_nix(self) -> dict[str, object]:
        secrets_nix = self.flake_root / "secrets.nix"
        if not secrets_nix.is_file():
            return {}
        try:
            result = subprocess.run(
                ["nix", "eval", "--json", "--file", str(secrets_nix)],
                capture_output=True,
                text=True,
                check=True,
            )
            data = json.loads(result.stdout)
            if isinstance(data, dict):
                return data
            return {}
        except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError) as exc:
            msg = f"Failed to evaluate {secrets_nix}: {exc}"
            raise SecretError(msg) from exc
