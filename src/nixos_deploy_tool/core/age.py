from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from nixos_deploy_tool.exceptions import SecretError


class AgeWrapper:
    def __init__(self, age_bin: str = "age") -> None:
        self._age_bin = age_bin
        self._logger = logging.getLogger(self.__class__.__name__)

    def decrypt(self, age_file: Path, identity: Path | None = None) -> str:
        cmd = [self._age_bin, "--decrypt"]
        if identity:
            cmd.extend(["--identity", str(identity)])
        cmd.append(str(age_file))
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as exc:
            msg = f"age decrypt failed: {exc.stderr.strip()}"
            raise SecretError(msg) from exc

    def encrypt(self, recipient: str, plaintext: str) -> str:
        cmd = [self._age_bin, "--encrypt", "--recipient", recipient]
        try:
            result = subprocess.run(
                cmd, input=plaintext, capture_output=True, text=True, check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as exc:
            msg = f"age encrypt failed: {exc.stderr.strip()}"
            raise SecretError(msg) from exc

    def keygen(self, output: Path | None = None) -> str:
        cmd = [self._age_bin, "--keygen"]
        if output:
            cmd.extend(["--output", str(output)])
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as exc:
            msg = f"age keygen failed: {exc.stderr.strip()}"
            raise SecretError(msg) from exc
