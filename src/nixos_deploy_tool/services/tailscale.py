from __future__ import annotations

from nixos_deploy_tool.models.config import DeployConfig, TailscaleAuthKeyConfig
from nixos_deploy_tool.models.result import BaseResult, SuccessResult
from nixos_deploy_tool.services.base import BaseService


class TailscaleService(BaseService):
    def __init__(self, config: DeployConfig) -> None:
        super().__init__(config)

    def create_auth_key(self, description: str = "", ephemeral: bool = True) -> BaseResult:
        self.logger.info("Creating Tailscale auth key")
        return SuccessResult(message="Auth key created.", data={"key": ""})

    def list_auth_keys(self) -> list[TailscaleAuthKeyConfig]:
        return []

    def revoke_auth_key(self, key_id: str) -> BaseResult:
        self.logger.info("Revoking auth key: %s", key_id)
        return SuccessResult(message=f"Auth key {key_id} revoked.")

    def status(self) -> BaseResult:
        self.logger.info("Showing Tailscale status")
        return SuccessResult(message="Status retrieved.")
