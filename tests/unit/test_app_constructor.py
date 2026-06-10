from __future__ import annotations

import pytest

from nixos_deploy_tool.cli.context import AppContext
from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.textual_ui.app import DeployToolApp


class TestDeployToolApp:
    def test_requires_flake_root(self) -> None:
        with pytest.raises(RuntimeError, match="config.flake_root"):
            DeployToolApp()

    def test_requires_context_with_config(self) -> None:
        ctx = AppContext()  # no config
        with pytest.raises(RuntimeError, match="config.flake_root"):
            DeployToolApp(context=ctx)

    def test_requires_flake_root_in_config(self) -> None:
        ctx = AppContext(config=DeployConfig())  # no flake_root
        with pytest.raises(RuntimeError, match="config.flake_root"):
            DeployToolApp(context=ctx)

    def test_constructs_with_valid_config(self) -> None:
        ctx = AppContext(config=DeployConfig(flake_root="/fake/project"))
        app = DeployToolApp(context=ctx)
        assert app.context is ctx
        assert app._svc is not None
        assert app._state is not None

    def test_state_overrides_applied(self) -> None:
        ctx = AppContext(config=DeployConfig(flake_root="/fake/project"))
        app = DeployToolApp(
            context=ctx,
            state_overrides={"host_name": "my-host"},
        )
        assert app._state.host_name == "my-host"

    def test_state_overrides_missing_partlabels(self) -> None:
        ctx = AppContext(config=DeployConfig(flake_root="/fake/project"))
        app = DeployToolApp(
            context=ctx,
            state_overrides={"missing_partlabels": ["disk-main-root"]},
        )
        assert app._state.missing_partlabels == ["disk-main-root"]

    def test_state_overrides_empty(self) -> None:
        ctx = AppContext(config=DeployConfig(flake_root="/fake/project"))
        app = DeployToolApp(context=ctx, state_overrides={})
        assert app._state.host_name == ""

    def test_on_mount_pushes_host_screen(self) -> None:
        ctx = AppContext(config=DeployConfig(flake_root="/fake/project"))
        app = DeployToolApp(context=ctx)
        assert len(app.screen_stack) == 0
        app.on_mount()
        assert len(app.screen_stack) == 1
