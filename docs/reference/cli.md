# CLI Reference

## Usage

```bash
uv2nix-template [OPTIONS] COMMAND [ARGS]...
```

## Global options

| Option | Description |
|--------|-------------|
| `--verbose` | Enable verbose logging |
| `--help` | Show help message |

## Commands

### `init`

Initialise a new uv2nix project.

```bash
uv2nix-template init
```

### `generate`

Generate output from the current project configuration.

```bash
uv2nix-template generate
```

### `validate`

Validate a generated project.

```bash
uv2nix-template validate [PATH]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `PATH` | `.` | Path to validate |
