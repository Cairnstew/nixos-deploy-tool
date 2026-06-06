from __future__ import annotations

import logging

from nixos_deploy_tool.models.config import DeployConfig


class BaseService:
    def __init__(self, config: DeployConfig) -> None:
        self.config = config
        self.logger = logging.getLogger(self.__class__.__module__)
