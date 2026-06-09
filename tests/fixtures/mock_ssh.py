from __future__ import annotations

import subprocess


MOCK_DISKS = [
    {
        "name": "sda", "size": "238.5G", "type": "disk", "model": "Samsung SSD",
        "children": [
            {"name": "sda1", "fstype": "vfat", "mountpoint": "/boot",
             "size": "512M", "type": "part"},
            {"name": "sda2", "fstype": "ext4", "mountpoint": "/",
             "size": "238G", "type": "part"},
        ],
    },
    {
        "name": "sdb", "size": "1.0T", "type": "disk", "model": "WD Blue",
        "children": [],
    },
]


class MockSshClient:
    """No-op SshClient — never shells out.

    Configure per-test by mutating the shared instance:

        svc.ssh_client.partition_exists_results = {
            "disk-main-root": False,
        }
    """

    def __init__(self, target: str, ssh_key: str | None = None) -> None:
        self._target = target
        self._ssh_key = ssh_key
        self.partition_exists_results: dict[str, bool] = {}
        self.created_partitions: list[tuple[str, str]] = []
        self.mkfs_calls: list[tuple[str, str, str]] = []
        self.list_disks_results: list[dict] = MOCK_DISKS

    def partition_exists(self, partlabel: str) -> bool:
        return self.partition_exists_results.get(partlabel, True)

    def create_partition(self, device: str, label: str) -> None:
        self.created_partitions.append((device, label))

    def mkfs(self, device_path: str, fstype: str, label: str) -> None:
        self.mkfs_calls.append((device_path, fstype, label))

    def path_for_partlabel(self, partlabel: str) -> str | None:
        return f"/dev/{partlabel}"

    def list_disks(self) -> list[dict]:
        return list(self.list_disks_results)

    def run(self, *args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
