from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path


class SshClient:
    def __init__(self, target: str, ssh_key: str | None = None) -> None:
        self._target = target
        self._key = ssh_key
        self._logger = logging.getLogger(self.__class__.__name__)

    def _base_cmd(self) -> list[str]:
        cmd: list[str] = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
        ]
        if self._key:
            cmd.extend(["-i", self._key])
        cmd.append(self._target)
        return cmd

    def run(self, command: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        full_cmd = [*self._base_cmd(), command]
        self._logger.debug("Running: ssh ... %s", command)
        result = subprocess.run(full_cmd, capture_output=True, text=True)
        if check and result.returncode != 0:
            raise RuntimeError(
                f"remote command failed (exit {result.returncode}): {command}\n{result.stderr}"
            )
        return result

    def partition_exists(self, partlabel: str) -> bool:
        result = self.run(
            f"test -e /dev/disk/by-partlabel/{partlabel}", check=False
        )
        return result.returncode == 0

    def list_partitions(self) -> list[dict[str, object]]:
        result = self.run("lsblk --json -o NAME,PATH,LABEL,PARTLABEL,TYPE")
        data = json.loads(result.stdout)
        return data.get("blockdevices", [])

    def create_partition(self, device: str, label: str) -> None:
        self.run(
            f"sgdisk -n 0:0:0 -t 0:8300 -c 0:{label} {device}"
        )

    def mkfs(self, device_path: str, fstype: str, label: str) -> None:
        self.run(f"mkfs.{fstype} -L {label} {device_path}")

    def path_for_partlabel(self, partlabel: str) -> str | None:
        result = self.run(
            f"readlink -f /dev/disk/by-partlabel/{partlabel}",
            check=False,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()
