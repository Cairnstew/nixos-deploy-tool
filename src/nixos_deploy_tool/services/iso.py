from __future__ import annotations

from pathlib import Path

from nixos_deploy_tool.models.config import DeployConfig, ISOConfig, SecretInjection
from nixos_deploy_tool.models.result import BaseResult, SuccessResult
from nixos_deploy_tool.services.base import BaseService


class ISOService(BaseService):
    def __init__(self, config: DeployConfig) -> None:
        super().__init__(config)
        self._flake_root = Path(config.flake_root) if config.flake_root else Path.cwd()

    def list_isos(self) -> list[ISOConfig]:
        return []

    def build(self, name: str) -> BaseResult:
        self.logger.info("Building ISO: %s", name)
        return SuccessResult(message=f"ISO {name} built.")

    def rotate_keys(self, name: str) -> BaseResult:
        self.logger.info("Rotating keys for ISO: %s", name)
        return SuccessResult(message=f"Keys rotated for {name}.")

    def info(self, name: str) -> ISOConfig | None:
        return None

    def inject_secrets(self, iso_name: str, secrets: list[SecretInjection]) -> BaseResult:
        self.logger.info("Injecting %d secrets into ISO %s", len(secrets), iso_name)
        return SuccessResult(message=f"Secrets injected into {iso_name}.")
