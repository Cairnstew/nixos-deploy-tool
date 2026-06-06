# CI Reference

## Pipeline overview

The CI uses `dorny/paths-filter` to detect which areas changed, then conditionally
calls reusable workflows.

## Workflows

### `ci.yml` (orchestrator)

| Job | Trigger | Runs on |
|-----|---------|---------|
| `lint` | Python changes | `uv run ruff check` + `ruff format --check` |
| `typecheck` | Python changes | `uv run mypy src/` |
| `test-unit` | Python changes | `uv run pytest tests/unit/ --cov` |
| `test-integration` | Python changes | `uv run pytest tests/integration/` |
| `nix` | Nix changes | `nix flake check` + `nix build` |
| `audit` | Python changes | `uv run pip-audit` + `uv run bandit` |
| `vm-test` | Nix changes | `nix build .#vmTests.basic` |

### `release.yml` (tag push `v*`)

1. Detect if the project has a CLI (via `[project.scripts]` in pyproject.toml)
2. Build via Nix
3. Publish to PyPI via OIDC trusted publishing
4. Create GitHub release

### `update-flake-lock.yml` (weekly)

Runs `nix flake lock --update`, opens a PR with label `automated`.
