# Contributing

## Prerequisites

- Nix (with flakes enabled)
- `just` (optional, for recipe shortcuts)

## Quick start

```bash
nix develop
```

## Development loop

1. Make changes to `src/` or `nix/`
2. Run `just check` to lint, typecheck, and test
3. Run `just nix-check` to verify flake evaluation
4. Commit and open a PR

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
