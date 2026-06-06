# Change Heatmap

## Hot (changes every feature)

| File | Rationale |
|------|-----------|
| `src/nixos_deploy_tool/cli/commands/` | New command class + Typer sub-app |
| `src/nixos_deploy_tool/services/` | New service inheriting BaseService |
| `src/nixos_deploy_tool/core/` | New core wrapper |
| `nix/module.nix` | Every new NixOS module option |
| `.github/workflows/ci.yml` | Path filters |

## Warm (changes per major version)

| File | Rationale |
|------|-----------|
| `src/nixos_deploy_tool/models/config.py` | New config fields |
| `pyproject.toml` | New deps, version bump |
| `flake.nix` | New inputs or app entries |

## Cold (rarely changes)

| File | Rationale |
|------|-----------|
| `src/nixos_deploy_tool/exceptions.py` | Exception hierarchy is stable |
| `src/nixos_deploy_tool/cli/commands/base.py` | BaseCommand contract is stable |
| `src/nixos_deploy_tool/services/base.py` | BaseService contract is stable |
| `nix/default.nix` | Package builder is stable |
| `tests/conftest.py` | Fixture contracts are stable |

## Currently unused

| File | Rationale |
|------|-----------|
| `nix/boot-decrypt.nix` | Generated dynamically, not imported directly |
