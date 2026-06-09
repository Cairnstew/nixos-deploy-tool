from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from nixos_deploy_tool.models.config import DeployConfig


@dataclass
class AppContext:
    verbose: bool = False
    flake_root: Path | None = None
    config: DeployConfig | None = None
    _services: dict[str, object] = field(default_factory=dict, repr=False)

    def _get_deploy_service(self):
        from nixos_deploy_tool.services.deploy import DeployService

        svc = self._services.get("deploy")
        if svc is None:
            if self.config is None or not self.config.flake_root:
                raise RuntimeError(
                    "AppContext.config must be set with a valid flake_root "
                    "before accessing deploy_service"
                )
            svc = DeployService(config=self.config)
            self._services["deploy"] = svc
        return svc

    def _get_iso_service(self):
        from nixos_deploy_tool.services.iso import ISOService

        svc = self._services.get("iso")
        if svc is None:
            if self.config is None or not self.config.flake_root:
                raise RuntimeError(
                    "AppContext.config must be set with a valid flake_root "
                    "before accessing iso_service"
                )
            svc = ISOService(config=self.config)
            self._services["iso"] = svc
        return svc

    def _get_tailscale_service(self):
        from nixos_deploy_tool.services.tailscale import TailscaleService

        svc = self._services.get("tailscale")
        if svc is None:
            if self.config is None:
                raise RuntimeError(
                    "AppContext.config must be set before accessing tailscale_service"
                )
            svc = TailscaleService(config=self.config)
            self._services["tailscale"] = svc
        return svc

    def _get_secret_service(self):
        from nixos_deploy_tool.services.secrets import SecretService

        svc = self._services.get("secrets")
        if svc is None:
            if self.config is None or not self.config.flake_root:
                raise RuntimeError(
                    "AppContext.config must be set with a valid flake_root "
                    "before accessing secret_service"
                )
            svc = SecretService(config=self.config)
            self._services["secrets"] = svc
        return svc

    def _get_prepare_service(self):
        from nixos_deploy_tool.services.prepare import PrepareService

        svc = self._services.get("prepare")
        if svc is None:
            if self.config is None:
                raise RuntimeError(
                    "AppContext.config must be set before accessing prepare_service"
                )
            svc = PrepareService(config=self.config)
            self._services["prepare"] = svc
        return svc
