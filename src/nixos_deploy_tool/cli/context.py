from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, cast

from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.services.base import BaseService

if TYPE_CHECKING:
    from nixos_deploy_tool.services.deploy import DeployService
    from nixos_deploy_tool.services.iso import ISOService
    from nixos_deploy_tool.services.prepare import PrepareService
    from nixos_deploy_tool.services.secrets import SecretService
    from nixos_deploy_tool.services.tailscale import TailscaleService


_SERVICE_MAP: dict[str, tuple[str, str, bool]] = {
    "deploy": ("nixos_deploy_tool.services.deploy", "DeployService", True),
    "iso": ("nixos_deploy_tool.services.iso", "ISOService", True),
    "tailscale": ("nixos_deploy_tool.services.tailscale", "TailscaleService", False),
    "secrets": ("nixos_deploy_tool.services.secrets", "SecretService", True),
    "prepare": ("nixos_deploy_tool.services.prepare", "PrepareService", False),
}


@dataclass
class AppContext:
    verbose: bool = False
    flake_root: Path | None = None
    config: DeployConfig | None = None
    _services: dict[str, BaseService] = field(default_factory=dict, repr=False)

    def _lazy_service(
        self, key: str, module: str, class_name: str, require_flake: bool = False
    ) -> BaseService:
        svc = self._services.get(key)
        if svc is not None:
            return svc
        if self.config is None:
            raise RuntimeError("AppContext.config must be set before accessing service")
        if require_flake and not self.config.flake_root:
            raise RuntimeError(
                "AppContext.config must be set with a valid flake_root "
                "before accessing this service"
            )
        import importlib

        mod = importlib.import_module(module)
        cls = getattr(mod, class_name)
        svc = cls(config=self.config)
        self._services[key] = cast(BaseService, svc)
        return cast(BaseService, svc)

    def _get_service(self, key: str) -> BaseService:
        if key not in _SERVICE_MAP:
            raise KeyError(f"Unknown service key: {key}")
        module, class_name, require_flake = _SERVICE_MAP[key]
        return self._lazy_service(key, module, class_name, require_flake=require_flake)

    def _get_deploy_service(self) -> DeployService:
        return cast("DeployService", self._get_service("deploy"))

    def _get_iso_service(self) -> ISOService:
        return cast("ISOService", self._get_service("iso"))

    def _get_tailscale_service(self) -> TailscaleService:
        return cast("TailscaleService", self._get_service("tailscale"))

    def _get_secret_service(self) -> SecretService:
        return cast("SecretService", self._get_service("secrets"))

    def _get_prepare_service(self) -> PrepareService:
        return cast("PrepareService", self._get_service("prepare"))
