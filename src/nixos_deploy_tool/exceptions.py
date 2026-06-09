from __future__ import annotations


class NixosDeployError(Exception):
    """Root exception for all nixos-deploy-tool errors."""


class ISOBuildError(NixosDeployError):
    """Raised when ISO build fails."""


class DeployRuntimeError(NixosDeployError):
    """Raised when deployment operation fails."""


class SecretError(NixosDeployError):
    """Raised when secret operation fails."""


class TailscaleAPIError(NixosDeployError):
    """Raised when Tailscale API call fails."""


class CoreError(NixosDeployError):
    """Root for all core/infrastructure wrapper errors."""


class SubprocessError(CoreError):
    """Raised when a subprocess runner call fails."""


class APIError(CoreError):
    """Raised when an HTTP API client call fails."""


class NixEvalError(NixosDeployError):
    """Raised when nix eval fails (e.g. attribute missing)."""
