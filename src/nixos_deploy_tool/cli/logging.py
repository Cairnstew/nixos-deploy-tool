from __future__ import annotations

import logging
import sys
from pathlib import Path

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

    Logs go to *stderr* by default.  Set ``config.log_file`` to a path
    to redirect to a file instead.
    """
    level_name = config.log_level.lower()
    level = _LOG_LEVEL_MAP.get(level_name, logging.INFO)
    if verbose:
        level = logging.DEBUG

    if config.log_file:
        log_path = Path(config.log_file).expanduser().resolve()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            level=level,
            format=_LOG_FORMAT,
            datefmt=_LOG_DATE_FORMAT,
            filename=str(log_path),
            filemode="a",
        )
    else:
        logging.basicConfig(
            level=level,
            format=_LOG_FORMAT,
            datefmt=_LOG_DATE_FORMAT,
            stream=sys.stderr,
        )
