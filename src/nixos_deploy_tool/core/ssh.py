from __future__ import annotations

import json
import subprocess
from pathlib import Path

from nixos_deploy_tool.core._base import SubprocessRunner
from nixos_deploy_tool.exceptions import SubprocessError


class SshClient(SubprocessRunner):
    def __init__(self, target: str, ssh_key: str | None = None) -> None:
        super().__init__("ssh")
        self._target = target
        self._key = ssh_key

    def _wrap_error(self, exc: subprocess.CalledProcessError) -> Exception:
        return SubprocessError(
            f"SSH command failed (exit {exc.returncode}): {exc.stderr.strip()}"
        )

    def _base_args(self) -> list[str]:
        args: list[str] = [
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=10",
        ]
        if self._key:
            args.extend(["-i", self._key])
        args.append(self._target)
        return args

    def run(
        self, command: str, check: bool = True, timeout: int = 30
    ) -> subprocess.CompletedProcess[str]:
        full_cmd = [*self._base_args(), command]
        self.logger.debug("Running: ssh ... %s", command)
        result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
        if check and result.returncode != 0:
            raise SubprocessError(
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
