# Agent Instructions

## About this project

Python project managed with `uv2nix` — uv's `uv.lock` drives Nix derivations via pure Nix code.
CLI/TUI for building NixOS live ISOs with embedded secrets, managing Tailscale auth keys via OAuth
API, and orchestrating nixos-anywhere deployments.

## Reference files

| File | Role |
|------|------|
| `STRUCTURE.md` | Project structure, architecture diagram, class hierarchy |
| `UV2NIX.md` | Full uv2nix reference & lookup table |
| `GOTCHAS.md` | Common pitfalls — read before debugging build issues |
| `HEATMAP.md` | Complexity/fragility heatmap of every project file |
| `TESTS.md` | Test tier layout, design decisions, and conventions |
| `CONTRIBUTING.md` | Contribution guide |
| `AGENTS.md` | This file — agent instructions |

## Key files

| File | Role |
|------|------|
| `flake.nix` | Nix flake — thin orchestrator, delegates to nix/ modules |
| `nix/default.nix` | Package derivation (mkApplication) |
| `nix/module.nix` | NixOS module (activation script + systemd service) |
| `nix/home-module.nix` | Home Manager module (user env) |
| `nix/boot-decrypt.nix` | Boot-time age decrypt service generator |
| `nix/vm-tests.nix` | NixOS VM integration tests |
| `pyproject.toml` | Python project metadata, dependencies |
| `uv.lock` | Lock file — drives the Nix overlay |
| `src/nixos_deploy_tool/` | Application package source |
| `src/nixos_deploy_tool/textual_ui/` | TUI package (Textual) |
| `tests/` | Test suite |
| `.github/workflows/` | CI/CD workflows |

## Workflows

### Add a dependency
```
nix develop .#bootstrap
uv add <package>
uv lock
```

### Enter dev environment
```
nix develop
```

### Build for production
```
nix build .#default
```

## Rules for agents

1. **Never edit `uv.lock` directly** — always use `uv lock` or `uv add`/`uv remove`.
2. **After editing `pyproject.toml`**, run `uv lock` to regenerate `uv.lock`.
3. **After editing `flake.nix`**, run `nix flake lock` to update `flake.lock`.
4. **Source filtering**: avoid filtering at the workspace root level (causes IFD + breaks editables).
   Filter per-package via overlay in `flake.nix`.
5. **Python version**: controlled by `requires-python` in `pyproject.toml` and `python = pkgs.python312`
   in `flake.nix`. Keep in sync.
6. **Adding Nix-specific overrides** — place them in `flake.nix` as an additional extension in
   `composeManyExtensions`. See `UV2NIX.md` > Overriding Packages for patterns.
7. **Class hierarchy** — follow the class hierarchy in `STRUCTURE.md`. New commands inherit from
   `BaseCommand(ABC)`, new services inherit from `BaseService(ABC)`, new screens inherit from
   `BaseScreen` / `ListScreen` / `DetailScreen`.
8. **New features**: add one file per layer (e.g. `models/user.py` + `services/user.py` +
   `cli/commands/user.py`), not feature folders.
9. **Abstract base classes**: Always use `ABC` + `@abstractmethod`, never `raise NotImplementedError`.
10. **Dependency injection**: Services accept optional core instances in their constructor
    (e.g., `DeployService(config, *, nixos_anywhere=None, flake=None, ...)`).
    Default to inferring them from config. This enables testing without monkey-patching.
11. **Services from AppContext**: CLI commands retrieve services via `self.ctx._get_deploy_service()`
    (or `_get_iso_service`, `_get_tailscale_service`, etc.), never `Service(config)` directly.
    TUI screens receive services via constructor injection from `DeployToolApp`.
12. **TUI screen pattern**: All screens inherit from `BaseScreen` (or `ListScreen`/`DetailScreen`) and
    accept `(svc: DeployService, state: WizardState)` in their constructor. Screens that need flake
    device info also accept `flake_devices: dict[str, Any]` (``WizardDiskScreen``, ``WizardManualScreen``).
    Screens call public service methods only — never `svc._private_method` or `svc._private_attr`.
13. **SSH interface**: `DeployService.create_ssh()` returns `SshProtocol`, not `SubprocessRunner`.
    Mock tests with `MockSshClient` which implements `SshProtocol`.
14. **Flake-root tilde expansion**: Always call `Path(x).expanduser().resolve()` on user-provided
    paths before passing to Nix's `builtins.getFlake` — it requires absolute paths and Nix doesn't
    expand tilde. Both `cli/main.py:_resolve_flake_root` and `services/deploy.py:__init__` do this.
