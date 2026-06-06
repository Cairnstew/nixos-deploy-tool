# Tests

Three-tier test suite with scoped fixtures and Nix integration tests.

## Layout

```
tests/
├── conftest.py            # Root: CliRunner, shared fixtures
│
├── unit/                  # Fast — no I/O, no services, no Nix
│   ├── conftest.py        #   Mocks & fakes scoped here
│   ├── test_models.py
│   ├── test_services.py
│   ├── test_commands.py
│   ├── test_cli.py
│   ├── test_tui_base.py
│   └── test_context.py
│
├── integration/           # CLI subprocess invocation
│   ├── conftest.py       #   Nix-dependent fixtures
│   └── test_cli_invocation.py
│
├── nix_eval/              # Requires nix in PATH
│   ├── conftest.py
│   └── test_module_eval.py
│
└── nixos/                 # NixOS VM test fixtures (.nix files only)
    └── basic.nix
```

## Running subsets

```bash
pytest tests/unit/            # fast, no I/O
pytest tests/integration/     # CLI subprocess
pytest -m "not nix"           # skip Nix-dependent tests
pytest tests/nix_eval/ -m nix # only Nix eval tests
pytest tests/                 # everything
```

## Markers

| Marker | Scope | Skippable |
|--------|-------|-----------|
| `nix` | Tests requiring `nix` in PATH | `-m 'not nix'` |
| `integration` | CLI subprocess tests | `-m 'not integration'` |

## Design decisions

- **Scoped conftest.py per tier.** Each tier has its own `conftest.py` so fixtures are scoped by tier.
- **`nix` marker on eval tests.** These need `nix` in PATH and evaluate real derivations.
- **NixOS VM tests are Nix-only.** They live in `tests/nixos/` as `.nix` fixtures read by
  `nix/vm-tests.nix`. No pytest files.

## Testing by package layer

| Package layer | Test tier | Approach |
|---------------|-----------|----------|
| `models/` | `unit/` | Instantiate Pydantic models, assert serialisation |
| `services/` | `unit/` | Instantiate services with mock config, call methods |
| `commands/` | `unit/` | Assert BaseCommand subclass contract, handle_result |
| `cli/` | `unit/` + `integration/` | Typer CliRunner in unit, subprocess in integration |
| `textual_ui/` | `unit/` | Inheritance chain verification, mixin contract tests |
| `exceptions/` | `unit/` | Instantiate and assert isinstance checks |
