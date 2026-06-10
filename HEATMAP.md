# Change Heatmap

## Hot (changes every feature)

| File | Rationale |
|------|-----------|
| `src/nixos_deploy_tool/cli/commands/` | New command class + Typer sub-app |
| `src/nixos_deploy_tool/services/` | New service inheriting BaseService |
| `src/nixos_deploy_tool/core/` | New core wrapper |
| `src/nixos_deploy_tool/textual_ui/screens/` | New TUI screens (currently 11 screens) |
| `nix/module.nix` | Every new NixOS module option |
| `.github/workflows/ci.yml` | Path filters |

## Warm (changes per major version)

| File | Rationale |
|------|-----------|
| `src/nixos_deploy_tool/models/config.py` | New config fields |
| `pyproject.toml` | New deps, version bump |
| `flake.nix` | New inputs or app entries |
| `src/nixos_deploy_tool/cli/main.py` | Flake-root resolution, new sub-apps |
| `src/nixos_deploy_tool/textual_ui/screens/wizard_*.py` | Wizard screen logic (validation, partition mgmt) |
| `tests/unit/test_tui_screens.py` | New TUI screen tests |
| `tests/unit/test_tui_wizard.py` | Full-wizard integration tests |
| `tests/unit/test_wizard_*.py` | Per-screen advanced tests |
| `tests/fixtures/mocks.py` | Mock infrastructure for TUI tests |

## Cold (rarely changes)

| File | Rationale |
|------|-----------|
| `src/nixos_deploy_tool/core/_base.py` | SubprocessRunner/APIClient contracts are stable |
| `src/nixos_deploy_tool/exceptions.py` | Exception hierarchy is stable (add new leaf types only) |
| `src/nixos_deploy_tool/cli/commands/base.py` | BaseCommand contract is stable |
| `src/nixos_deploy_tool/services/base.py` | BaseService contract is stable |
| `src/nixos_deploy_tool/textual_ui/base.py` | BaseScreen/ListScreen/DetailScreen contracts are stable |
| `nix/default.nix` | Package builder is stable |
| `tests/conftest.py` | Root fixture contracts are stable |
| `tests/unit/conftest.py` | ScreenHarness, tui_app_async fixture |

## Currently unused

| File | Rationale |
|------|-----------|
| `nix/boot-decrypt.nix` | Generated dynamically, not imported directly |
| `src/nixos_deploy_tool/textual_ui/screens/iso_build.py` | Stub — not yet implemented |
| `src/nixos_deploy_tool/textual_ui/screens/deploy_wizard.py` | Stub — not yet implemented |
| `src/nixos_deploy_tool/textual_ui/screens/secrets.py` | Stub — not yet implemented |
