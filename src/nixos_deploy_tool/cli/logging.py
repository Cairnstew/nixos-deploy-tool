from __future__ import annotations

import logging
import sys

from nixos_deploy_tool.models.config import DeployConfig

_LOG_LEVEL_MAP: dict[str, int] = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_LOG_DATE_FORMAT = "%H:%M:%S"


def setup_logging(config: DeployConfig, verbose: bool = False) -> None:
    """Configure the root logger based on config and CLI flags.

    Called once at application startup (CLI and TUI).
    Idempotent — ``logging.basicConfig`` is a no-op if handlers exist.
    """
    level_name = config.log_level.lower()
    level = _LOG_LEVEL_MAP.get(level_name, logging.INFO)
    if verbose:
        level = logging.DEBUG

    logging.basicConfig(
        level=level,
        format=_LOG_FORMAT,
        datefmt=_LOG_DATE_FORMAT,
        stream=sys.stderr,
    )
