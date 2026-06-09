from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Label

from nixos_deploy_tool.models.config import DeployConfig
from nixos_deploy_tool.services.deploy import DeployService
from nixos_deploy_tool.textual_ui.wizard_state import WizardState


class WizardHostScreen(Screen[None]):
    CSS_PATH = "../styles/wizard.tcss"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "quit", "Quit"),
    ]

    def action_quit(self) -> None:
        self.app.exit()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Label("Select a host configuration to deploy:", classes="instruction"),
            DataTable(id="hosts-table", cursor_type="row"),
        )
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#hosts-table", DataTable)
        table.add_columns("Host", "Flake Attribute")
        app = self.app
        ctx = getattr(app, "context", None)
        cfg = ctx.config if ctx else DeployConfig()
        svc = DeployService(cfg)
        hosts = svc._flake.list_host_configs()
        for h in hosts:
            table.add_row(h["name"], h["attr"])
        table.focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table = self.query_one("#hosts-table", DataTable)
        row = table.get_row(event.row_key)
        host = str(row[0])
        attr = str(row[1])
        state = WizardState(host_name=host, flake_attr=attr)
        from nixos_deploy_tool.textual_ui.screens.wizard_config import WizardConfigScreen
        self.app.push_screen(WizardConfigScreen(state))
