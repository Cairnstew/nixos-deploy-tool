from __future__ import annotations

__all__ = [
    "APIError",
    "CoreError",
    "DeployRuntimeError",
    "ISOBuildError",
    "NixEvalError",
    "NixosDeployError",
    "SecretError",
    "SubprocessError",
    "TailscaleAPIError",
]


class NixosDeployError(Exception):
    """Root exception for all nixos-deploy-tool errors."""


class CoreError(NixosDeployError):
    """Root for all core/infrastructure wrapper errors."""


class SubprocessError(CoreError):
    """Raised when a subprocess runner call fails."""


class APIError(CoreError):
    """Raised when an HTTP API client call fails."""


class ISOBuildError(SubprocessError):
    """Raised when ISO build fails."""


class DeployRuntimeError(SubprocessError):
    """Raised when deployment operation fails."""


class SecretError(SubprocessError):
    """Raised when secret operation fails."""


class NixEvalError(SubprocessError):
    """Raised when nix eval fails (e.g. attribute missing)."""


class TailscaleAPIError(APIError):
    """Raised when Tailscale API call fails."""
