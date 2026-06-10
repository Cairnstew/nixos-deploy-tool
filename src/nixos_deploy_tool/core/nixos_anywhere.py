from __future__ import annotations

import logging
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any  # noqa: TC003 — used in _validate signature

from nixos_deploy_tool.core.nix_tool import NixTool
from nixos_deploy_tool.exceptions import DeployRuntimeError

logger = logging.getLogger(__name__)

VALID_PHASES: frozenset[str] = frozenset({"kexec", "disko", "install", "reboot"})
VALID_DISKO_MODES: frozenset[str] = frozenset({"disko", "mount", "format"})
VALID_BUILD_MODES: frozenset[str] = frozenset({"auto", "remote", "local"})
VALID_HW_BACKENDS: frozenset[str] = frozenset({"nixos-facter", "nixos-generate-config"})


class NixosAnywhere(NixTool):
    """Wrapper for the ``nixos-anywhere`` CLI tool.

    Usage::

        nix = NixosAnywhere()
        nix.deploy(
            target="nixos@10.0.0.1",
            flake_attr="myhost",
            flake_root=Path("/home/user/my-flake"),
            ssh_key="/home/user/.ssh/id_ed25519",
            phases="kexec,disko,install,reboot",
            extra_files=Path("/tmp/extra-files"),
        )

    All flags are declared as typed Python parameters.  The ``extra_args``
    escape hatch remains for flags not yet modelled.
    """

    # ── Lifecycle ─────────────────────────────────────────────────────

    def __init__(self, binary: str = "nixos-anywhere") -> None:
        super().__init__(binary)

    # ── Error mapping ─────────────────────────────────────────────────

    def _wrap_error(self, exc: subprocess.CalledProcessError) -> Exception:
        return DeployRuntimeError(
            f"nixos-anywhere failed (exit {exc.returncode}): {exc.stderr.strip()}"
        )

    # ── Validation ────────────────────────────────────────────────────

    def _validate(self, **flags: Any) -> None:
        """Validate nixos-anywhere flag values.

        Called automatically by ``_build_command``.  Checks enum values,
        path existence, and mutual exclusivity.
        """
        self._validate_phases(flags.get("phases"))
        self._validate_disko_mode(flags.get("disko_mode"))
        self._validate_build_on(flags.get("build_on"))
        self._validate_hw_backend(flags.get("generate_hardware_config"))
        self._validate_store_paths(flags.get("store_paths"))
        self._validate_flake_store_mutex(flags.get("flake"), flags.get("store_paths"))

    @staticmethod
    def _validate_phases(phases: Any) -> None:
        if phases is None:
            return
        if not isinstance(phases, str):
            raise TypeError(f"phases must be a comma-separated string, got {type(phases).__name__}")
        parts = [p.strip() for p in phases.split(",")]
        invalid = [p for p in parts if p not in VALID_PHASES]
        if invalid:
            raise ValueError(
                f"Invalid phase(s): {', '.join(invalid)}. Valid: {', '.join(sorted(VALID_PHASES))}"
            )

    @staticmethod
    def _validate_disko_mode(mode: Any) -> None:
        if mode is None:
            return
        if mode not in VALID_DISKO_MODES:
            raise ValueError(
                f"Invalid disko mode: {mode!r}. Valid: {', '.join(sorted(VALID_DISKO_MODES))}"
            )

    @staticmethod
    def _validate_build_on(build_on: Any) -> None:
        if build_on is None:
            return
        if build_on not in VALID_BUILD_MODES:
            raise ValueError(
                f"Invalid build-on mode: {build_on!r}. "
                f"Valid: {', '.join(sorted(VALID_BUILD_MODES))}"
            )

    @staticmethod
    def _validate_hw_backend(config: Any) -> None:
        if config is None:
            return
        if not isinstance(config, tuple) or len(config) != 2:
            raise TypeError(
                f"generate_hardware_config must be a (backend, path) tuple, got {config!r}"
            )
        backend = config[0]
        if backend not in VALID_HW_BACKENDS:
            raise ValueError(
                f"Invalid hardware-config backend: {backend!r}. "
                f"Valid: {', '.join(sorted(VALID_HW_BACKENDS))}"
            )

    @staticmethod
    def _validate_store_paths(pair: Any) -> None:
        if pair is None:
            return
        if not isinstance(pair, tuple) or len(pair) != 2:
            raise TypeError(
                f"store_paths must be a (disko_script, nixos_system) tuple, got {pair!r}"
            )
        for p in pair:
            if not isinstance(p, str) or not p.startswith("/nix/store/"):
                raise ValueError(f"store_paths entries must be /nix/store/ paths, got {p!r}")

    @staticmethod
    def _validate_key_identity(key: Any) -> None:
        if key is None:
            return
        p = Path(key).expanduser()
        if not p.exists():
            logger.warning(
                "SSH identity key not found: %s — nixos-anywhere will fail if it doesn't exist",
                p,
            )

    @staticmethod
    def _validate_extra_files(path: Any) -> None:
        if path is None:
            return
        p = Path(path)
        if not p.exists():
            logger.warning(
                "Extra files path does not exist: %s — nixos-anywhere will fail",
                p,
            )
            return
        if not p.is_dir():
            logger.warning(
                "Extra files path is not a directory: %s",
                p,
            )

    @staticmethod
    def _validate_flake_store_mutex(flake: Any, store_paths: Any) -> None:
        if flake is not None and store_paths is not None:
            raise ValueError(
                "--flake and --store-paths are mutually exclusive. "
                "Provide one or the other, not both."
            )

    # ── SSH helpers ───────────────────────────────────────────────────

    @staticmethod
    def _extract_host(target: str) -> str:
        if "@" in target:
            return target.rsplit("@", 1)[1]
        return target

    def _clear_known_hosts(self, target: str) -> None:
        host = self._extract_host(target)
        self.logger.info("Removing stale known_hosts entry for '%s'", host)
        subprocess.run(
            ["ssh-keygen", "-R", host],
            capture_output=True,
            text=True,
        )

    # ── Deploy ────────────────────────────────────────────────────────

    def deploy(
        self,
        target: str,
        flake_attr: str | None = None,
        flake_root: Path | None = None,
        *,
        # --- SSH / connection ---
        ssh_key: str | None = None,
        ssh_port: int | None = None,
        ssh_options: list[tuple[str, str]] | None = None,
        env_password: bool = False,
        post_kexec_ssh_port: int | None = None,
        target_host: str | None = None,
        # --- Disko ---
        phases: str | None = None,
        disko_mode: str | None = None,
        no_disko_deps: bool = False,
        # --- Build ---
        build_on: str | None = None,
        build_on_remote: bool = False,
        store_paths: tuple[str, str] | None = None,
        kexec: str | None = None,
        kexec_extra_flags: str | None = None,
        from_store: str | None = None,
        # --- Files ---
        extra_files: Path | str | None = None,
        chown: list[tuple[str, str]] | None = None,
        copy_host_keys: bool = False,
        disk_encryption_keys: list[tuple[str, str]] | None = None,
        # --- Nix ---
        nix_options: list[tuple[str, str]] | None = None,
        print_build_logs: bool = False,
        show_trace: bool = False,
        debug: bool = False,
        no_substitute_on_destination: bool = False,
        no_use_machine_substituters: bool = False,
        # --- VM / hardware ---
        vm_test: bool = False,
        generate_hardware_config: tuple[str, str] | None = None,
        # --- SSH store ---
        ssh_store_settings: list[tuple[str, str]] | None = None,
        # --- Escape hatch ---
        extra_args: Sequence[str] | None = None,
        # --- Callbacks ---
        on_output: Callable[[str], None] | None = None,
        on_done: Callable[[int], None] | None = None,
    ) -> subprocess.CompletedProcess[str] | int:
        """Deploy NixOS to a target machine via ``nixos-anywhere``.

        Parameters
        ----------
        target:
            SSH target (``user@host`` or just ``host``).
        flake_attr:
            Flake attribute to deploy (e.g. ``"myhost"``).
        flake_root:
            Path to the flake root directory.
        ssh_key:
            Path to an SSH identity file.
        ssh_port:
            SSH port to connect to.
        ssh_options:
            Repeatable ``--ssh-option`` list, each as ``(key, value)``.
        env_password:
            Use ``SSHPASS`` environment variable for ``ssh-copy-id``.
        post_kexec_ssh_port:
            Port to connect on after kexec (default: 22).
        target_host:
            Alternative to positional target (``--target-host``).
        phases:
            Comma-separated phase list
            (``kexec,disko,install,reboot``).
        disko_mode:
            Disko mode: ``"disko"``, ``"mount"``, or ``"format"``.
        no_disko_deps:
            Skip uploading disko partitioning tool dependencies.
        build_on:
            Where to build: ``"auto"``, ``"remote"``, or ``"local"``.
        build_on_remote:
            Build on the remote machine (shortcut for
            ``build_on="remote"``).
        store_paths:
            ``(disko_script, nixos_system)`` store paths (alternative to
            ``--flake``).  Both must be ``/nix/store/...`` paths.
        kexec:
            Use an alternative kexec tarball.
        kexec_extra_flags:
            Extra flags to pass to the kexec call.
        from_store:
            Source Nix store URI for copying closures.
        extra_files:
            Local directory whose contents are copied to the target root.
        chown:
            Repeatable ``--chown`` list, each as ``(path, ownership)``.
        copy_host_keys:
            Copy existing ``/etc/ssh/ssh_host_*`` keys to the
            installation.
        disk_encryption_keys:
            Repeatable ``--disk-encryption-keys`` list, each as
            ``(remote_path, local_path)``.
        nix_options:
            Repeatable ``--option`` list, each as ``(key, value)``.
        print_build_logs:
            Print full build logs (``-L``).
        show_trace:
            Show Nix build traces.
        debug:
            Enable debug output.
        no_substitute_on_destination:
            Disable ``--substitute-on-destination`` for ``nix-copy``.
        no_use_machine_substituters:
            Don't copy substituters to the installer environment.
        vm_test:
            Build and test inside a VM without deploying.
        generate_hardware_config:
            ``(backend, output_path)`` to generate a hardware config.
        ssh_store_settings:
            Repeatable ``--ssh-store-setting`` list, each as
            ``(key, value)``.
        extra_args:
            Raw extra CLI arguments appended to the end of argv.
        on_output:
            Callback for each line of stdout during streaming execution.
        on_done:
            Callback with exit code when streaming completes.

        Returns
        -------
        ``subprocess.CompletedProcess`` for non-streaming, ``int`` exit
        code for streaming.
        """
        # Pre-flight validation (before any I/O)
        self._validate_key_identity(ssh_key)
        self._validate_extra_files(extra_files)

        # Resolve flake flag
        flake_flag: str | None = None
        if flake_attr and flake_root:
            flake_flag = f"{flake_root}#{flake_attr}"
        elif flake_attr:
            flake_flag = flake_attr

        # Build the command via _build_command (calls _validate for
        # phase/mode/enum validation).  Validation errors raised here
        # prevent any subprocess I/O.
        try:
            cmd = self._build_command(
                target,
                # SSH / connection
                i=ssh_key,
                ssh_port=ssh_port,
                ssh_option=ssh_options,
                env_password=env_password or None,
                post_kexec_ssh_port=post_kexec_ssh_port,
                target_host=target_host,
                # Flake / store
                flake=flake_flag,
                store_paths=store_paths,
                # Disko
                phases=phases,
                disko_mode=disko_mode,
                no_disko_deps=no_disko_deps or None,
                # Build
                build_on=build_on,
                build_on_remote=build_on_remote or None,
                kexec=kexec,
                kexec_extra_flags=kexec_extra_flags,
                from_=from_store,
                # Files
                extra_files=extra_files,
                chown=chown,
                copy_host_keys=copy_host_keys or None,
                disk_encryption_keys=disk_encryption_keys,
                # Nix options
                option=nix_options,
                print_build_logs=print_build_logs,
                show_trace=show_trace,
                debug=debug,
                no_substitute_on_destination=no_substitute_on_destination or None,
                no_use_machine_substituters=no_use_machine_substituters or None,
                # VM / hardware
                vm_test=vm_test or None,
                generate_hardware_config=generate_hardware_config,
                # SSH store
                ssh_store_setting=ssh_store_settings,
            )
        except (ValueError, TypeError, FileNotFoundError, NotADirectoryError):
            raise

        # Clear stale known_hosts entry and execute
        self._clear_known_hosts(target)

        # Append raw extra args (escape hatch)
        if extra_args:
            cmd.extend(extra_args)

        # Execute
        if on_output or on_done:
            # _build_command returns [binary, ...] but _run_streaming
            # also prepends binary, so strip it here.
            return self._run_streaming(cmd[1:], on_output=on_output, on_done=on_done)

        try:
            # _build_command returns [binary, ...] but _run expects
            # args-only, so strip the binary.
            stdout = self._run(cmd[1:])
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout=stdout,
                stderr="",
            )
        except DeployRuntimeError:
            raise
