# Quickstart Guide

## Prerequisites

- Nix (with flakes enabled)

## 1. Enter the development environment

```bash
nix develop
```

This builds a Nix-managed venv with all dependencies. The `uv2nix-template` CLI is
available directly.

## 2. Try the CLI

```bash
uv2nix-template --help
uv2nix-template init
uv2nix-template generate
uv2nix-template validate
```

## 3. Run tests

```bash
pytest tests/unit/ -v
```

## 4. Check format and types

```bash
ruff check src/ tests/
ruff format --check src/ tests/
mypy src/
```

## 5. Build for production

```bash
nix build .#default
```

## 6. Use the TUI

```bash
python -m uv2nix_template.textual_ui
```

## Next steps

- Read the [CLI reference](../reference/cli.md) for command details
- Read the [Module reference](../reference/module.md) for NixOS integration
- Read the [CI reference](../reference/ci.md) for CI/CD workflow details
