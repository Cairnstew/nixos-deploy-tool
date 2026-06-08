from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from nixos_deploy_tool.services.deploy import DeployService
from nixos_deploy_tool.models.config import DeployConfig


def _make_config(**kwargs) -> DeployConfig:
    overrides = {"ssh_key_path": None, "flake_root": "/fake/flake", **kwargs}
    return DeployConfig(**overrides)


def _expanduser_self(self: Path) -> Path:
    """A fake Path.expanduser that doesn't depend on real system users."""
    parts = str(self)
    if not parts.startswith("~"):
        return self
    tilde_part = parts.split("/")[0]
    username = tilde_part[1:]
    rest = "/".join(parts.split("/")[1:])
    if username:
        return Path(f"/home/{username}/{rest}")
    return Path(f"/root/{rest}")


@patch.object(Path, "expanduser", autospec=True)
@patch.object(Path, "exists", autospec=True)
def test_resolve_ssh_key_uses_sudo_user_home(
    mock_exists: MagicMock, mock_expanduser: MagicMock
) -> None:
    mock_exists.return_value = True
    mock_expanduser.side_effect = _expanduser_self

    config = _make_config()
    svc = DeployService(config)

    with patch.dict(os.environ, {"SUDO_USER": "seanc"}, clear=True):
        result = svc._resolve_ssh_key()

    assert result is not None
    assert result == "/home/seanc/.ssh/id_ed25519"


@patch.object(Path, "expanduser", autospec=True)
@patch.object(Path, "exists", autospec=True)
def test_resolve_ssh_key_returns_none_when_no_key_found(
    mock_exists: MagicMock, mock_expanduser: MagicMock
) -> None:
    mock_expanduser.side_effect = _expanduser_self
    mock_exists.return_value = False

    config = _make_config()
    svc = DeployService(config)

    with patch.dict(os.environ, {"SUDO_USER": "seanc"}, clear=True):
        result = svc._resolve_ssh_key()

    assert result is None


@patch.object(Path, "expanduser", autospec=True)
@patch.object(Path, "exists", autospec=True)
def test_resolve_ssh_key_falls_back_to_root_when_no_sudo_user(
    mock_exists: MagicMock, mock_expanduser: MagicMock
) -> None:
    mock_expanduser.side_effect = _expanduser_self
    mock_exists.side_effect = lambda self: str(self).startswith("/root/.ssh/")

    config = _make_config()
    svc = DeployService(config)

    with patch.dict(os.environ, {}, clear=True):
        result = svc._resolve_ssh_key()

    assert result is not None
    assert result.startswith("/root/.ssh/")


@patch.object(Path, "expanduser", autospec=True)
@patch.object(Path, "exists", autospec=True)
def test_resolve_ssh_key_prefers_sudo_user_over_root_fallback(
    mock_exists: MagicMock, mock_expanduser: MagicMock
) -> None:
    mock_expanduser.side_effect = _expanduser_self
    mock_exists.side_effect = lambda self: str(self).startswith("/home/jane/.ssh/")

    config = _make_config()
    svc = DeployService(config)

    with patch.dict(os.environ, {"SUDO_USER": "jane"}, clear=True):
        result = svc._resolve_ssh_key()

    assert result is not None
    assert result.startswith("/home/jane/.ssh/")
    assert "id_ed25519" in result
