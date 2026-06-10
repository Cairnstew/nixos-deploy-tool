from __future__ import annotations

import asyncio
import threading

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Label, Select, Static

from nixos_deploy_tool.services.deploy import DeployService
from nixos_deploy_tool.textual_ui.base import BaseScreen
from nixos_deploy_tool.textual_ui.screens.wizard_deploy import WizardDeployScreen
from nixos_deploy_tool.textual_ui.wizard_state import WizardState


class WizardPartitionScreen(BaseScreen):
    CSS_PATH = "../styles/wizard.tcss"

    def __init__(self, svc: DeployService, state: WizardState) -> None:
        super().__init__()
        self._svc = svc
        self._state = state
        self.creation_done = asyncio.Event()
        self._part_choices: dict[str, str] = {}
        self._pending_creation: list[str] = []

    def compose_content(self) -> ComposeResult:
        yield Vertical(
            Label("Partition Configuration", classes="title"),
            Static(
                f"Target: {self._state.ssh_target}",
                id="intro",
            ),
            Vertical(id="part-choices-container"),
            Horizontal(
                Button("Create Selected & Deploy", id="create-deploy", variant="primary"),
                Button("Use Flake Layout", id="use-flake", variant="default"),
                Button("Skip All & Deploy", id="skip-deploy", variant="default"),
                Button("Back", id="back", variant="default"),
                classes="button-row",
                id="action-buttons",
            ),
            Static("", id="status"),
        )

    async def on_mount(self) -> None:
        self._loop = asyncio.get_running_loop()
        self.creation_done.clear()
        container = self.query_one("#part-choices-container", Vertical)
        if self._state.missing_partlabels:
            for label in self._state.missing_partlabels:
                self._part_choices[label] = "create"
                row = Horizontal(
                    Label(f"  {label}", classes="part-label"),
                    Select(
                        options=[("Create", "create"), ("Skip", "skip")],
                        value="create",
                        id=f"part-{label}",
                    ),
                )
                await container.mount(row)
        elif self._state.disko_disk_overrides:
            self._load_from_flake()
            return
        else:
            await container.mount(
                Static(
                    "No partitions detected. "
                    "Click 'Use Flake Layout' to load partitions from your flake config, "
                    "or 'Skip All & Deploy' to proceed without creating partitions."
                )
            )
        if self._state.create_partitions:
            self._create_selected()
            return

    def on_select_changed(self, event: Select.Changed) -> None:
        prefix = "part-"
        if event.select.id and event.select.id.startswith(prefix):
            label = event.select.id[len(prefix):]
            self._part_choices[label] = str(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create-deploy":
            self._preview_creation()
        elif event.button.id == "confirm-preview":
            self._confirm_creation()
        elif event.button.id == "cancel-preview":
            self._cancel_preview()
        elif event.button.id == "use-flake":
            self._load_from_flake()
        elif event.button.id == "skip-deploy":
            self._go_to_deploy()
        elif event.button.id == "back":
            self.app.pop_screen()

    def _create_selected(self) -> None:
        """Create only the partitions marked for creation (no confirmation)."""
        to_create = [lbl for lbl, choice in self._part_choices.items() if choice == "create"]
        if not to_create:
            self._go_to_deploy()
            return
        self.query_one("#create-deploy", Button).disabled = True
        self.query_one("#skip-deploy", Button).disabled = True
        self.query_one("#back", Button).disabled = True
        self.query_one("#status", Static).update("Creating partitions...")
        thread = threading.Thread(target=self._create_thread, args=(to_create,), daemon=True)
        thread.start()

    # ── Preview & confirm creation ────────────────────────────────

    def _preview_creation(self) -> None:
        """Probe target disk and preview predicted device paths before creating."""
        to_create = [lbl for lbl, choice in self._part_choices.items() if choice == "create"]
        if not to_create:
            self._go_to_deploy()
            return
        self._pending_creation = to_create
        self.query_one("#create-deploy", Button).disabled = True
        self.query_one("#skip-deploy", Button).disabled = True
        self.query_one("#back", Button).disabled = True
        self.query_one("#status", Static).update("Probing target disk...")
        thread = threading.Thread(target=self._probe_thread, args=(to_create,), daemon=True)
        thread.start()

    def _probe_thread(self, to_create: list[str]) -> None:
        """SSH into target, probe partition table, build preview of what will be created."""
        try:
            ssh = self._svc.create_ssh(self._state.ssh_target, self._state.ssh_key)
            devices_raw = self._svc.get_disko_devices(self._state.host_name)
        except Exception:
            self.app.call_from_thread(
                self.query_one("#status", Static).update,
                "Error: could not probe target disk",
            )
            self.app.call_from_thread(self._reenable_buttons)
            return

        try:
            parts: list[str] = []
            for disk_name, device in self._state.disko_disk_overrides.items():
                result = ssh.run(f"sgdisk --print {device}")
                existing: set[int] = set()
                for line in result.stdout.split("\n"):
                    line = line.strip()
                    if line and line.split()[0].isdigit():
                        existing.add(int(line.split()[0]))

                next_num = 1
                while next_num in existing:
                    next_num += 1

                disk = devices_raw.get("disk", {}).get(disk_name, {})
                for part in (disk.get("content", {}).get("partitions", []) or []):
                    part_name = part.get("name", "")
                    label = f"disk-{disk_name}-{part_name}"
                    if label in to_create:
                        predicted = f"{device}p{next_num}" if device[-1].isdigit() else f"{device}{next_num}"
                        fstype = part.get("content", {}).get("format", "ext4")
                        parts.append(f"  {predicted}  →  {part_name} ({fstype})")
                        next_num += 1

            if not parts:
                self.app.call_from_thread(
                    self.query_one("#status", Static).update,
                    "No partitions found to create",
                )
                self.app.call_from_thread(self._reenable_buttons)
                return

            text = "Partitions to create:\n" + "\n".join(parts)
            self.app.call_from_thread(self._show_preview, text)
        except Exception as exc:
            self.app.call_from_thread(
                self.query_one("#status", Static).update,
                f"Error probing target: {exc}",
            )
            self.app.call_from_thread(self._reenable_buttons)

    def _show_preview(self, text: str) -> None:
        if not self._pending_creation:
            return
        self.query_one("#status", Static).update(text)
        row = self.query_one("#action-buttons", Horizontal)
        row.remove_children()
        row.mount(Button("Confirm & Deploy", id="confirm-preview", variant="primary"))
        row.mount(Button("Cancel", id="cancel-preview"))

    def _confirm_creation(self) -> None:
        self._restore_action_buttons()
        self._create_selected()

    def _cancel_preview(self) -> None:
        self._pending_creation = []
        self._restore_action_buttons()
        self.query_one("#status", Static).update("")

    def _restore_action_buttons(self) -> None:
        row = self.query_one("#action-buttons", Horizontal)
        row.remove_children()
        row.mount(Button("Create Selected & Deploy", id="create-deploy", variant="primary"))
        row.mount(Button("Use Flake Layout", id="use-flake", variant="default"))
        row.mount(Button("Skip All & Deploy", id="skip-deploy", variant="default"))
        row.mount(Button("Back", id="back", variant="default"))

    def _create_thread(self, to_create: list[str]) -> None:
        try:
            devices_raw = self._svc.get_disko_devices(self._state.host_name)
        except Exception:
            self.app.call_from_thread(
                self.query_one("#status", Static).update,
                "Error: could not evaluate disko config",
            )
            self.app.call_from_thread(self._reenable_buttons)
            return

        ssh = self._svc.create_ssh(self._state.ssh_target, self._state.ssh_key)
        for disk_name, disk in devices_raw.get("disk", {}).items():
            device = self._state.disko_disk_overrides.get(disk_name, disk.get("device", ""))
            for part in (disk.get("content", {}).get("partitions", []) or []):
                part_name = part.get("name", "")
                label = f"disk-{disk_name}-{part_name}"
                if label in to_create:
                    self.app.call_from_thread(
                        self.query_one("#status", Static).update,
                        f"Creating partition '{label}' on {device}...",
                    )
                    try:
                        ssh.create_partition(device, label)
                        fstype = part.get("content", {}).get("format", "") or "ext4"
                        part_path = ssh.path_for_partlabel(label)
                        if part_path:
                            ssh.mkfs(part_path, fstype, label)
                    except RuntimeError as exc:
                        self.app.call_from_thread(
                            self.query_one("#status", Static).update,
                            f"Failed to create {label}: {exc}",
                        )
                        self.app.call_from_thread(self._reenable_buttons)
                        return

        self.app.call_from_thread(
            self.query_one("#status", Static).update,
            "Selected partitions created successfully",
        )
        self.app.call_from_thread(self._go_to_deploy)
        self._loop.call_soon_threadsafe(self.creation_done.set)

    def _load_from_flake(self) -> None:
        """Load partition layout from flake in a background thread."""
        if not self._state.disko_disk_overrides:
            self.query_one("#status", Static).update("No target disk selected")
            return
        self.query_one("#status", Static).update("Evaluating flake disko config...")
        self.query_one("#use-flake", Button).disabled = True
        thread = threading.Thread(target=self._load_from_flake_thread, daemon=True)
        thread.start()

    def _load_from_flake_thread(self) -> None:
        try:
            devices_raw = self._svc.get_disko_devices(self._state.host_name)
        except Exception:
            self.app.call_from_thread(
                self.query_one("#status", Static).update,
                "Could not evaluate flake disko config",
            )
            self.app.call_from_thread(self._reenable_buttons)
            return

        disk_name = next(iter(self._state.disko_disk_overrides.keys()), "")
        missing: list[str] = []
        for name, disk in devices_raw.get("disk", {}).items():
            if disk_name and name != disk_name:
                continue
            for part in (disk.get("content", {}).get("partitions", []) or []):
                pname = part.get("name", "")
                label = f"disk-{name}-{pname}"
                missing.append(label)

        if not missing:
            self.app.call_from_thread(
                self.query_one("#status", Static).update,
                "No partitions defined in flake config for this disk",
            )
            self.app.call_from_thread(self._reenable_buttons)
            return

        self._state.missing_partlabels = missing
        self._part_choices = {lbl: "create" for lbl in missing}
        self.app.call_from_thread(self._rebuild_partition_choices, missing)

    def _rebuild_partition_choices(self, missing: list[str]) -> None:
        container = self.query_one("#part-choices-container", Vertical)
        container.remove_children()
        for label in missing:
            self._part_choices[label] = "create"
            row = Horizontal(
                Label(f"  {label}", classes="part-label"),
                Select(
                    options=[("Create", "create"), ("Skip", "skip")],
                    value="create",
                    id=f"part-{label}",
                ),
            )
            container.mount(row)
        self.query_one("#status", Static).update(f"Loaded {len(missing)} partition(s) from flake")
        self.query_one("#use-flake", Button).disabled = False

    def _reenable_buttons(self) -> None:
        self.query_one("#create-deploy", Button).disabled = False
        self.query_one("#skip-deploy", Button).disabled = False
        self.query_one("#back", Button).disabled = False

    def _go_to_deploy(self) -> None:
        self.app.push_screen(WizardDeployScreen(self._svc, self._state))
