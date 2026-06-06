from __future__ import annotations

from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.models.result import BaseResult, SuccessResult
from nixos_deploy_tool.services.base import BaseService


class SecretService(BaseService):
    def __init__(self, config: DeployConfig) -> None:
        super().__init__(config)

    def list_secrets(self) -> list[dict[str, object]]:
        return []

    def decrypt(self, name: str) -> BaseResult:
        self.logger.info("Decrypting secret: %s", name)
        return SuccessResult(message=f"Secret {name} decrypted.")

    def rekey(self) -> BaseResult:
        self.logger.info("Rekeying all secrets")
        return SuccessResult(message="Secrets rekeyed.")
