from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

from nixos_deploy_tool.exceptions import NixEvalError
from nixos_deploy_tool.models.config import DeployConfig, TailscaleConfig, TailscaleOAuthConfig
from nixos_deploy_tool.services.deploy import DeployService
from nixos_deploy_tool.services.iso import ISOService
from nixos_deploy_tool.services.prepare import PrepareService
from nixos_deploy_tool.services.secrets import SecretService
from nixos_deploy_tool.services.tailscale import TailscaleService


def _cfg(**kw: object) -> DeployConfig:
    """DeployConfig with a fake flake_root by default."""
    overrides = dict(flake_root="/fake/flake")
    overrides.update(kw)
    return DeployConfig(**overrides)


def test_isoservice_build() -> None:
    with patch("nixos_deploy_tool.services.iso.ISOBuilder.build") as mock_build:
        mock_build.return_value = Path("/nix/store/abc-test-iso")
        svc = ISOService(_cfg())
        result = svc.build("test-iso")
    assert result.ok
    assert "test-iso" in result.message


def _flake_patch():
    return patch(
        "nixos_deploy_tool.services.deploy.FlakeIntrospector.list_host_configs",
        return_value=[{"name": "myhost", "attr": "myhost"}],
    )


def test_deployservice_run() -> None:
    with (
        patch("nixos_deploy_tool.services.deploy.NixosAnywhere.deploy") as m,
        _flake_patch(),
    ):
        m.return_value = None
        svc = DeployService(_cfg())
        result = svc.run("myhost")
    assert result.ok


def test_deployservice_run_injects_extra_files_when_key_exists() -> None:
    with (
        patch("nixos_deploy_tool.services.deploy.NixosAnywhere.deploy") as m,
        patch("nixos_deploy_tool.services.deploy.KeyStore.exists", return_value=True),
        _flake_patch(),
    ):
        m.return_value = None
        svc = DeployService(_cfg())
        result = svc.run("myhost")
    assert result.ok
    assert m.call_args.kwargs["extra_files"] is not None


def test_deployservice_run_no_extra_files_when_key_missing() -> None:
    with (
        patch("nixos_deploy_tool.services.deploy.NixosAnywhere.deploy") as m,
        patch("nixos_deploy_tool.services.deploy.KeyStore.exists", return_value=False),
        _flake_patch(),
    ):
        m.return_value = None
        svc = DeployService(_cfg())
        result = svc.run("myhost")
    assert result.ok
    assert m.call_args.kwargs["extra_files"] is None


def test_deployservice_with_keys_uses_configured_ssh_key() -> None:
    with (
        patch("nixos_deploy_tool.services.deploy.NixosAnywhere.deploy") as m,
        patch("nixos_deploy_tool.services.deploy.Path.exists", return_value=True),
        _flake_patch(),
    ):
        m.return_value = None
        cfg = _cfg(ssh_key_path="/custom/key")
        svc = DeployService(cfg)
        result = svc.with_keys("myhost")
    assert result.ok
    assert m.call_args.kwargs["ssh_key"] == "/custom/key"


def test_deployservice_with_keys_no_ssh_key_found() -> None:
    with (
        patch("nixos_deploy_tool.services.deploy.NixosAnywhere.deploy") as m,
        patch("nixos_deploy_tool.services.deploy.KeyStore.exists", return_value=True),
        patch("nixos_deploy_tool.services.deploy.Path.exists", return_value=False),
        _flake_patch(),
    ):
        m.return_value = None
        cfg = _cfg(ssh_key_path=None)
        svc = DeployService(cfg)
        result = svc.with_keys("myhost")
    assert result.ok
    assert m.call_args.kwargs["ssh_key"] is None


def test_deployservice_with_keys_injects_extra_files() -> None:
    with (
        patch("nixos_deploy_tool.services.deploy.NixosAnywhere.deploy") as m,
        patch("nixos_deploy_tool.services.deploy.KeyStore.exists", return_value=True),
        _flake_patch(),
    ):
        m.return_value = None
        svc = DeployService(_cfg())
        result = svc.with_keys("myhost")
    assert result.ok
    assert m.call_args.kwargs["extra_files"] is not None


def test_deployservice_with_keys_uses_addr_when_provided() -> None:
    with (
        patch("nixos_deploy_tool.services.deploy.NixosAnywhere.deploy") as m,
        patch("nixos_deploy_tool.services.deploy.KeyStore.exists", return_value=False),
        _flake_patch(),
    ):
        m.return_value = None
        svc = DeployService(_cfg())
        result = svc.with_keys("myhost", addr="nixos@10.0.0.1")
    assert result.ok
    assert m.call_args.kwargs["target"] == "nixos@10.0.0.1"


def test_deployservice_with_keys_defaults_to_host_when_no_addr() -> None:
    with (
        patch("nixos_deploy_tool.services.deploy.NixosAnywhere.deploy") as m,
        patch("nixos_deploy_tool.services.deploy.KeyStore.exists", return_value=False),
        _flake_patch(),
    ):
        m.return_value = None
        svc = DeployService(_cfg())
        result = svc.with_keys("myhost")
    assert result.ok
    assert m.call_args.kwargs["target"] == "myhost"


def test_build_extra_args_empty_config() -> None:
    svc = DeployService(_cfg())
    result = svc.build_extra_args("myhost", None)
    assert result == []


def test_build_extra_args_default_extra_args() -> None:
    svc = DeployService(_cfg(default_extra_args=["--verbose"]))
    result = svc.build_extra_args("myhost", None)
    assert result == ["--verbose"]


def test_build_extra_args_skip_disko() -> None:
    svc = DeployService(_cfg(skip_disko=True))
    result = svc.build_extra_args("myhost", None)
    assert result == ["--phases", "kexec,install,reboot"]


def test_build_extra_args_disko_mode_mount() -> None:
    svc = DeployService(_cfg(disko_mode="mount"))
    result = svc.build_extra_args("myhost", None)
    assert result == ["--disko-mode", "mount"]


def test_build_extra_args_defaults_plus_skip_disko() -> None:
    svc = DeployService(_cfg(default_extra_args=["--verbose"], skip_disko=True))
    result = svc.build_extra_args("myhost", None)
    assert result == ["--verbose", "--phases", "kexec,install,reboot"]


def test_build_extra_args_skip_disko_overrides_disko_mode() -> None:
    svc = DeployService(_cfg(skip_disko=True, disko_mode="mount"))
    result = svc.build_extra_args("myhost", None)
    assert result == ["--phases", "kexec,install,reboot"]


def test_build_extra_args_disko_mode_no_eval() -> None:
    svc = DeployService(_cfg(disko_mode="mount", auto_detect_disko=True))
    with patch.object(svc._nix, "eval_flake_json") as mock_eval:
        result = svc.build_extra_args("myhost", None)
    assert result == ["--disko-mode", "mount"]
    mock_eval.assert_not_called()


def test_build_extra_args_auto_detect_skips_when_missing() -> None:
    svc = DeployService(_cfg(auto_detect_disko=True))
    with patch.object(svc._nix, "eval_flake_json", side_effect=NixEvalError("not found")):
        result = svc.build_extra_args("myhost", None)
    assert result == ["--phases", "kexec,install,reboot"]


def test_build_extra_args_auto_detect_no_skip_when_present() -> None:
    svc = DeployService(_cfg(auto_detect_disko=True))
    with patch.object(svc._nix, "eval_flake_json", return_value="/nix/store/abc-disko-script"):
        result = svc.build_extra_args("myhost", None)
    assert result == []


def test_build_extra_args_cli_appended_last() -> None:
    svc = DeployService(_cfg(default_extra_args=["--phases", "kexec,disko"]))
    result = svc.build_extra_args("myhost", "--phases kexec,install,reboot")
    assert result == ["--phases", "kexec,disko", "--phases", "kexec,install,reboot"]


def test_deployservice_wizard_accepts_extra_args() -> None:
    with (
        patch("nixos_deploy_tool.services.deploy.NixosAnywhere.deploy") as m,
        patch("nixos_deploy_tool.services.deploy.KeyStore.exists", return_value=True),
        _flake_patch(),
    ):
        m.return_value = None
        svc = DeployService(_cfg())
        result = svc.wizard("myhost", addr="nixos@10.0.0.1", extra_args="--verbose")
    assert result.ok
    assert m.call_args.kwargs["target"] == "nixos@10.0.0.1"
    assert "--verbose" in m.call_args.kwargs["extra_args"]


def test_build_extra_args_skip_disko_overrides_auto_detect() -> None:
    svc = DeployService(_cfg(skip_disko=True, auto_detect_disko=True))
    with patch.object(svc._nix, "eval_flake_json") as mock_eval:
        result = svc.build_extra_args("myhost", None)
    assert result == ["--phases", "kexec,install,reboot"]
    mock_eval.assert_not_called()


def test_build_extra_args_warns_on_default_extra_args_conflict() -> None:
    svc = DeployService(_cfg(skip_disko=True, default_extra_args=["--disko-mode", "mount"]))
    with patch.object(svc.logger, "warning") as mock_warning:
        result = svc.build_extra_args("myhost", None)
    assert result == ["--disko-mode", "mount", "--phases", "kexec,install,reboot"]
    mock_warning.assert_any_call(
        "default_extra_args contains %s which will be overridden by "
        "skip_disko/disko_mode/auto_detect_disko settings",
        "--disko-mode",
    )


def test_build_extra_args_warns_on_cli_override() -> None:
    svc = DeployService(_cfg(disko_mode="mount"))
    with patch.object(svc.logger, "warning") as mock_warning:
        result = svc.build_extra_args("myhost", "--phases kexec,disko,install,reboot")
    assert result == ["--disko-mode", "mount", "--phases", "kexec,disko,install,reboot"]
    mock_warning.assert_any_call(
        "disko_mode=%s but --extra-args contains --phases; "
        "last flag wins for nixos-anywhere",
        "mount",
    )


def test_build_extra_args_logs_final_args() -> None:
    svc = DeployService(_cfg(skip_disko=True))
    with patch.object(svc.logger, "info") as mock_info:
        svc.build_extra_args("myhost", None)
    mock_info.assert_any_call("nixos-anywhere extra args: %s", "--phases kexec,install,reboot")


def test_build_extra_args_explicit_mode_overrides_config_skip() -> None:
    svc = DeployService(_cfg(skip_disko=True))
    result = svc.build_extra_args("myhost", None, disko_mode="create")
    assert result == ["--disko-mode", "create"]


def test_build_extra_args_explicit_skip_overrides_config_mount() -> None:
    svc = DeployService(_cfg(disko_mode="mount"))
    result = svc.build_extra_args("myhost", None, disko_mode="skip")
    assert result == ["--phases", "kexec,install,reboot"]


def test_build_extra_args_explicit_mode_ignores_config_auto_detect() -> None:
    svc = DeployService(_cfg(auto_detect_disko=True))
    result = svc.build_extra_args("myhost", None, disko_mode="mount")
    assert result == ["--disko-mode", "mount"]


def test_build_extra_args_disk_overrides() -> None:
    svc = DeployService(_cfg())
    result = svc.build_extra_args(
        "myhost", None, disk_overrides={"main": "/dev/sdb", "cache": "/dev/nvme0n1"}
    )
    assert "--disk" in result
    assert result[result.index("--disk") + 1] == "main"
    assert result[result.index("--disk") + 2] == "/dev/sdb"


def test_prepareservice_new_key() -> None:
    with patch("nixos_deploy_tool.services.prepare.KeyStore") as mock_keystore_cls:
        mock_ks = MagicMock()
        mock_keystore_cls.return_value = mock_ks
        mock_ks.exists.return_value = False
        mock_ks.generate.return_value = (Path("/fake/privkey"), "ssh-ed25519 AAAAB3...")

        svc = PrepareService(_cfg())
        result = svc.prepare("desktop")
    assert result.ok
    assert result.data["newly_generated"] is True
    assert result.data["pubkey"] == "ssh-ed25519 AAAAB3..."
    mock_ks.generate.assert_called_once_with("desktop")


def test_prepareservice_existing_key() -> None:
    with patch("nixos_deploy_tool.services.prepare.KeyStore") as mock_keystore_cls:
        mock_ks = MagicMock()
        mock_keystore_cls.return_value = mock_ks
        mock_ks.exists.return_value = True
        mock_ks.public_key.return_value = "ssh-ed25519 AAAAB3... existing"

        svc = PrepareService(_cfg())
        result = svc.prepare("desktop")
    assert result.ok
    assert result.data["newly_generated"] is False
    assert result.data["pubkey"] == "ssh-ed25519 AAAAB3... existing"
    mock_ks.generate.assert_not_called()


def test_prepareservice_error() -> None:
    with patch("nixos_deploy_tool.services.prepare.KeyStore") as mock_keystore_cls:
        mock_ks = MagicMock()
        mock_keystore_cls.return_value = mock_ks
        mock_ks.exists.side_effect = RuntimeError("ssh-keygen not found")

        svc = PrepareService(_cfg())
        result = svc.prepare("desktop")
    assert not result.ok


def test_tailscale_service_create_key_no_creds() -> None:
    svc = TailscaleService(_cfg())
    result = svc.create_auth_key(description="test")
    assert not result.ok


def test_tailscale_service_create_key_with_creds() -> None:
    cfg = _cfg(
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
    svc = SecretService(_cfg())
    secrets = svc.list_secrets()
    assert secrets == []
