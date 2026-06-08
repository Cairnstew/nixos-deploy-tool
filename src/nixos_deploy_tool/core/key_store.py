from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path


class KeyStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = (base_dir or Path("~/.local/share/nixos-deploy/keys")).expanduser().resolve()
        self._logger = logging.getLogger(self.__class__.__name__)

    def key_dir(self, hostname: str) -> Path:
        return self._base_dir / hostname

    def privkey_path(self, hostname: str) -> Path:
        return self.key_dir(hostname) / "ssh_host_ed25519_key"

    def pubkey_path(self, hostname: str) -> Path:
        return self.key_dir(hostname) / "ssh_host_ed25519_key.pub"

    def exists(self, hostname: str) -> bool:
        return self.privkey_path(hostname).exists()

    def generate(self, hostname: str) -> tuple[Path, str]:
        kdir = self.key_dir(hostname)
        kdir.mkdir(parents=True, exist_ok=True)

        privkey = self.privkey_path(hostname)

        subprocess.run(
            ["ssh-keygen", "-t", "ed25519", "-N", "", "-f", str(privkey)],
            check=True,
            capture_output=True,
            text=True,
        )

        os.chmod(privkey, 0o600)

        pubkey = self.public_key(hostname)

        extra_dir = kdir / "extra-files" / "etc" / "ssh"
        extra_dir.mkdir(parents=True, exist_ok=True)
        extra_priv = extra_dir / "ssh_host_ed25519_key"
        extra_pub = extra_dir / "ssh_host_ed25519_key.pub"
        if not extra_priv.exists():
            shutil.copy2(privkey, extra_priv)
            os.chmod(extra_priv, 0o600)
        if not extra_pub.exists():
            shutil.copy2(self.pubkey_path(hostname), extra_pub)

        return privkey, pubkey

    def public_key(self, hostname: str) -> str:
        return self.pubkey_path(hostname).read_text().strip()

    def extra_files_dir(self, hostname: str) -> Path:
        return self.key_dir(hostname) / "extra-files"
