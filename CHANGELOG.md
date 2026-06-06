# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial project scaffold with uv2nix, Typer CLI, and Textual TUI.
- Nix flake with hermetic Python builds via uv2nix.
- NixOS module with activation script and systemd service.
- CI/CD with path-based change detection and reusable workflows.
- Pre-commit hooks, Justfile, and developer tooling.
- Three-tier test suite (unit, integration, Nix eval).
- NixOS VM integration tests.
- Documentation: quickstart, CLI reference, module reference, CI reference.
