from __future__ import annotations

from pathlib import Path
from typing import Any

import pydantic


def normalise_partitions(content: dict[str, Any]) -> list[dict[str, Any]]:
    """Return partitions as a list of dicts regardless of disko input format.

    Disko supports both dict-keyed partitions (``{ name = {...}; }``)
    and list-style partitions (``[ { name = "..."; } ]``).  Normalise to
    a list so callers can always iterate with ``for part in ...``.
    """
    raw = content.get("partitions") or {}
    if isinstance(raw, dict):
        return [
            {"name": k, **(v if isinstance(v, dict) else {})}
            for k, v in raw.items()
        ]
    return [p for p in raw if isinstance(p, dict) and p.get("name")]


class ISOConfig(pydantic.BaseModel):
    """Describes a NixOS live ISO build target from the flake."""

    name: str
    flake_attr: str = ""
    system: str = "x86_64-linux"


class HostConfig(pydantic.BaseModel):
    """Describes a NixOS host configuration from the flake."""

    name: str
    flake_attr: str = ""
    system: str = "x86_64-linux"


class TailscaleOAuthConfig(pydantic.BaseModel):
    """OAuth client credentials for Tailscale API access."""

    client_id: str = ""
    client_secret_file: str = ""


class TailscaleConfig(pydantic.BaseModel):
    """Top-level Tailscale configuration container."""

    oauth: TailscaleOAuthConfig = pydantic.Field(default_factory=TailscaleOAuthConfig)


class ToolPaths(pydantic.BaseModel):
    """Override paths for external tool binaries."""

    age_bin: str = ""
    agenix_manager_bin: str = ""
    nixos_anywhere_bin: str = ""
    tailscale_bin: str = ""


class DeployConfig(pydantic.BaseModel):
    """Top-level application configuration, loaded from YAML or CLI flags."""

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
    """Describes a single secret to inject into an ISO build."""

    name: str
    age_source: Path
    target_path: str
    decrypt_key: Path | None = None
    decrypt_at_boot: bool = False


class TailscaleAuthKeyConfig(pydantic.BaseModel):
    """Describes a Tailscale pre-authentication key from the API."""

    id: str = ""
    key: str = ""
    description: str = ""
    created: str = ""
    expires: str = ""
    ephemeral: bool = False
