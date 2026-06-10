# Project Structure

```
.
├── .github/                     # CI/CD & dependency management
│   ├── actions/
│   │   └── setup-nix/
│   │       └── action.yml       #   Reusable: Nix installer + cache + uv
│   └── workflows/
│       ├── ci.yml               #   Orchestrator — path detection, fan-out
│       ├── lint.yml             #   Reusable — ruff (format + lint)
│       ├── typecheck.yml        #   Reusable — mypy
│       ├── test-unit.yml        #   Reusable — pytest unit + coverage
│       ├── test-integration.yml #   Reusable — pytest integration (soft-fail)
│       ├── nix.yml              #   Reusable — flake check + build
│       ├── audit.yml            #   Reusable — pip-audit + bandit
│       ├── vm-test.yml          #   Reusable — NixOS VM tests
│       ├── release.yml          #   Tag v* — Nix build, PyPI OIDC, GH release
│       └── update-flake-lock.yml #  Weekly — automated flake.lock bump
│
├── flake.nix                 # Nix flake — thin orchestrator, delegates to nix/
├── flake.lock                # Nix lock file — pins all flake input versions
├── pyproject.toml            # Python project metadata & dependency declarations
├── uv.lock                   # uv lock file — exact dependency resolution, drives uv2nix overlay
├── AGENTS.md                 # Instructions for AI coding agents
├── GOTCHAS.md                # Common pitfalls
├── HEATMAP.md                # Complexity/fragility heatmap
├── STRUCTURE.md              # This file
├── README.md                 # Project readme
├── CHANGELOG.md              # Release changelog
├── CONTRIBUTING.md           # Contribution guide
├── RELEASE.md                # Release process
├── TESTS.md                  # Test tier layout and conventions
├── UV2NIX.md                 # uv2nix reference & lookup table
├── .pre-commit-config.yaml   # Pre-commit hooks (ruff, mypy, nixpkgs-fmt)
├── Justfile                  # Developer command shortcuts
├── .python-version           # Python version pin (3.12)
│
├── nix/                      # Nix building blocks
│   ├── default.nix           #   Package derivation (mkApplication)
│   ├── module.nix            #   NixOS module — activation script + systemd service
│   ├── home-module.nix       #   Home Manager module — user env package
│   ├── boot-decrypt.nix      #   Boot-time age decrypt service generator
│   └── vm-tests.nix          #   NixOS VM integration tests
│
├── src/
│   └── nixos_deploy_tool/        # Application package
│       ├── __init__.py           #   Public API + version
│       ├── __main__.py           #   python -m nixos_deploy_tool
│       ├── py.typed              #   PEP 561 marker
│       ├── exceptions.py         #   NixosDeployError hierarchy
│       ├── models/
│       │   ├── __init__.py
│       │   ├── config.py         #   ISOConfig, HostConfig, DeployConfig, SecretInjection
│       │   └── result.py         #   BaseResult, SuccessResult, ErrorResult
│       ├── services/
│       │   ├── __init__.py
│       │   ├── base.py           #   BaseService
│       │   ├── iso.py            #   ISOService
│       │   ├── deploy.py         #   DeployService
│       │   ├── tailscale.py      #   TailscaleService
│       │   └── secrets.py        #   SecretService
│       ├── core/
│       │   ├── __init__.py
│       │   ├── _base.py          #   SubprocessRunner, APIClient — ABCs
│       │   ├── nix_tool.py       #   NixTool — declarative Nix CLI base
│       │   ├── age.py            #   AgeRunner — age CLI wrapper
│       │   ├── flake.py          #   FlakeIntrospector — nix flake show
│       │   ├── nix.py            #   NixRunner — nix build/eval
│       │   ├── nixos_anywhere.py #   NixosAnywhere — nixos-anywhere wrapper
│       │   ├── tailscale_api.py  #   TailscaleAPIClient — REST API client
│       │   └── iso_builder.py    #   ISOBuilder — ISO generation
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── main.py           #   Typer app + callback
│       │   ├── context.py        #   AppContext dataclass
│       │   └── commands/
│       │       ├── __init__.py
│       │       ├── base.py       #   BaseCommand
│       │       ├── iso.py        #   ISO commands (build, list, rotate-keys, info)
│       │       ├── deploy.py     #   Deploy commands (run, wizard, with-keys, test)
│       │       ├── tailscale.py  #   Tailscale commands (auth-key, status)
│       │       └── secrets.py    #   Secrets commands (list, decrypt, inject, rekey)
│       ├── textual_ui/           #   TUI package (Textual)
│       │   ├── __init__.py
│       │   ├── app.py            #   DeployToolApp
│       │   ├── base.py           #   BaseScreen, ListScreen, DetailScreen
│       │   ├── actions.py        #   Mixins: LoggingMixin, RefreshMixin, SelectionMixin, NavigationMixin
│       │   ├── screens/
│       │   │   ├── __init__.py
│       │   │   ├── main.py       #   Dashboard
│       │   │   ├── iso_build.py  #   ISO build screen
│       │   │   ├── deploy_wizard.py # Deploy wizard screen
│       │   │   └── secrets.py    #   Secrets list screen
│       │   └── styles/
│       │       ├── base.tcss
│       │       └── main.tcss
│       └── repositories/
│           ├── __init__.py
│           ├── _base.py          #   BaseRepository ABC
│           ├── flake_repo.py     #   Discover hosts, outputs, hardware configs
│           └── agenix_catalog.py #   Parse secrets.nix, list .age files
│
├── tests/
│   ├── conftest.py               #   Root: CliRunner, shared fixtures
│   ├── unit/                     #   Fast, no I/O — mocks & fakes only
│   │   ├── conftest.py
│   │   ├── test_models.py
│   │   ├── test_services.py
│   │   ├── test_commands.py
│   │   ├── test_cli.py
│   │   ├── test_tui_base.py
│   │   └── test_context.py
│   ├── integration/              #   CLI subprocess invocation
│   │   ├── conftest.py
│   │   └── test_cli_invocation.py
│   ├── nix_eval/                 #   Nix eval tests (require nix in PATH)
│   │   ├── conftest.py
│   │   └── test_module_eval.py
│   └── nixos/                    #   NixOS VM test fixtures
│       └── basic.nix
│
├── docs/
│   ├── reference/
│   │   ├── cli.md
│   │   ├── module.md
│   │   └── ci.md
│   └── guides/
│       ├── quickstart.md
│       └── nixos-integration.md
│
├── .envrc                    # direnv: use flake
├── .gitignore                # Git ignore rules
└── uv.lock.example           # Example lock file for bootstrapping
```

## Class Hierarchy

```
# ── Core domain models (src/nixos_deploy_tool/models/) ───────────────────

BaseModel (pydantic.BaseModel)
  ├── ISOConfig
  ├── HostConfig
  ├── DeployConfig
  ├── SecretInjection
  └── TailscaleAuthKeyConfig

BaseResult (pydantic.BaseModel)
  ├── SuccessResult
  └── ErrorResult

# ── CLI context (src/nixos_deploy_tool/cli/) ──────────────────────────────

AppContext (dataclass)
  # fields: verbose, flake_root, config (DeployConfig)
  # methods: _get_deploy_service(), _get_iso_service(), etc. (lazy init)

# ── Abstract base classes (ABCs) ──────────────────────────────────────────

ABC
  ├── BaseCommand          # run() -> BaseResult [abstract], execute() [template]
  ├── BaseService          # config, logger; on_start(), on_stop() [hooks]
  ├── BaseRepository       # list(), get() [abstract]
  ├── SubprocessRunner     # _run() [shared impl], _wrap_error() [abstract]
  └── APIClient             # _get/_post/_delete [shared impl], _auth_headers() [abstract]

# ── CLI commands (src/nixos_deploy_tool/cli/commands/) ────────────────────

BaseCommand(ABC)
  ├── run() -> BaseResult                    [@abstractmethod]
  ├── execute() -> None                      [template — calls run(), catch, handle_result]
  ├── handle_result(r: BaseResult) -> None   [concrete — prints or exits]
  └── abort(msg: str) -> None               [concrete — red message + typer.Exit(1)]
      ├── ISOBuildCommand(BaseCommand)
      ├── ISOListCommand(BaseCommand)
      ├── ISORotateKeysCommand(BaseCommand)
      ├── ISOInfoCommand(BaseCommand)
      ├── DeployRunCommand(BaseCommand)
      ├── DeployWizardCommand(BaseCommand)
      ├── DeployWithKeysCommand(BaseCommand)
      ├── DeployTestCommand(BaseCommand)
      ├── AuthKeyCreateCommand(BaseCommand)
      ├── AuthKeyListCommand(BaseCommand)
      ├── AuthKeyRevokeCommand(BaseCommand)
      ├── StatusCommand(BaseCommand)
      ├── SecretsListCommand(BaseCommand)
      ├── SecretsDecryptCommand(BaseCommand)
      ├── SecretsInjectCommand(BaseCommand)
      └── SecretsRekeyCommand(BaseCommand)

# ── Textual TUI (src/nixos_deploy_tool/textual_ui/) ───────────────────────

LoggingMixin, RefreshMixin, SelectionMixin, NavigationMixin

BaseScreen(Screen, LoggingMixin)
  compose_content() -> ComposeResult       [@abstractmethod]
  ├── ListScreen(BaseScreen, RefreshMixin, SelectionMixin)
  │     load_rows() -> list[tuple[...]]    [@abstractmethod]
  └── DetailScreen(BaseScreen, NavigationMixin)
        load_detail(key) -> str            [@abstractmethod]

DeployToolApp(App)
  # Creates services once via AppContext, injects into all screens
  # WizardState flows as mutable singleton through screen constructors

# ── TUI screens (src/nixos_deploy_tool/textual_ui/screens/) ──────────────

BaseScreen
  ├── MainScreen(BaseScreen)               # Dashboard
  ├── WizardHostScreen(ListScreen)         # Host selection via DataTable
  ├── WizardConfigScreen(BaseScreen)       # Config + partition validation
  ├── WizardPartitionScreen(BaseScreen)    # Partition creation
  └── WizardDeployScreen(BaseScreen)       # Streaming deploy output

# ── Services (src/nixos_deploy_tool/services/) ────────────────────────────

BaseService(ABC)
  ├── ISOService(BaseService)
  ├── DeployService(BaseService)           # + list_hosts, get_disko_devices, run_streaming
  ├── TailscaleService(BaseService)
  └── SecretService(BaseService)

# ── Core (src/nixos_deploy_tool/core/) ────────────────────────────────────

SubprocessRunner(ABC)        [core/_base.py]
  ├── NixTool(ABC)            [core/nix_tool.py]   — declarative Nix CLI base
  │   ├── NixRunner           [core/nix.py]
  │   ├── ISOBuilder          [core/iso_builder.py]
  │   └── NixosAnywhere       [core/nixos_anywhere.py]
  ├── AgeRunner               [core/age.py]
  └── SshClient               [core/ssh.py]

APIClient(ABC)               [core/_base.py]
  └── TailscaleAPIClient     [core/tailscale_api.py]

Standalone:
  ├── FlakeIntrospector      [core/flake.py]
  └── KeyStore               [core/key_store.py]

# ── Repositories (src/nixos_deploy_tool/repositories/) ────────────────────

BaseRepository(ABC)
  └── AgenixCatalog(BaseRepository)

# ── Exceptions (src/nixos_deploy_tool/exceptions.py) ──────────────────────

NixosDeployError(Exception)
  ├── CoreError(NixosDeployError)
  │     ├── SubprocessError(CoreError)
  │     │     ├── NixEvalError(SubprocessError)
  │     │     ├── ISOBuildError(SubprocessError)
  │     │     ├── DeployRuntimeError(SubprocessError)
  │     │     └── SecretError(SubprocessError)
  │     └── APIError(CoreError)
  │           └── TailscaleAPIError(APIError)
```

## Dependency Injection

Services accept optional core instances in their constructor.
CLI commands retrieve services via AppContext._get_*_service() (lazy init, cached).
TUI screens receive services + WizardState via constructor injection from DeployToolApp.

```
CLI callback → creates AppContext(config)
                        │
              ┌─────────┴──────────┐
              ▼                    ▼
        CLI command             TUI App
        ctx._get_service()     DeployToolApp(context)
              │                    │
              ▼                    ├── AppContext._get_deploy_service()
         DeployService             └── WizardHostScreen(svc, state)
              │                          │
         Services use                   ├── WizardConfigScreen(svc, state)
         DI for core deps               ├── WizardPartitionScreen(svc, state)
              │                          └── WizardDeployScreen(svc, state)
              ▼
         Core classes use
         SubprocessRunner / APIClient
```

## Architecture

```
pyproject.toml  ──uv add/lock──►  uv.lock
                                      │
                                      ▼
flake.nix  ──workspace.mkPyprojectOverlay──►  Nix overlay
  │                                                  │
  │  pyproject-build-systems.overlays.wheel ─────────┤
  │                                                  │
  └── composeManyExtensions ─────────────────────────► pythonSet
                                                           │
                                               ┌───────────┼───────────────────┐
                                               ▼           ▼                   ▼
                                    nix/default.nix   devShell           nix/module.nix
                                    (mkApplication)   (mkShell)          (systemd service)
```

## Nix Flake outputs

| Output | Source file | Description |
|--------|-------------|-------------|
| `packages.default` | `nix/default.nix` | Production build via `mkApplication` |
| `devShells.default` | `flake.nix` (inline) | Full dev environment with editable installs |
| `devShells.bootstrap` | `flake.nix` (inline) | Python + uv only (no uv2nix dependency) |
| `apps.default` | `flake.nix` | `nix run .` |
| `apps.build-iso` | `flake.nix` | `nix run .#build-iso` |
| `apps.deploy` | `flake.nix` | `nix run .#deploy` |
| `apps.deploy-wizard` | `flake.nix` | `nix run .#deploy-wizard` |
| `overlays.default` | `flake.nix` (inline) | Adds `nixos-deploy-tool` to `pkgs` |
| `nixosModules.default` | `nix/module.nix` | NixOS module with activation script |
| `homeManagerModules.default` | `nix/home-module.nix` | User environment package |
| `checks` | `flake.nix` (inline) | build, venv, format, app-help, module-eval |
| `vmTests` | `nix/vm-tests.nix` | NixOS VM integration tests |
