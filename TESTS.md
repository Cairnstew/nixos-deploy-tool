# Tests

Three-tier test suite with scoped fixtures and Nix integration tests.

## Layout

```
tests/
├── __init__.py              # Makes tests a package
├── conftest.py              # Root: CliRunner, shared fixtures
│
├── fixtures/                # Test data & mock infrastructure
│   ├── factories.py         #   make_deploy_config, make_wizard_state
│   ├── mocks.py             #   MockDeployService, MockNixRunner, MockFlakeIntrospector
│   └── mock_ssh.py          #   MockSshClient (lsblk, sgdisk, partition_exists, etc.)
│
├── utils/                   # Test helpers
│   ├── assertions.py        #   assert_ok
│   └── builders.py          #   build_success, build_error
│
├── unit/                    # Fast — no I/O, no services, no Nix
│   ├── conftest.py          #   ScreenHarness, tui_app_async fixture
│   ├── test_cli.py
│   ├── test_commands.py
│   ├── test_context.py
│   ├── test_deploy.py
│   ├── test_key_store.py
│   ├── test_models.py
│   ├── test_nixos_anywhere.py
│   ├── test_services.py
│   ├── test_app_constructor.py      # DeployToolApp edge cases
│   ├── test_wizard_state.py          # WizardState defaults + mutability
│   ├── test_tui_base.py              # BaseScreen/ListScreen/DetailScreen mixins
│   ├── test_tui_screens.py           # Per-screen composition + navigation
│   ├── test_tui_wizard.py            # Full-wizard integration pipelines
│   ├── test_tui_extra_coverage.py    # Edge cases, fallbacks, error paths
│   ├── test_wizard_host_advanced.py
│   ├── test_wizard_config_advanced.py
│   ├── test_wizard_disks_advanced.py
│   ├── test_wizard_manual_advanced.py
│   ├── test_wizard_partitions_advanced.py
│   ├── test_wizard_confirm.py
│   └── test_wizard_deploy_advanced.py
│
├── integration/            # CLI subprocess invocation
│   ├── conftest.py         #   Nix-dependent fixtures
│   ├── test_cli_invocation.py
│   └── test_example.py
│
├── nix_eval/               # Requires nix in PATH
│   ├── conftest.py
│   └── test_module_eval.py
│
└── nixos/                  # NixOS VM test fixtures (.nix files only)
    └── basic.nix
```

## Running subsets

```bash
pytest tests/unit/            # fast, no I/O (274 tests)
pytest tests/integration/     # CLI subprocess
pytest -m "not nix"           # skip Nix-dependent tests
pytest -m "tui"               # only TUI screen/wizard tests
pytest tests/nix_eval/ -m nix # only Nix eval tests
pytest tests/                 # everything
```

## Markers

| Marker | Scope | Skippable |
|--------|-------|-----------|
| `nix` | Tests requiring `nix` in PATH | `-m 'not nix'` |
| `integration` | CLI subprocess tests | `-m 'not integration'` |
| `tui` | Textual TUI screen tests | `-m 'not tui'` |

## Design decisions

- **Scoped conftest.py per tier.** Each tier has its own `conftest.py` so fixtures are scoped by tier.
- **`nix` marker on eval tests.** These need `nix` in PATH and evaluate real derivations.
- **`tui` marker on screen tests.** Uses `ScreenHarness` and `tui_app_async` fixture.
  Run without TUI tests when Textual isn't available.
- **NixOS VM tests are Nix-only.** They live in `tests/nixos/` as `.nix` fixtures read by
  `nix/vm-tests.nix`. No pytest files.
- **MockSshClient** simulates `lsblk --json` output, `sgdisk`, `mkfs`, and partition
  existence checks without SSH. Tests configure it via `partition_exists_results`,
  `created_partitions`, `mkfs_calls` on the shared `MockDeployService.ssh_client` instance.
- **`make_wizard_state()`** factory creates a pre-filled `WizardState` with test defaults
  (`host_name="test-host"`, `ssh_target="nixos@10.0.0.1"`, `config_source="flake"`).

## Testing by package layer

| Package layer | Test tier | Approach |
|---------------|-----------|----------|
| `models/` | `unit/` | Instantiate Pydantic models, assert serialisation |
| `services/` | `unit/` | Instantiate services with mock config, call methods |
| `commands/` | `unit/` | Assert BaseCommand subclass contract, handle_result |
| `cli/` | `unit/` + `integration/` | Typer CliRunner in unit, subprocess in integration |
| `textual_ui/` | `unit/` | ScreenHarness per screen, tui_app_async for full wizard flows |
| `exceptions/` | `unit/` | Instantiate and assert isinstance checks |
