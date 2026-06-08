from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, call

from nixos_deploy_tool.core.nixos_anywhere import NixosAnywhere


def test_extract_host_strips_user() -> None:
    assert NixosAnywhere._extract_host("nixos@nixos") == "nixos"


def test_extract_host_preserves_plain_hostname() -> None:
    assert NixosAnywhere._extract_host("desktop") == "desktop"


def test_extract_host_handles_ip() -> None:
    assert NixosAnywhere._extract_host("nixos@100.1.2.3") == "100.1.2.3"


def test_extract_host_handles_ip_without_user() -> None:
    assert NixosAnywhere._extract_host("100.1.2.3") == "100.1.2.3"


def test_extract_host_handles_multiple_ats() -> None:
    assert NixosAnywhere._extract_host("user@name@host") == "host"


@patch("nixos_deploy_tool.core.nixos_anywhere.subprocess.run")
def test_clear_known_hosts_calls_ssh_keygen(mock_run) -> None:
    nix = NixosAnywhere()
    nix._clear_known_hosts("nixos@nixos")

    mock_run.assert_called_once_with(
        ["ssh-keygen", "-R", "nixos"],
        capture_output=True,
        text=True,
    )


@patch("nixos_deploy_tool.core.nixos_anywhere.subprocess.run")
def test_clear_known_hosts_with_ip(mock_run) -> None:
    nix = NixosAnywhere()
    nix._clear_known_hosts("nixos@100.1.2.3")

    mock_run.assert_called_once_with(
        ["ssh-keygen", "-R", "100.1.2.3"],
        capture_output=True,
        text=True,
    )


@patch("nixos_deploy_tool.core.nixos_anywhere.subprocess.run")
def test_deploy_clears_known_hosts_before_running(mock_run) -> None:
    mock_run.return_value.returncode = 0

    nix = NixosAnywhere()
    nix.deploy(
        target="nixos@nixos",
        flake_attr="desktop",
        flake_root=Path("/fake/flake"),
    )

    assert mock_run.call_count >= 2
    assert mock_run.call_args_list[0] == call(
        ["ssh-keygen", "-R", "nixos"],
        capture_output=True,
        text=True,
    )


@patch("nixos_deploy_tool.core.nixos_anywhere.subprocess.run")
def test_deploy_includes_no_ssh_copy_id_when_key_provided(mock_run) -> None:
    mock_run.return_value.returncode = 0

    nix = NixosAnywhere()
    nix.deploy(
        target="nixos@nixos",
        flake_attr="desktop",
        flake_root=Path("/fake/flake"),
        ssh_key="/home/user/.ssh/id_ed25519",
    )

    nixos_anywhere_call = mock_run.call_args_list[-1]
    args = nixos_anywhere_call[0][0]
    assert "--no-ssh-copy-id" in args
    assert "-i" in args
    assert "/home/user/.ssh/id_ed25519" in args
