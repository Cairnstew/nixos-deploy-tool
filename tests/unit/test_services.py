from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

from nixos_deploy_tool.models.config import DeployConfig, TailscaleConfig, TailscaleOAuthConfig
from nixos_deploy_tool.services.base import BaseService
from nixos_deploy_tool.services.deploy import DeployService
from nixos_deploy_tool.services.iso import ISOService
from nixos_deploy_tool.services.prepare import PrepareService
from nixos_deploy_tool.services.secrets import SecretService
from nixos_deploy_tool.services.tailscale import TailscaleService


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


@patch("nixos_deploy_tool.services.deploy.NixosAnywhere.deploy")
@patch("nixos_deploy_tool.services.deploy.KeyStore.exists", return_value=True)
def test_deployservice_run_injects_extra_files_when_key_exists(mock_exists, mock_deploy) -> None:
    mock_deploy.return_value = None
    svc = DeployService(DeployConfig())
    result = svc.run("myhost")
    assert result.ok
    _, kwargs = mock_deploy.call_args
    assert kwargs["extra_files"] is not None


@patch("nixos_deploy_tool.services.deploy.NixosAnywhere.deploy")
@patch("nixos_deploy_tool.services.deploy.KeyStore.exists", return_value=False)
def test_deployservice_run_no_extra_files_when_key_missing(mock_exists, mock_deploy) -> None:
    mock_deploy.return_value = None
    svc = DeployService(DeployConfig())
    result = svc.run("myhost")
    assert result.ok
    _, kwargs = mock_deploy.call_args
    assert kwargs["extra_files"] is None


@patch("nixos_deploy_tool.services.deploy.NixosAnywhere.deploy")
@patch("nixos_deploy_tool.services.deploy.Path.exists", return_value=True)
def test_deployservice_with_keys_uses_configured_ssh_key(mock_exists, mock_deploy) -> None:
    mock_deploy.return_value = None
    cfg = DeployConfig(ssh_key_path="/custom/key")
    svc = DeployService(cfg)
    result = svc.with_keys("myhost")
    assert result.ok
    _, kwargs = mock_deploy.call_args
    assert kwargs["ssh_key"] == "/custom/key"





@patch("nixos_deploy_tool.services.deploy.NixosAnywhere.deploy")
@patch("nixos_deploy_tool.services.deploy.KeyStore.exists", return_value=True)
def test_deployservice_with_keys_no_ssh_key_found(mock_exists, mock_deploy) -> None:
    mock_deploy.return_value = None
    cfg = DeployConfig(ssh_key_path=None)

    with patch("nixos_deploy_tool.services.deploy.Path.exists", return_value=False):
        svc = DeployService(cfg)
        result = svc.with_keys("myhost")

    assert result.ok
    _, kwargs = mock_deploy.call_args
    assert kwargs["ssh_key"] is None


@patch("nixos_deploy_tool.services.deploy.NixosAnywhere.deploy")
@patch("nixos_deploy_tool.services.deploy.KeyStore.exists", return_value=True)
def test_deployservice_with_keys_injects_extra_files(mock_exists, mock_deploy) -> None:
    mock_deploy.return_value = None
    svc = DeployService(DeployConfig())
    result = svc.with_keys("myhost")
    assert result.ok
    _, kwargs = mock_deploy.call_args
    assert kwargs["extra_files"] is not None


@patch("nixos_deploy_tool.services.deploy.NixosAnywhere.deploy")
@patch("nixos_deploy_tool.services.deploy.KeyStore.exists", return_value=False)
def test_deployservice_with_keys_uses_addr_when_provided(mock_exists, mock_deploy) -> None:
    mock_deploy.return_value = None
    svc = DeployService(DeployConfig())
    result = svc.with_keys("myhost", addr="nixos@10.0.0.1")
    assert result.ok
    target = mock_deploy.call_args.kwargs["target"]
    assert target == "nixos@10.0.0.1"


@patch("nixos_deploy_tool.services.deploy.NixosAnywhere.deploy")
@patch("nixos_deploy_tool.services.deploy.KeyStore.exists", return_value=False)
def test_deployservice_with_keys_defaults_to_host_when_no_addr(mock_exists, mock_deploy) -> None:
    mock_deploy.return_value = None
    svc = DeployService(DeployConfig())
    result = svc.with_keys("myhost")
    assert result.ok
    target = mock_deploy.call_args.kwargs["target"]
    assert target == "myhost"


@patch("nixos_deploy_tool.services.prepare.KeyStore")
def test_prepareservice_new_key(mock_keystore_cls) -> None:
    mock_ks = MagicMock()
    mock_keystore_cls.return_value = mock_ks
    mock_ks.exists.return_value = False
    mock_ks.generate.return_value = (Path("/fake/privkey"), "ssh-ed25519 AAAAB3...")

    svc = PrepareService(DeployConfig())
    result = svc.prepare("desktop")
    assert result.ok
    assert result.data["newly_generated"] is True
    assert result.data["pubkey"] == "ssh-ed25519 AAAAB3..."
    mock_ks.generate.assert_called_once_with("desktop")


@patch("nixos_deploy_tool.services.prepare.KeyStore")
def test_prepareservice_existing_key(mock_keystore_cls) -> None:
    mock_ks = MagicMock()
    mock_keystore_cls.return_value = mock_ks
    mock_ks.exists.return_value = True
    mock_ks.public_key.return_value = "ssh-ed25519 AAAAB3... existing"

    svc = PrepareService(DeployConfig())
    result = svc.prepare("desktop")
    assert result.ok
    assert result.data["newly_generated"] is False
    assert result.data["pubkey"] == "ssh-ed25519 AAAAB3... existing"
    mock_ks.generate.assert_not_called()


@patch("nixos_deploy_tool.services.prepare.KeyStore")
def test_prepareservice_error(mock_keystore_cls) -> None:
    mock_ks = MagicMock()
    mock_keystore_cls.return_value = mock_ks
    mock_ks.exists.side_effect = RuntimeError("ssh-keygen not found")

    svc = PrepareService(DeployConfig())
    result = svc.prepare("desktop")
    assert not result.ok


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
