from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from nixos_deploy_tool.models.config import DeployConfig


class BaseService(ABC):
    def __init__(self, config: DeployConfig) -> None:
        self.config = config
        self.logger = logging.getLogger(self.__class__.__module__)

    @abstractmethod
    def on_start(self) -> None:
        """Perform setup when the service is first used."""

    @abstractmethod
    def on_stop(self) -> None:
        """Perform teardown when the service is discarded."""
