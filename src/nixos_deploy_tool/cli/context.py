from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.services.base import BaseService


@dataclass
class AppContext:
    verbose: bool = False
    flake_root: Path | None = None
    config: DeployConfig | None = None
    services: dict[str, BaseService] = field(default_factory=dict)
