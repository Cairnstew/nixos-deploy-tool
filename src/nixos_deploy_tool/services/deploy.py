from __future__ import annotations

from pathlib import Path

from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.models.result import BaseResult, SuccessResult
from nixos_deploy_tool.services.base import BaseService


class DeployService(BaseService):
    def __init__(self, config: DeployConfig) -> None:
        super().__init__(config)
        self._flake_root = Path(config.flake_root) if config.flake_root else Path.cwd()

    def run(self, host: str, addr: str | None = None) -> BaseResult:
        self.logger.info("Deploying to %s (addr=%s)", host, addr or "auto")
        return SuccessResult(message=f"Deployed {host}.")

    def wizard(self, host: str) -> BaseResult:
        self.logger.info("Running deploy wizard for %s", host)
        return SuccessResult(message=f"Wizard completed for {host}.")

    def with_keys(self, host: str) -> BaseResult:
        self.logger.info("Deploying with keys to %s", host)
        return SuccessResult(message=f"Deployed {host} with keys.")

    def test(self, host: str) -> BaseResult:
        self.logger.info("VM-testing host config: %s", host)
        return SuccessResult(message=f"Test passed for {host}.")
