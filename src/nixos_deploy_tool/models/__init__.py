from nixos_deploy_tool.models.config import (
    DeployConfig,
    HostConfig,
    ISOConfig,
    SecretInjection,
    TailscaleAuthKeyConfig,
    TailscaleConfig,
    TailscaleOAuthConfig,
    ToolPaths,
    normalise_partitions,
)
from nixos_deploy_tool.models.result import BaseResult, ErrorResult, SuccessResult

__all__ = [
    "DeployConfig",
    "HostConfig",
    "ISOConfig",
    "SecretInjection",
    "TailscaleAuthKeyConfig",
    "TailscaleConfig",
    "TailscaleOAuthConfig",
    "ToolPaths",
    "BaseResult",
    "SuccessResult",
    "ErrorResult",
    "normalise_partitions",
]
