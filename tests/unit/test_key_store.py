from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from nixos_deploy_tool.core.key_store import KeyStore


def _fake_ssh_keygen(privkey_path: Path) -> None:
    """Simulate what ssh-keygen does: create privkey + pubkey files."""
    privkey_path.write_text("fake-private-key-content\n")
    pubkey_path = privkey_path.with_suffix(".pub")
    pubkey_path.write_text("ssh-ed25519 AAAAB3NzaC1yc2EAAAADAQABAAABAQ fake-key nixos-deploy/test\n")


def _mock_ssh_keygen_run(args, **kwargs):
    """side_effect for subprocess.run that creates key files when ssh-keygen is called."""
    if args[0] == "ssh-keygen":
        for i, arg in enumerate(args):
            if arg == "-f" and i + 1 < len(args):
                _fake_ssh_keygen(Path(args[i + 1]))
                break
    return subprocess.CompletedProcess(args=[], returncode=0)


def test_key_dir_resolves_correctly(tmp_path: Path) -> None:
    ks = KeyStore(base_dir=tmp_path)
    kdir = ks.key_dir("desktop")
    assert kdir == tmp_path / "desktop"


def test_exists_returns_false_when_missing(tmp_path: Path) -> None:
    ks = KeyStore(base_dir=tmp_path)
    assert not ks.exists("nonexistent")


def test_exists_returns_true_when_present(tmp_path: Path) -> None:
    ks = KeyStore(base_dir=tmp_path)
    privkey = ks.privkey_path("myhost")
    privkey.parent.mkdir(parents=True)
    privkey.write_text("fake-key")
    assert ks.exists("myhost")


@patch("nixos_deploy_tool.core.key_store.subprocess.run")
def test_generate_creates_files(mock_run, tmp_path: Path) -> None:
    ks = KeyStore(base_dir=tmp_path)
    privkey_path = ks.privkey_path("desktop")
    mock_run.side_effect = _mock_ssh_keygen_run

    privkey, pubkey = ks.generate("desktop")

    assert privkey == privkey_path
    assert privkey.exists()
    assert privkey.read_text() == "fake-private-key-content\n"

    pubkey_path = tmp_path / "desktop" / "ssh_host_ed25519_key.pub"
    assert pubkey_path.exists()
    assert pubkey == pubkey_path.read_text().strip()

    extra_priv = tmp_path / "desktop" / "extra-files" / "etc" / "ssh" / "ssh_host_ed25519_key"
    assert extra_priv.exists()
    assert extra_priv.read_text() == "fake-private-key-content\n"

    extra_pub = tmp_path / "desktop" / "extra-files" / "etc" / "ssh" / "ssh_host_ed25519_key.pub"
    assert extra_pub.exists()


@patch("nixos_deploy_tool.core.key_store.subprocess.run")
def test_generate_chmod_600(mock_run, tmp_path: Path) -> None:
    mock_run.side_effect = _mock_ssh_keygen_run

    ks = KeyStore(base_dir=tmp_path)
    privkey, _ = ks.generate("desktop")
    mode = os.stat(privkey).st_mode & 0o777
    assert mode == 0o600


@patch("nixos_deploy_tool.core.key_store.subprocess.run")
def test_generate_invokes_ssh_keygen(mock_run, tmp_path: Path) -> None:
    mock_run.side_effect = _mock_ssh_keygen_run

    ks = KeyStore(base_dir=tmp_path)
    ks.generate("desktop")

    mock_run.assert_called_with(
        ["ssh-keygen", "-t", "ed25519", "-N", "", "-C", "nixos-deploy/desktop", "-f", str(tmp_path / "desktop" / "ssh_host_ed25519_key")],
        check=True,
        capture_output=True,
        text=True,
    )


@patch("nixos_deploy_tool.core.key_store.subprocess.run")
def test_generate_is_idempotent(mock_run, tmp_path: Path) -> None:
    mock_run.side_effect = _mock_ssh_keygen_run

    ks = KeyStore(base_dir=tmp_path)
    privkey1, pubkey1 = ks.generate("desktop")

    privkey2, pubkey2 = ks.generate("desktop")

    assert privkey1 == privkey2
    assert pubkey1 == pubkey2


def test_public_key_reads_pubfile(tmp_path: Path) -> None:
    ks = KeyStore(base_dir=tmp_path)
    pubkey_path = ks.pubkey_path("myhost")
    pubkey_path.parent.mkdir(parents=True)
    pubkey_path.write_text("ssh-ed25519 AAAAC3... nixos-deploy/myhost\n")

    result = ks.public_key("myhost")
    assert result == "ssh-ed25519 AAAAC3... nixos-deploy/myhost"


def test_extra_files_dir(tmp_path: Path) -> None:
    ks = KeyStore(base_dir=tmp_path)
    assert ks.extra_files_dir("h") == tmp_path / "h" / "extra-files"


def test_privkey_path(tmp_path: Path) -> None:
    ks = KeyStore(base_dir=tmp_path)
    assert ks.privkey_path("h") == tmp_path / "h" / "ssh_host_ed25519_key"


def test_pubkey_path(tmp_path: Path) -> None:
    ks = KeyStore(base_dir=tmp_path)
    assert ks.pubkey_path("h") == tmp_path / "h" / "ssh_host_ed25519_key.pub"
