# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed (structural refactor)

- **ABC contracts**: `BaseCommand`, `BaseService`, `BaseScreen`, `ListScreen`, `DetailScreen`,
  and `BaseRepository` now use `ABC` + `@abstractmethod` instead of `raise NotImplementedError` or
  empty defaults. Subclasses must implement abstract methods at definition time.

- **SubprocessRunner base**: New `core/_base.py` with `SubprocessRunner(ABC)` unifying subprocess
  error handling, logging, and streaming. Six core classes refactored to use it:
  `NixRunner`, `AgeRunner` (renamed from `AgeWrapper`), `ISOBuilder`, `NixosAnywhere`,
  `SshClient`. `TailscaleAPIClient` refactored to use `APIClient(ABC)`.

- **Dependency injection**: All service constructors accept optional core instances
  (`nixos_anywhere=None`, `flake=None`, etc.). Defaults inferred from config.
  CLI commands retrieve services via `AppContext._get_*_service()` (lazy init, cached).

- **Public service API**: `DeployService.list_hosts()`, `get_disko_devices()`,
  `get_disko_summary()`, `resolve_ssh_key()`, `build_extra_args()`, and
  `run_streaming()` (with `on_output`/`on_done` callbacks) replace all
  private-method access from TUI screens.

- **TUI consistency**: All wizard screens inherit from `BaseScreen`/`ListScreen` instead of
  raw `Screen[None]`. `DeployToolApp` injects `DeployService` + `WizardState` via constructor.
  `WizardDeployScreen` uses `run_streaming()` instead of raw `subprocess.run()`.

- **Repository trim**: `FlakeRepo` deleted. `AgenixCatalog` inherits from `BaseRepository(ABC)`.
  `FlakeIntrospector` gained `discover_hosts()`.

- **Exception expansion**: `CoreError`, `SubprocessError`, `APIError` added. `NixEvalError`
  now extends `SubprocessError`.

- **Test infrastructure**: `fixtures/factories.py`, `fixtures/mocks.py`, `utils/builders.py`,
  and `utils/assertions.py` filled with reusable helpers. `MockSubprocessRunner`,
  `MockNixRunner`, `MockFlakeIntrospector`, `MockDeployService` available for testing
  without monkey-patching.

### Added

- Initial project scaffold with uv2nix, Typer CLI, and Textual TUI.
- Nix flake with hermetic Python builds via uv2nix.
- NixOS module with activation script and systemd service.
- CI/CD with path-based change detection and reusable workflows.
- Pre-commit hooks, Justfile, and developer tooling.
- Three-tier test suite (unit, integration, Nix eval).
- NixOS VM integration tests.
- Documentation: quickstart, CLI reference, module reference, CI reference.
