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
