# NixOS Integration Guide

## Adding to a NixOS configuration

```nix
# flake.nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    uv2nix-template = {
      url = "github:your-user/uv2nix-template";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, uv2nix-template, ... }: {
    nixosConfigurations.myhost = nixpkgs.lib.nixosSystem {
      modules = [
        uv2nix-template.nixosModules.default
        ./configuration.nix
      ];
    };
  };
}
```

## Basic configuration

```nix
{ config, ... }: {
  services.uv2nix-template = {
    enable = true;
    settings.logLevel = "debug";
    settings.extraArgs = [ "--flag" ];
    environment.MY_VAR = "value";
  };
}
```

## Using with Home Manager

```nix
{ config, ... }: {
  imports = [ uv2nix-template.homeManagerModules.default ];
  homeManagerModules.uv2nix-template.enable = true;
}
```

## Running VM tests

```bash
nix build .#vmTests.basic
```

This spins up a NixOS VM, verifies the service starts, and checks that
`/etc/uv2nix-template/config.json` exists.
