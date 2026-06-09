from __future__ import annotations

import logging
import subprocess
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence


class SubprocessRunner(ABC):
    """Shared interface for CLI subprocess wrappers.

    Subclasses define _wrap_error() to map CalledProcessError to a
    domain exception.  Call _run(args) for simple execution,
    _run_streaming(args) for line-by-line output via a callback.
    """

    binary: str

    def __init__(self, binary: str) -> None:
        self.binary = binary
        self.logger = logging.getLogger(self.__class__.__module__)

    def _run(
        self,
        args: Sequence[str],
        input: str | None = None,
        timeout: int = 300,
        **kwargs: object,
    ) -> str:
        cmd = [self.binary, *args]
        self.logger.debug("Running: %s", " ".join(cmd))
        try:
            result = subprocess.run(
                cmd,
                input=input,
                capture_output=True,
                text=True,
                timeout=timeout,
                **kwargs,
            )
            if result.returncode != 0:
                raise subprocess.CalledProcessError(
                    result.returncode, cmd, result.stdout, result.stderr
                )
            return result.stdout.strip()
        except subprocess.CalledProcessError as exc:
            raise self._wrap_error(exc) from exc

    def _run_streaming(
        self,
        args: Sequence[str],
        on_output: Callable[[str], None] | None = None,
        on_done: Callable[[int], None] | None = None,
        **kwargs: object,
    ) -> int:
        cmd = [self.binary, *args]
        self.logger.info("Running: %s", " ".join(cmd))
        try:
            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                **kwargs,
            ) as proc:
                if proc.stdout:
                    for line in proc.stdout:
                        stripped = line.rstrip()
                        if on_output:
                            on_output(stripped)
                proc.wait()
                returncode = proc.returncode
        except Exception as exc:
            self.logger.error("Streaming run failed: %s", exc)
            returncode = -1

        if on_done:
            on_done(returncode)
        return returncode

    @abstractmethod
    def _wrap_error(self, exc: subprocess.CalledProcessError) -> Exception:
        """Map a CalledProcessError to a domain-specific exception."""


class APIClient(ABC):
    """Shared interface for HTTP API clients.

    Subclasses define _auth_headers() to inject authentication.
    """

    base_url: str

    def __init__(self, base_url: str = "") -> None:
        self.base_url = base_url
        self.logger = logging.getLogger(self.__class__.__module__)

    @abstractmethod
    def _auth_headers(self) -> dict[str, str]:
        ...
