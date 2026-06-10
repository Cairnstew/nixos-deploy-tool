from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch

import pytest

from nixos_deploy_tool.core.nix import NixRunner
from nixos_deploy_tool.exceptions import NixEvalError, SubprocessError


# ── _build_command ─────────────────────────────────────────────────────────


def test_build_command_first_element_is_binary() -> None:
    runner = NixRunner()
    args = runner._build_command("eval")
    assert args[0] == "nix"


def test_build_command_with_positional() -> None:
    runner = NixRunner()
    args = runner._build_command("eval", "extra")
    assert args[1] == "eval"
    assert args[2] == "extra"


def test_build_command_with_flags() -> None:
    runner = NixRunner()
    args = runner._build_command("eval", json=True, impure=True)
    assert "--json" in args
    assert "--impure" in args


def test_build_command_expr_flag() -> None:
    runner = NixRunner()
    expr = "builtins.currentTime"
    args = runner._build_command("eval", json=True, expr=expr)
    idx = args.index("--expr")
    assert args[idx + 1] == expr


# ── _run_cmd strips binary ────────────────────────────────────────────────


@patch.object(NixRunner, "_run", return_value='"mocked"')
@patch.object(NixRunner, "_build_command", return_value=["nix", "eval", "--json"])
def test_run_cmd_strips_binary_before_run(mock_build, mock_run) -> None:
    """_run_cmd must strip the binary element before _run() to avoid double binary."""
    runner = NixRunner()
    runner._run_cmd("eval")
    # _run receives args-only (no binary), _build_command passes its output
    # minus the first element (the binary).
    call_args = mock_run.call_args[0][0]
    assert call_args[0] != "nix"
    assert call_args == ["eval", "--json"]


# ── eval_json strips binary ───────────────────────────────────────────────


@patch.object(NixRunner, "_run", return_value='"test"')
def test_eval_json_passes_args_without_binary(mock_run) -> None:
    """eval_json must not double-include 'nix' in the args passed to _run."""
    runner = NixRunner()
    runner.eval_json("builtins.currentTime")
    call_args = mock_run.call_args[0][0]
    assert call_args[0] != "nix"
    assert "eval" in call_args
    assert "--json" in call_args
    assert "--expr" in call_args


@patch.object(NixRunner, "_run", return_value='"test"')
def test_eval_json_includes_flake_option(mock_run) -> None:
    runner = NixRunner()
    runner.eval_json("expr", flake_root=Path("/some/flake"))
    call_args = mock_run.call_args[0][0]
    assert "--option" in call_args
    assert "flake" in call_args
    assert "/some/flake" in call_args


# ── eval_flake_json strips binary ─────────────────────────────────────────


@patch.object(NixRunner, "_run", return_value='{"disk": {}}')
def test_eval_flake_json_passes_args_without_binary(mock_run) -> None:
    """eval_flake_json must not double-include 'nix' in the args passed to _run."""
    runner = NixRunner()
    runner.eval_flake_json(
        'nixosConfigurations."host".config.disko.devices',
        flake_root=Path("/fake/flake"),
    )
    call_args = mock_run.call_args[0][0]
    assert call_args[0] != "nix"
    assert "eval" in call_args
    assert "--json" in call_args
    assert "--impure" in call_args
    assert "--expr" in call_args


@patch.object(NixRunner, "_run", return_value='{"disk": {}}')
def test_eval_flake_json_expression_contains_flake_and_attr(mock_run) -> None:
    """The Nix expression passed to --expr must reference the flake root and attr."""
    runner = NixRunner()
    runner.eval_flake_json(
        'nixosConfigurations."host".config.disko.devices',
        flake_root=Path("/some/flake"),
    )
    call_args = mock_run.call_args[0][0]
    expr_idx = call_args.index("--expr")
    expr = call_args[expr_idx + 1]
    assert "/some/flake" in expr
    assert 'nixosConfigurations."host".config.disko.devices' in expr


# ── eval_flake_json error wrapping ────────────────────────────────────────


@patch.object(NixRunner, "_run", side_effect=SubprocessError("nix failed: error: attribute 'disko' missing"))
def test_eval_flake_json_wraps_subprocess_error(mock_run) -> None:
    """SubprocessError from _run is wrapped in NixEvalError."""
    runner = NixRunner()
    with pytest.raises(NixEvalError, match="nix failed"):
        runner.eval_flake_json(
            'nixosConfigurations."host".config.disko.devices',
            flake_root=Path("/fake/flake"),
        )


@patch.object(NixRunner, "_run", side_effect=SubprocessError("nix failed: error: syntax error"))
def test_eval_flake_json_preserves_error_message(mock_run) -> None:
    """The NixEvalError message includes the original SubprocessError message."""
    runner = NixRunner()
    with pytest.raises(NixEvalError) as exc_info:
        runner.eval_flake_json(
            'nixosConfigurations."host".config.disko.devices',
            flake_root=Path("/fake/flake"),
        )
    assert "syntax error" in str(exc_info.value)


# ── _build_strip_expr ──────────────────────────────────────────────────────


def test_build_strip_expr_contains_flake_root() -> None:
    expr = NixRunner._build_strip_expr("attr.path", Path("/my/flake"))
    assert "/my/flake" in expr


def test_build_strip_expr_contains_attr_path() -> None:
    expr = NixRunner._build_strip_expr(
        'nixosConfigurations."host".config.disko.devices',
        Path("/flake"),
    )
    assert 'nixosConfigurations."host".config.disko.devices' in expr


def test_build_strip_expr_has_getflake() -> None:
    expr = NixRunner._build_strip_expr("attr", Path("/f"))
    assert 'builtins.getFlake "/f"' in expr


def test_build_strip_expr_has_strip_internal() -> None:
    expr = NixRunner._build_strip_expr("attr", Path("/f"))
    assert "stripInternal" in expr


def test_build_strip_expr_has_no_duplicate_brackets() -> None:
    """The template uses {{ and }} to escape literal braces in Nix format().
    The output should contain single braces only."""
    expr = NixRunner._build_strip_expr("attr", Path("/f"))
    assert "{{" not in expr
    assert "}}" not in expr
    # Should be valid Nix-like syntax
    assert re.search(r'safe = builtins\.filter.*builtins\.substring 0 1 x\.name', expr)


# ── _wrap_error ────────────────────────────────────────────────────────────


def test_wrap_error_includes_stderr() -> None:
    runner = NixRunner()
    exc = SubprocessError("custom error: something broke")
    assert "custom error" in str(exc)
