# NixOS Module Reference

All options under `services.uv2nix-template`.

## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enable` | bool | false | Enable the service |
| `package` | package | auto | Package to use as binary |
| `settings.logLevel` | enum | `"info"` | Log verbosity: `debug`, `info`, `warn`, `error` |
| `settings.extraArgs` | list of str | `[]` | Extra CLI arguments |
| `environment` | attrs of str | `{}` | Environment variables for the service |

## Activation script

When enabled, the module writes `/etc/uv2nix-template/config.json` on every
`nixos-rebuild switch`. The config file contains the serialised `settings` value.

## Systemd service

The module creates `uv2nix-template.service` with:

- Type=simple
- Restart on failure (5s delay)
- NoNewPrivileges, ProtectSystem=strict, ProtectHome, PrivateTmp
- Environment variables from `environment` option
