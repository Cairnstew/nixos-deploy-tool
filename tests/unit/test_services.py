from __future__ import annotations

from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.services.base import BaseService
from nixos_deploy_tool.services.iso import ISOService
from nixos_deploy_tool.services.deploy import DeployService
from nixos_deploy_tool.services.tailscale import TailscaleService
from nixos_deploy_tool.services.secrets import SecretService


def test_baseservice_takes_config() -> None:
    cfg = DeployConfig()
    svc = BaseService(cfg)
    assert svc.config is cfg


def test_isoservice_build() -> None:
    svc = ISOService(DeployConfig())
    result = svc.build("test-iso")
    assert result.ok
    assert "test-iso" in result.message


def test_deployservice_run() -> None:
    svc = DeployService(DeployConfig())
    result = svc.run("myhost")
    assert result.ok


def test_tailscale_service_create_key() -> None:
    svc = TailscaleService(DeployConfig())
    result = svc.create_auth_key(description="test")
    assert result.ok


def test_secret_service_list() -> None:
    svc = SecretService(DeployConfig())
    secrets = svc.list_secrets()
    assert secrets == []
