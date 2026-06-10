# Contributing

## Prerequisites

- Nix (with flakes enabled)
- `just` (optional, for recipe shortcuts)
- `uv` (available via `nix develop .#bootstrap`)

## Quick start

```bash
nix develop
```

## Development loop

1. Make changes to `src/` or `nix/`
2. Run `just check` to lint, typecheck, and test
3. Run `just nix-check` to verify flake evaluation
4. Commit and open a PR

## Available `just` commands

| Command | What it does |
|---------|-------------|
| `just check` | ruff lint + format, mypy, pytest unit+integration |
| `just nix-check` | `nix flake check` |
| `just test` | pytest unit + integration |
| `just test-all` | all tests including nix eval |
| `just test-tui` | only TUI screen/wizard tests |
| `just lint` | ruff check only |
| `just typecheck` | mypy only |

## Code style

- Python: ruff (format + lint) + mypy strict
- Nix: nixpkgs-fmt
- Pre-commit hooks enforce all of the above

## Adding a new CLI command

1. Create `src/nixos_deploy_tool/cli/commands/<name>.py` with a `BaseCommand` subclass
2. Register the Typer sub-app in `cli/main.py`
3. Add tests in `tests/unit/` and `tests/integration/`
4. Add docs in `docs/reference/cli.md`

## Adding a new NixOS module option

1. Add the option in `nix/module.nix`
2. Add a test in `flake.nix` (module-eval check)
3. Document in `docs/reference/module.md`

## Adding a new TUI screen

1. Create `src/nixos_deploy_tool/textual_ui/screens/<name>.py` inheriting from
   `BaseScreen` (or `ListScreen`/`DetailScreen`)
2. Constructor accepts `(svc: DeployService, state: WizardState)` plus optional
   extra params (e.g. `flake_devices` for disk/manual screens)
3. Export the screen class in `screens/__init__.py` and register in `__all__`
4. Add tests using `ScreenHarness` in `tests/unit/`
5. Add the screen to the wizard flow in the parent screen's button handler
