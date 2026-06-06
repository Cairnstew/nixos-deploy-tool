# uv2nix-template

Scaffold for building CLI/Nix/TUI tools with **uv2nix**, **Typer**, and **Textual**.

## Quick start

```bash
nix develop
uv2nix-template --help
```

## What you get

- **Hermetic builds** — full dependency tree locked via `uv.lock` and built by Nix
- **CLI** — Typer-based command interface with subcommands
- **TUI** — Optional Textual dashboard (keyboard-driven, hotkey-based)
- **NixOS module** — Activation script writes config, systemd service for production
- **CI/CD** — Path-based change detection, 7 reusable workflows, OIDC PyPI publish
- **Tests** — Three-tier suite (unit, integration, Nix eval) + NixOS VM tests

## Docs

- [Quickstart](docs/guides/quickstart.md)
- [CLI reference](docs/reference/cli.md)
- [Module reference](docs/reference/module.md)
- [CI reference](docs/reference/ci.md)
- [NixOS integration](docs/guides/nixos-integration.md)

## Development

```bash
just check      # lint + typecheck + unit tests
just nix-check  # flake validation
just nix-build  # nix build
```
