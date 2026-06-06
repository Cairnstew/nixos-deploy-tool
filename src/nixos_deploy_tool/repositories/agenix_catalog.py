from __future__ import annotations

from pathlib import Path


class AgenixCatalog:
    def __init__(self, flake_root: Path) -> None:
        self.flake_root = flake_root

    def list_age_files(self) -> list[Path]:
        return []

    def parse_secrets_nix(self) -> dict[str, object]:
        return {}
