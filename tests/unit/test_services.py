from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from nixos_deploy_tool.models.config import DeployConfig, TailscaleConfig, TailscaleOAuthConfig
from nixos_deploy_tool.services.base import BaseService
from nixos_deploy_tool.services.iso import ISOService
from nixos_deploy_tool.services.deploy import DeployService
from nixos_deploy_tool.services.tailscale import TailscaleService
from nixos_deploy_tool.services.secrets import SecretService


def test_baseservice_takes_config() -> None:
    cfg = DeployConfig()
    svc = BaseService(cfg)
    assert svc.config is cfg


@patch("nixos_deploy_tool.services.iso.ISOBuilder.build")
def test_isoservice_build(mock_build) -> None:
    mock_build.return_value = Path("/nix/store/abc-test-iso")
    svc = ISOService(DeployConfig())
    result = svc.build("test-iso")
    assert result.ok
    assert "test-iso" in result.message


@patch("nixos_deploy_tool.services.deploy.NixosAnywhere.deploy")
def test_deployservice_run(mock_deploy) -> None:
    mock_deploy.return_value = None
    svc = DeployService(DeployConfig())
    result = svc.run("myhost")
    assert result.ok


def test_tailscale_service_create_key_no_creds() -> None:
    svc = TailscaleService(DeployConfig())
    result = svc.create_auth_key(description="test")
    assert not result.ok


def test_tailscale_service_create_key_with_creds() -> None:
    cfg = DeployConfig(
        tailscale=TailscaleConfig(
            oauth=TailscaleOAuthConfig(
                client_id="test", client_secret_file="/nonexistent/secret"
            ),
        ),
    )
    svc = TailscaleService(cfg)
    result = svc.create_auth_key(description="test")
    assert not result.ok


def test_secret_service_list() -> None:
    svc = SecretService(DeployConfig())
    secrets = svc.list_secrets()
    assert secrets == []
