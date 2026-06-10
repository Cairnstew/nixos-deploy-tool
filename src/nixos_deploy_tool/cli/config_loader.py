from __future__ import annotations

import os
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from nixos_deploy_tool.models.config import DeployConfig

CONFIG_FILE_ENV_VAR = "NIXOS_DEPLOY_CONFIG"
DEFAULT_CONFIG_DIR = "~/.config/nixos-deploy"
DEFAULT_CONFIG_FILENAME = "config.yaml"


def _resolve_config_path() -> Path | None:
    env_path = os.environ.get(CONFIG_FILE_ENV_VAR)
    if env_path:
        return Path(env_path).expanduser().resolve()
    default = Path(DEFAULT_CONFIG_DIR).expanduser() / DEFAULT_CONFIG_FILENAME
    if default.exists():
        return default.resolve()
    return None


def load_config() -> DeployConfig:
    config_path = _resolve_config_path()
    if config_path is None:
        return DeployConfig()
    raw = yaml.safe_load(config_path.read_text())
    if not isinstance(raw, dict):
        return DeployConfig()
    return DeployConfig(**raw)
