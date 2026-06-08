from __future__ import annotations

from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.models.result import SuccessResult, ErrorResult


def test_deployconfig_defaults() -> None:
    cfg = DeployConfig()
    assert cfg.log_level == "info"
    assert cfg.live_iso_user == "nixos"


def test_deployconfig_serialise() -> None:
    cfg = DeployConfig(log_level="debug")
    d = cfg.model_dump()
    assert d["log_level"] == "debug"


def test_deployconfig_default_extra_args_defaults_to_empty_list() -> None:
    cfg = DeployConfig()
    assert cfg.default_extra_args == []


def test_deployconfig_skip_disko_defaults_to_false() -> None:
    cfg = DeployConfig()
    assert cfg.skip_disko is False


def test_deployconfig_disko_mode_defaults_to_none() -> None:
    cfg = DeployConfig()
    assert cfg.disko_mode is None


def test_deployconfig_auto_detect_disko_defaults_to_false() -> None:
    cfg = DeployConfig()
    assert cfg.auto_detect_disko is False


def test_success_result_defaults() -> None:
    r = SuccessResult(message="done")
    assert r.ok is True
    assert r.message == "done"


def test_error_result_defaults() -> None:
    r = ErrorResult(message="fail")
    assert r.ok is False
    assert r.message == "fail"


def test_error_result_has_error_type() -> None:
    r = ErrorResult(message="not found", error_type="not_found")
    assert r.error_type == "not_found"
