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

_DEFAULT_LOG_PATH = "~/.local/share/nixos-deploy/deploy.log"


def setup_logging(config: DeployConfig, verbose: bool = False) -> None:
    """Configure the root logger based on config and CLI flags.

    Always logs to a file (default ``~/.local/share/nixos-deploy/deploy.log``)
    **and** to stderr so the terminal shows progress.  Override the file path
    via ``config.log_file`` (from config YAML or ``--log-file`` CLI flag).

    Idempotent — cleared and recreated each call.
    """
    level_name = config.log_level.lower()
    level = _LOG_LEVEL_MAP.get(level_name, logging.INFO)
    if verbose:
        level = logging.DEBUG

    log_path = (
        Path(config.log_file).expanduser().resolve()
        if config.log_file
        else Path(_DEFAULT_LOG_PATH).expanduser().resolve()
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    fh = logging.FileHandler(str(log_path), mode="w")
    fh.setLevel(level)
    fh.setFormatter(logging.Formatter(_LOG_FORMAT, _LOG_DATE_FORMAT))
    root.addHandler(fh)

    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(level)
    sh.setFormatter(logging.Formatter(_LOG_FORMAT, _LOG_DATE_FORMAT))
    root.addHandler(sh)
