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
        super().on_mount()
        table.focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table = self.query_one("#hosts-table", DataTable)
        row = table.get_row(event.row_key)
        self._state.host_name = str(row[0])
        self._state.flake_attr = str(row[1])
        self.app.push_screen(WizardConfigScreen(self._svc, self._state))
