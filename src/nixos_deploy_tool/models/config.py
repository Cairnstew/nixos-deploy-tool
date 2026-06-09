from __future__ import annotations

from pathlib import Path

import pydantic


class ISOConfig(pydantic.BaseModel):
    name: str
    flake_attr: str = ""
    system: str = "x86_64-linux"


class HostConfig(pydantic.BaseModel):
    name: str
    flake_attr: str = ""
    system: str = "x86_64-linux"


class TailscaleOAuthConfig(pydantic.BaseModel):
    client_id: str = ""
    client_secret_file: str = ""


class TailscaleConfig(pydantic.BaseModel):
    oauth: TailscaleOAuthConfig = pydantic.Field(default_factory=TailscaleOAuthConfig)


class ToolPaths(pydantic.BaseModel):
    age_bin: str = ""
    agenix_manager_bin: str = ""
    nixos_anywhere_bin: str = ""
    tailscale_bin: str = ""


class DeployConfig(pydantic.BaseModel):
    flake_root: str = ""
    log_level: str = "info"
    log_file: str = ""
    live_iso_user: str = "nixos"
    tailscale: TailscaleConfig = pydantic.Field(default_factory=TailscaleConfig)
    paths: ToolPaths = pydantic.Field(default_factory=ToolPaths)
    secrets_dir: str = "secrets"
    ssh_key_path: str | None = None
    default_extra_args: list[str] = pydantic.Field(default_factory=list)
    skip_disko: bool = False
    disko_mode: str | None = None
    auto_detect_disko: bool = False


class SecretInjection(pydantic.BaseModel):
    name: str
    age_source: Path
    target_path: str
    decrypt_key: Path | None = None
    decrypt_at_boot: bool = False


class TailscaleAuthKeyConfig(pydantic.BaseModel):
    id: str = ""
    key: str = ""
    description: str = ""
    created: str = ""
    expires: str = ""
    ephemeral: bool = False
