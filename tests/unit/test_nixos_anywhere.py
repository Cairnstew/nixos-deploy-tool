from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import call, patch

import pytest

from nixos_deploy_tool.core.nixos_anywhere import NixosAnywhere


# ── _extract_host ─────────────────────────────────────────────────────────────

def test_extract_host_strips_user() -> None:
    assert NixosAnywhere._extract_host("nixos@nixos") == "nixos"


def test_extract_host_preserves_plain_hostname() -> None:
    assert NixosAnywhere._extract_host("desktop") == "desktop"


def test_extract_host_handles_ip() -> None:
    assert NixosAnywhere._extract_host("nixos@100.1.2.3") == "100.1.2.3"


def test_extract_host_handles_ip_without_user() -> None:
    assert NixosAnywhere._extract_host("100.1.2.3") == "100.1.2.3"


def test_extract_host_handles_multiple_ats() -> None:
    assert NixosAnywhere._extract_host("user@name@host") == "host"


# ── _clear_known_hosts ────────────────────────────────────────────────────────

@patch("nixos_deploy_tool.core.nixos_anywhere.subprocess.run")
def test_clear_known_hosts_calls_ssh_keygen(mock_run) -> None:
    nix = NixosAnywhere()
    nix._clear_known_hosts("nixos@nixos")
    mock_run.assert_called_once_with(
        ["ssh-keygen", "-R", "nixos"],
        capture_output=True,
        text=True,
    )


@patch("nixos_deploy_tool.core.nixos_anywhere.subprocess.run")
def test_clear_known_hosts_with_ip(mock_run) -> None:
    nix = NixosAnywhere()
    nix._clear_known_hosts("nixos@100.1.2.3")
    mock_run.assert_called_once_with(
        ["ssh-keygen", "-R", "100.1.2.3"],
        capture_output=True,
        text=True,
    )


# ── Validation: phases ───────────────────────────────────────────────────────

def test_validate_phases_none() -> None:
    NixosAnywhere._validate_phases(None)


def test_validate_phases_valid() -> None:
    NixosAnywhere._validate_phases("kexec,disko,install,reboot")


def test_validate_phases_single() -> None:
    NixosAnywhere._validate_phases("install")


def test_validate_phases_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid phase"):
        NixosAnywhere._validate_phases("kexec,unknown")


def test_validate_phases_non_string() -> None:
    with pytest.raises(TypeError, match="phases must be"):
        NixosAnywhere._validate_phases(42)  # type: ignore[arg-type]


# ── Validation: disko mode ────────────────────────────────────────────────────

def test_validate_disko_mode_none() -> None:
    NixosAnywhere._validate_disko_mode(None)


@pytest.mark.parametrize("mode", ["disko", "mount", "format"])
def test_validate_disko_mode_valid(mode: str) -> None:
    NixosAnywhere._validate_disko_mode(mode)


def test_validate_disko_mode_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid disko mode"):
        NixosAnywhere._validate_disko_mode("destroy")


# ── Validation: build-on ──────────────────────────────────────────────────────

def test_validate_build_on_none() -> None:
    NixosAnywhere._validate_build_on(None)


@pytest.mark.parametrize("mode", ["auto", "remote", "local"])
def test_validate_build_on_valid(mode: str) -> None:
    NixosAnywhere._validate_build_on(mode)


def test_validate_build_on_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid build-on mode"):
        NixosAnywhere._validate_build_on("hybrid")


# ── Validation: hardware config backend ───────────────────────────────────────

def test_validate_hw_backend_none() -> None:
    NixosAnywhere._validate_hw_backend(None)


def test_validate_hw_backend_valid() -> None:
    NixosAnywhere._validate_hw_backend(("nixos-facter", "/tmp/hw.nix"))


def test_validate_hw_backend_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid hardware-config backend"):
        NixosAnywhere._validate_hw_backend(("invalid-backend", "/tmp/hw.nix"))


def test_validate_hw_backend_bad_type() -> None:
    with pytest.raises(TypeError, match="generate_hardware_config must be"):
        NixosAnywhere._validate_hw_backend("just-a-string")


# ── Validation: store_paths ───────────────────────────────────────────────────

def test_validate_store_paths_none() -> None:
    NixosAnywhere._validate_store_paths(None)


def test_validate_store_paths_valid() -> None:
    NixosAnywhere._validate_store_paths(
        ("/nix/store/abc-disko", "/nix/store/xyz-system")
    )


def test_validate_store_paths_not_nix_store() -> None:
    with pytest.raises(ValueError, match="must be /nix/store"):
        NixosAnywhere._validate_store_paths(("/tmp/foo", "/nix/store/bar"))


def test_validate_store_paths_wrong_type() -> None:
    with pytest.raises(TypeError, match="store_paths must be"):
        NixosAnywhere._validate_store_paths("just-one-path")


# ── Validation: flake / store-paths mutex ─────────────────────────────────────

def test_validate_flake_store_mutex_both_none() -> None:
    NixosAnywhere._validate_flake_store_mutex(None, None)


def test_validate_flake_store_mutex_flake_only() -> None:
    NixosAnywhere._validate_flake_store_mutex(".#host", None)


def test_validate_flake_store_mutex_store_only() -> None:
    NixosAnywhere._validate_flake_store_mutex(
        None, ("/nix/store/a", "/nix/store/b")
    )


def test_validate_flake_store_mutex_both_set() -> None:
    with pytest.raises(ValueError, match="mutually exclusive"):
        NixosAnywhere._validate_flake_store_mutex(
            ".#host", ("/nix/store/a", "/nix/store/b")
        )


# ── _build_command type extensions ───────────────────────────────────────────

class TestBuildCommandTypes:
    """Verify the extended type handling in :meth:`NixTool._build_command`."""

    def test_int_flag(self) -> None:
        nix = NixosAnywhere()
        cmd = nix._build_command("target", ssh_port=2222)
        assert "--ssh-port" in cmd
        assert "2222" in cmd
        idx = cmd.index("--ssh-port")
        assert cmd[idx + 1] == "2222"

    def test_path_flag(self) -> None:
        nix = NixosAnywhere()
        cmd = nix._build_command("target", extra_files=Path("/some/dir"))
        assert "--extra-files" in cmd
        assert "/some/dir" in cmd

    def test_tuple_flag(self) -> None:
        """tuple[str, ...] expands as ``--flag val1 val2 ...``."""
        nix = NixosAnywhere()
        cmd = nix._build_command(
            "target", store_paths=("/nix/store/a", "/nix/store/b")
        )
        assert "--store-paths" in cmd
        idx = cmd.index("--store-paths")
        assert cmd[idx + 1] == "/nix/store/a"
        assert cmd[idx + 2] == "/nix/store/b"

    def test_list_of_tuples(self) -> None:
        """list[tuple[str, str]] repeats ``--flag k v``."""
        nix = NixosAnywhere()
        cmd = nix._build_command(
            "target",
            option=[("key1", "val1"), ("key2", "val2")],
        )
        assert cmd.count("--option") == 2
        opt_idx = cmd.index("--option")
        assert cmd[opt_idx + 1] == "key1"
        assert cmd[opt_idx + 2] == "val1"
        opt_idx2 = cmd.index("--option", opt_idx + 1)
        assert cmd[opt_idx2 + 1] == "key2"
        assert cmd[opt_idx2 + 2] == "val2"

    def test_bool_false_skips(self) -> None:
        nix = NixosAnywhere()
        cmd = nix._build_command("target", debug=False)
        assert "--debug" not in cmd

    def test_bool_true_includes(self) -> None:
        nix = NixosAnywhere()
        cmd = nix._build_command("target", debug=True)
        assert "--debug" in cmd

    def test_trailing_underscore(self) -> None:
        """Trailing underscore on keyword (e.g. ``from_``) is stripped."""
        nix = NixosAnywhere()
        cmd = nix._build_command("target", from_="https://cache.example.com")
        assert "--from" in cmd
        assert "https://cache.example.com" in cmd


# ── deploy ────────────────────────────────────────────────────────────────────

@patch("nixos_deploy_tool.core.nixos_anywhere.subprocess.run")
def test_deploy_clears_known_hosts_before_running(mock_run) -> None:
    mock_run.return_value.returncode = 0

    nix = NixosAnywhere()
    nix.deploy(
        target="nixos@nixos",
        flake_attr="desktop",
        flake_root=Path("/fake/flake"),
    )

    assert mock_run.call_count >= 2
    assert mock_run.call_args_list[0] == call(
        ["ssh-keygen", "-R", "nixos"],
        capture_output=True,
        text=True,
    )


@patch("nixos_deploy_tool.core.nixos_anywhere.subprocess.run")
def test_deploy_includes_i_flag_when_key_provided(mock_run) -> None:
    mock_run.return_value.returncode = 0

    nix = NixosAnywhere()
    nix.deploy(
        target="nixos@nixos",
        flake_attr="desktop",
        flake_root=Path("/fake/flake"),
        ssh_key="/home/user/.ssh/id_ed25519",
    )

    nixos_anywhere_call = mock_run.call_args_list[-1]
    args = nixos_anywhere_call[0][0]
    assert "-i" in args
    assert "/home/user/.ssh/id_ed25519" in args
    assert "--no-ssh-copy-id" not in args


@patch("nixos_deploy_tool.core.nixos_anywhere.subprocess.run")
def test_deploy_extra_args_appended(mock_run) -> None:
    mock_run.return_value.returncode = 0

    nix = NixosAnywhere()
    nix.deploy(
        target="nixos@nixos",
        flake_attr="desktop",
        flake_root=Path("/fake/flake"),
        extra_args=["--phases", "kexec,disko,install", "--debug"],
    )

    nixos_anywhere_call = mock_run.call_args_list[-1]
    args = nixos_anywhere_call[0][0]
    assert "--phases" in args
    assert "kexec,disko,install" in args
    assert args[-1] == "--debug"


@patch("nixos_deploy_tool.core.nixos_anywhere.subprocess.run")
def test_deploy_with_phases_typed(mock_run) -> None:
    """typed ``phases=`` parameter works."""
    mock_run.return_value.returncode = 0

    nix = NixosAnywhere()
    nix.deploy(
        target="nixos@nixos",
        flake_attr="desktop",
        flake_root=Path("/fake/flake"),
        phases="kexec,install,reboot",
    )

    nixos_anywhere_call = mock_run.call_args_list[-1]
    args = nixos_anywhere_call[0][0]
    assert "--phases" in args
    phases_idx = args.index("--phases")
    assert args[phases_idx + 1] == "kexec,install,reboot"


@patch("nixos_deploy_tool.core.nixos_anywhere.subprocess.run")
def test_deploy_with_disko_mode(mock_run) -> None:
    mock_run.return_value.returncode = 0

    nix = NixosAnywhere()
    nix.deploy(
        target="nixos@10.0.0.1",
        flake_attr="server",
        flake_root=Path("/flake"),
        disko_mode="mount",
    )

    nixos_anywhere_call = mock_run.call_args_list[-1]
    args = nixos_anywhere_call[0][0]
    assert "--disko-mode" in args
    mode_idx = args.index("--disko-mode")
    assert args[mode_idx + 1] == "mount"


@patch("nixos_deploy_tool.core.nixos_anywhere.subprocess.run")
def test_deploy_with_ssh_port(mock_run) -> None:
    mock_run.return_value.returncode = 0

    nix = NixosAnywhere()
    nix.deploy(
        target="nixos@host",
        flake_attr="host",
        flake_root=Path("/flake"),
        ssh_port=2222,
    )

    nixos_anywhere_call = mock_run.call_args_list[-1]
    args = nixos_anywhere_call[0][0]
    assert "--ssh-port" in args
    port_idx = args.index("--ssh-port")
    assert args[port_idx + 1] == "2222"


@patch("nixos_deploy_tool.core.nixos_anywhere.subprocess.run")
def test_deploy_with_multiple_options(mock_run) -> None:
    """list[tuple[str,str]] for ``--option`` produces repeated flags."""
    mock_run.return_value.returncode = 0

    nix = NixosAnywhere()
    nix.deploy(
        target="nixos@host",
        flake_attr="host",
        flake_root=Path("/flake"),
        nix_options=[("substituters", "https://cache.example.com")],
        print_build_logs=True,
        show_trace=True,
    )

    nixos_anywhere_call = mock_run.call_args_list[-1]
    args = nixos_anywhere_call[0][0]
    assert "--option" in args
    opt_idx = args.index("--option")
    assert args[opt_idx + 1] == "substituters"
    assert args[opt_idx + 2] == "https://cache.example.com"
    assert "--print-build-logs" in args
    assert "--show-trace" in args


@patch("nixos_deploy_tool.core.nixos_anywhere.subprocess.run")
def test_deploy_invalid_phases_raises(mock_run) -> None:
    nix = NixosAnywhere()
    with pytest.raises(ValueError, match="Invalid phase"):
        nix.deploy(
            target="nixos@host",
            flake_attr="host",
            flake_root=Path("/flake"),
            phases="kexec,bogus",
        )
    mock_run.assert_not_called()


@patch("nixos_deploy_tool.core.nixos_anywhere.subprocess.run")
def test_deploy_invalid_disko_mode_raises(mock_run) -> None:
    nix = NixosAnywhere()
    with pytest.raises(ValueError, match="Invalid disko mode"):
        nix.deploy(
            target="nixos@host",
            flake_attr="host",
            flake_root=Path("/flake"),
            disko_mode="destroy",
        )
    mock_run.assert_not_called()


@patch("nixos_deploy_tool.core.nixos_anywhere.subprocess.run")
def test_deploy_flake_store_mutex_raises(mock_run) -> None:
    nix = NixosAnywhere()
    with pytest.raises(ValueError, match="mutually exclusive"):
        nix.deploy(
            target="nixos@host",
            flake_attr="host",
            flake_root=Path("/flake"),
            store_paths=("/nix/store/a", "/nix/store/b"),
        )
    mock_run.assert_not_called()


@patch("nixos_deploy_tool.core.nixos_anywhere.subprocess.Popen")
@patch("nixos_deploy_tool.core.nixos_anywhere.subprocess.run")
def test_deploy_streaming_callback(mock_run, mock_popen) -> None:
    import io

    mock_run.return_value = subprocess.CompletedProcess(
        args=["ssh-keygen", "-R", "host"], returncode=0, stdout=b"", stderr=b"",
    )
    mock_proc = mock_popen.return_value.__enter__.return_value
    mock_proc.stdout = io.StringIO("line1\nline2\n")
    mock_proc.wait.return_value = 0
    mock_proc.returncode = 0

    lines: list[str] = []
    nix = NixosAnywhere()
    result = nix.deploy(
        target="nixos@host",
        flake_attr="host",
        flake_root=Path("/flake"),
        on_output=lambda s: lines.append(s),
    )
    assert isinstance(result, int)
    assert result == 0
    assert lines == ["line1", "line2"]


def test_custom_binary() -> None:
    nix = NixosAnywhere(binary="nixos-anywhere-custom")
    assert nix.binary == "nixos-anywhere-custom"
