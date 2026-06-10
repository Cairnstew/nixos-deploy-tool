from __future__ import annotations

from textual.app import App
from textual.screen import Screen

from nixos_deploy_tool.cli.context import AppContext
from nixos_deploy_tool.cli.logging import setup_logging
from nixos_deploy_tool.textual_ui.screens.wizard_host import WizardHostScreen
from nixos_deploy_tool.textual_ui.wizard_state import WizardState


class DeployToolApp(App[Screen[None]]):
    SCREENS = {
        "wizard_host": WizardHostScreen,  # type: ignore[dict-item]
    }

    def __init__(
        self,
        context: AppContext | None = None,
        state_overrides: dict[str, object] | None = None,
    ) -> None:
        super().__init__()
        if context is None or context.config is None or not context.config.flake_root:
            raise RuntimeError(
                "DeployToolApp requires an AppContext with config.flake_root set. "
                "Call: DeployToolApp(context=AppContext(config=DeployConfig(...)))"
            )
        self.context = context
        setup_logging(context.config, verbose=context.verbose)
        self._svc = context._get_deploy_service()
        state = WizardState()
        if state_overrides:
            for key, value in state_overrides.items():
                setattr(state, key, value)
        self._state = state

    def on_mount(self) -> None:
        self.push_screen(WizardHostScreen(self._svc, self._state))


def run_tui(
    context: AppContext | None = None,
    state_overrides: dict[str, object] | None = None,
) -> None:
    app = DeployToolApp(context=context, state_overrides=state_overrides)
    app.run()
