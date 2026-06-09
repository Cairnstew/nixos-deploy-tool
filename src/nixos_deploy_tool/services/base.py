from __future__ import annotations

import logging
from abc import ABC

from nixos_deploy_tool.models.config import DeployConfig


class BaseService(ABC):
    def __init__(self, config: DeployConfig) -> None:
        self.config = config
        self.logger = logging.getLogger(self.__class__.__module__)

    def on_start(self) -> None:
        """Override to perform setup when the service is first used."""

    def on_stop(self) -> None:
        """Override to perform teardown when the service is discarded."""
