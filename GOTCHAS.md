# Gotchas

## uv2nix

### uv.lock required for evaluation
The flake won't evaluate without a `uv.lock`. Use `nix develop .#bootstrap` to get Python + uv, then run `uv lock`.

### uv.lock doesn't contain build systems
uv doesn't lock build systems. uv2nix uses `pyproject-build-systems` overlay to supply them.
If a build system isn't in that repo, you must supply it via an overlay.

### Don't use `uv run` inside the dev shell
`uv run` creates its own venv, defeating uv2nix's provisioning. The dev shell already makes all
scripts/entry points available directly.

### Don't filter sources at workspace root
`uv2nix.lib.workspace.loadWorkspace` reads from the workspace root at evaluation time. Filtering
there causes IFD and breaks editables. Filter per-package instead.

### Editable packages need `$REPO_ROOT`
The editable overlay uses `$REPO_ROOT` to locate the source tree. The dev shell `shellHook` sets it
via `git rev-parse --show-toplevel`. If you're not in a git repo, set it manually.

### `unset PYTHONPATH`
Nixpkgs Python builders set `PYTHONPATH`, which leaks into unrelated builds. Always unset it in the
dev shell `shellHook`.

## Python

### hatchling build backend
This template uses `hatchling`, not `setuptools`. The `build-system.requires` must be `["hatchling"]`
and the build backend `hatchling.build`.

### `model_dump()` empty list preservation
`pydantic.BaseModel.model_dump(exclude_defaults=True)` drops fields with `[]` default values.
Always use bare `model_dump()` when you need empty lists in the output.

### Typer sub-app registration
Each command module exposes a `typer.Typer()` instance named `app`. The main app adds them via
`app.add_typer(module.app, name="<subcommand>")`. The sub-app name must match the command name.

## Nix

### `nix flake check` and callPackage wrappers
`callPackage` wraps attrsets with `override`, `overrideDerivation`, and `__functionArgs`, which
`nix flake check` rejects as non-derivation attrs. Inline devShells and checks directly in
`flake.nix` instead of using `callPackage`.

### `builtins.currentSystem` in pure eval
`builtins.currentSystem` is not available in pure evaluation contexts. Use hardcoded system strings
for VM tests or guard with explicit platform detection.

### Python version mismatch
`flake.nix` uses `pkgs.python312`. `pyproject.toml` says `requires-python = ">=3.12"`. Keep these
in sync.

## CI / GitHub Actions

### Reusable workflow inputs
All reusable workflows must use `workflow_call` trigger with explicit `inputs:` and `secrets: inherit`.
Omission causes silent failures or missing permissions.

### OIDC PyPI publishing
Trusted publisher must be configured on PyPI BEFORE the first release tag.
Without it, the publish step silently skips.

### `dorny/paths-filter@v3`
Use v3, not v2. v2 has broken `changes-file` output on newer runner images.

### Flake lock drift
After changing flake inputs, run `nix flake lock` to update `flake.lock`. Otherwise you'll silently
use the old pinned versions.
