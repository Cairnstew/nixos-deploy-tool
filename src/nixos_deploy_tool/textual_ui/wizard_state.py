from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WizardState:
    host_name: str = ""
    flake_attr: str = ""
    ssh_target: str = ""
    ssh_key: str | None = None
    disko_mode: str = "auto"
    extra_args: str | None = None
    missing_partlabels: list[str] = field(default_factory=list)
    disko_device_summary: str = ""
    create_partitions: bool = False
