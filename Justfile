default:
    @just --list

check: lint typecheck test-unit nix-check

lint:
    uv run ruff check src/ tests/
    uv run ruff format --check src/ tests/

lint-fix:
    uv run ruff check --fix src/ tests/
    uv run ruff format src/ tests/

typecheck:
    uv run mypy src/

test-unit:
    uv run pytest tests/unit/ -v

test-integration:
    uv run pytest tests/integration/ -v

test:
    uv run pytest -v

nix-check:
    nix flake check --no-build

nix-build:
    nix build .#default

build:
    uv build

clean:
    rm -rf dist/ .mypy_cache/ .ruff_cache/
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

uv-lock:
    uv lock

uv-sync:
    uv sync --all-groups

uv-upgrade:
    uv lock --upgrade
