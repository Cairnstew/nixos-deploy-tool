from __future__ import annotations

from pathlib import Path

from nixos_deploy_tool.core._base import SubprocessRunner
from nixos_deploy_tool.exceptions import SecretError, SubprocessError


class AgeRunner(SubprocessRunner):
    def __init__(self, age_bin: str = "age") -> None:
        super().__init__(age_bin)

    def _wrap_error(self, exc: subprocess.CalledProcessError) -> Exception:  # type: ignore[name-defined]
        import subprocess

        return SecretError(f"age failed: {exc.stderr.strip()}")

    def decrypt(self, age_file: Path, identity: Path | None = None) -> str:
        args = ["--decrypt"]
        if identity:
            args.extend(["--identity", str(identity)])
        args.append(str(age_file))
        return self._run(args)

    def encrypt(self, recipient: str, plaintext: str) -> str:
        args = ["--encrypt", "--recipient", recipient]
        try:
            return self._run(args, input=plaintext)
        except SubprocessError as exc:
            raise SecretError(str(exc)) from exc

    def keygen(self, output: Path | None = None) -> str:
        args = ["--keygen"]
        if output:
            args.extend(["--output", str(output)])
        return self._run(args)
