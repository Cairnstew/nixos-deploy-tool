from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from nixos_deploy_tool.core._base import SubprocessRunner
from nixos_deploy_tool.exceptions import SubprocessError


class NixTool(SubprocessRunner):
    """Declarative base for Nix CLI tool wrappers.

    Subclasses define their CLI contract via ``_build_command()``, which
    assembles ``argv`` from typed Python kwargs.  Callers invoke typed
    methods, never raw arg lists.

    Flag type handling (for ``**flags`` passed to ``_build_command``):

    ============================  =============================
    Python type                   CLI output
    ============================  =============================
    ``str``                       ``--flag value``
    ``bool True``                 ``--flag``
    ``bool False``                skipped
    ``None``                      skipped
    ``Path``                      ``--flag /path/to/file``
    ``list[str]``                 ``--flag v1 --flag v2``
    ``tuple[str, str]``           ``--flag val1 val2`` (single)
    ``list[tuple[str, str]]``     ``--flag k1 v1 --flag k2 v2``
    ============================  =============================
    """

    _cmd: str = ""

    def _validate(self, **flags: Any) -> None:
        """Validate flag values before command execution.

        Override in subclasses to enforce constraints (e.g. valid enum
        values, mutually exclusive options, path existence).
        Raise ``ValueError`` on invalid input.
        """

    def _build_command(
        self,
        *positional: str,
        **flags: Any,
    ) -> list[str]:
        """Build the full argv list.

        Args:
            *positional: Positional arguments (after binary, before flags).
            **flags: Named flags expanded per the type rules above.
                      Single-char keys become ``-x``, multi-char keys become
                      ``--kebab-case``.
        """
        self._validate(**flags)
        args: list[str] = [self.binary]
        if self._cmd:
            args.append(self._cmd)
        args.extend(positional)
        for key, val in flags.items():
            clean_key = key.rstrip("_")
            flag = f"-{clean_key}" if len(clean_key) == 1 else f"--{clean_key.replace('_', '-')}"
            if val is None:
                continue
            if isinstance(val, bool):
                if val:
                    args.append(flag)
                continue
            if isinstance(val, (int, float)):
                args.extend([flag, str(val)])
                continue
            if isinstance(val, Path):
                args.extend([flag, str(val)])
                continue
            if isinstance(val, str):
                args.extend([flag, val])
                continue
            if isinstance(val, tuple) and all(isinstance(v, str) for v in val):
                args.append(flag)
                for v in val:
                    args.append(v)
                continue
            if isinstance(val, list):
                if not val:
                    continue
                if all(isinstance(v, tuple) and all(isinstance(x, str) for x in v) for v in val):
                    for item in val:
                        args.append(flag)
                        for v in item:
                            args.append(v)
                else:
                    for v in val:
                        args.extend([flag, str(v)])
                continue

            raise TypeError(
                f"Unsupported flag type for '{key}': {type(val).__name__} "
                f"(value={val!r})"
            )
        return args

    def _run_cmd(
        self,
        *positional: str,
        input: str | None = None,
        timeout: int = 300,
        **flags: Any,
    ) -> str:
        """Build argv via ``_build_command`` and execute with ``_run``."""
        full = self._build_command(*positional, **flags)
        # _build_command returns [binary, ...] but _run expects
        # args-only, so strip the binary.
        return self._run(full[1:], input=input, timeout=timeout)

    def _run_cmd_streaming(
        self,
        *positional: str,
        on_output: Callable[[str], None] | None = None,
        on_done: Callable[[int], None] | None = None,
        **flags: Any,
    ) -> int:
        """Build argv via ``_build_command`` and execute with ``_run_streaming``."""
        full = self._build_command(*positional, **flags)
        return self._run_streaming(full[1:], on_output=on_output, on_done=on_done)

    @staticmethod
    def _resolve_store_path(out: str) -> Path:
        path = Path(out.strip())
        if not str(path).startswith("/nix/store/"):
            raise SubprocessError(
                f"Unexpected output — expected /nix/store/ path: {out}"
            )
        return path
