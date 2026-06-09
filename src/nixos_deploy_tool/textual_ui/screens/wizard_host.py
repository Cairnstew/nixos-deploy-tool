from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Label

from nixos_deploy_tool.services.deploy import DeployService
from nixos_deploy_tool.textual_ui.base import ListScreen
from nixos_deploy_tool.textual_ui.screens.wizard_config import WizardConfigScreen
from nixos_deploy_tool.textual_ui.wizard_state import WizardState


class WizardHostScreen(ListScreen):
    CSS_PATH = "../styles/wizard.tcss"

    def __init__(self, svc: DeployService, state: WizardState) -> None:
        super().__init__()
        self._svc = svc
        self._state = state

    def compose_content(self) -> ComposeResult:
        yield Vertical(
            Label("Select a host configuration to deploy:", classes="instruction"),
            DataTable(id="hosts-table", cursor_type="row"),
        )

    def load_rows(self) -> list[tuple[str, ...]]:
        return [(h["name"], h["attr"]) for h in self._svc.list_hosts()]

    def on_mount(self) -> None:
        table = self.query_one("#hosts-table", DataTable)
        table.add_columns("Host", "Flake Attribute")
        # If host is already set (from CLI flags), auto-advance
        if self._state.host_name:
            for h in self._svc.list_hosts():
                if h["name"] == self._state.host_name:
                    self._state.flake_attr = h.get("attr", self._state.host_name)
                    break
            self.app.push_screen(WizardConfigScreen(self._svc, self._state))
            return
        table.focus()
        # ListScreen.on_mount() is called automatically by Textual's
        # MRO dispatch — do NOT call super().on_mount() here or rows
        # will be inserted twice (once by super(), once by the MRO walk).

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table = self.query_one("#hosts-table", DataTable)
        row = table.get_row(event.row_key)
        self._state.host_name = str(row[0])
        self._state.flake_attr = str(row[1])
        self.app.push_screen(WizardConfigScreen(self._svc, self._state))
